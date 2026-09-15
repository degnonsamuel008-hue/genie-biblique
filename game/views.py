import random
import json
import qrcode
import base64
from io import BytesIO
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import Game, GamePlayer, GameAnswer
from quiz.models import Question, Book
from django.core.management import call_command


# ── Créer une partie ────────────────────────────────────────────────────────

@login_required
def create_game(request):
    if request.method == 'POST':
        difficulty = request.POST.get('difficulty', 'all')
        book_name  = request.POST.get('book', '')
        count      = int(request.POST.get('count', 10))
        time_per_q = int(request.POST.get('time', 15))

        # Construire le pool de questions
        qs = Question.objects.all()
        if difficulty != 'all':
            qs = qs.filter(difficulty=difficulty)
        if book_name:
            qs = qs.filter(book__name=book_name)

        if qs.count() < 5:
            messages.error(request, "Pas assez de questions pour ces critères. Essaie d'autres paramètres.")
            return redirect('create_game')

        selected = random.sample(list(qs), min(count, qs.count()))

        game = Game.objects.create(
            organizer         = request.user,
            time_per_question = time_per_q,
            question_count    = len(selected),
            book_filter       = book_name,
            difficulty_filter = difficulty,
        )
        game.set_questions([q.id for q in selected])
        game.save()

        # L'organisateur rejoint automatiquement
        GamePlayer.objects.create(game=game, user=request.user)

        return redirect('game_lobby', code=game.code)

    # Si aucun livre n'existe encore, tenter d'importer automatiquement
    # depuis les CSV dans /data via la commande management `importer_livres`.
    if not Book.objects.exists():
        try:
            call_command('importer_livres')
        except Exception:
            # Si l'import échoue, on continue mais la liste restera vide
            pass

    books = Book.objects.all()
    return render(request, 'game/create.html', {'books': books})


# ── Rejoindre par code ou lien ───────────────────────────────────────────────

@login_required
def join_game(request):
    # Rejoindre depuis un lien direct ?code=ABC123
    code = request.GET.get('code', '') or request.POST.get('code', '')
    code = code.upper().strip()

    if code:
        game = Game.objects.filter(code=code).first()
        if not game:
            messages.error(request, f"Aucune partie avec le code « {code} ».")
            return redirect('game_home')
        if game.status == 'finished':
            messages.error(request, "Cette partie est déjà terminée.")
            return redirect('game_home')
        if game.status == 'playing':
            messages.error(request, "Cette partie a déjà commencé.")
            return redirect('game_home')
        if game.players.count() >= 20:
            messages.error(request, "La salle est pleine (20 joueurs maximum).")
            return redirect('game_home')

        GamePlayer.objects.get_or_create(game=game, user=request.user)
        return redirect('game_lobby', code=game.code)

    # Aucun code → page d'accueil du game
    return redirect('game_home')


# ── Accueil du game ──────────────────────────────────────────────────────────

@login_required
def game_home(request):
    active_games = Game.objects.filter(status='waiting').order_by('-created_at')[:8]
    my_games     = Game.objects.filter(
        players__user=request.user
    ).order_by('-created_at')[:5]
    return render(request, 'game/home.html', {
        'active_games': active_games,
        'my_games':     my_games,
    })


# ── Lobby ────────────────────────────────────────────────────────────────────

@login_required
def game_lobby(request, code):
    game    = get_object_or_404(Game, code=code)
    players = game.players.select_related('user').all()
    is_organizer = (game.organizer == request.user)

    # Démarrer la partie (organisateur seulement)
    if request.method == 'POST' and is_organizer:
        if game.players.count() < 2:
            messages.error(request, "Il faut au moins 2 joueurs pour démarrer.")
        else:
            game.status     = 'playing'
            game.started_at = timezone.now()
            game.save()
            return redirect('game_play', code=code)

    # Générer le QR code
    invite_url = request.build_absolute_uri(f'/game/join/?code={game.code}')
    qr_b64 = generate_qr_code(invite_url)

    # Liens de partage
    share_links = build_share_links(game, invite_url)

    return render(request, 'game/lobby.html', {
        'game':         game,
        'players':      players,
        'is_organizer': is_organizer,
        'invite_url':   invite_url,
        'qr_code':      qr_b64,
        'share_links':  share_links,
    })


# ── Jouer ────────────────────────────────────────────────────────────────────

@login_required
def game_play(request, code):
    game   = get_object_or_404(Game, code=code, status='playing')
    player = get_object_or_404(GamePlayer, game=game, user=request.user)

    ids = game.get_questions()

    # Ordre personnalisé anti-IA par joueur
    session_key = f'game_{code}_order_{request.user.id}'
    if session_key not in request.session:
        my_order = ids[:]
        random.shuffle(my_order)
        request.session[session_key] = my_order
    my_ids = request.session[session_key]

    answered_count = GameAnswer.objects.filter(player=player).count()

    # Toutes les questions répondues → résultat
    if answered_count >= len(my_ids):
        player.finished = True
        player.save()
        # Vérifier si tout le monde a fini
        all_finished = not game.players.filter(finished=False).exists()
        if all_finished:
            game.status      = 'finished'
            game.finished_at = timezone.now()
            game.save()
        return redirect('game_result', code=code)

    q       = get_object_or_404(Question, id=my_ids[answered_count])
    options = [q.option1, q.option2, q.option3, q.option4]
    random.shuffle(options)

    if request.method == 'POST':
        ans        = request.POST.get('answer', '')
        time_taken = float(request.POST.get('time_taken', game.time_per_question))
        is_correct = (ans == q.correct_answer)

        # Calcul des points : plus c'est rapide plus c'est de points
        if is_correct:
            ratio  = max(0, (game.time_per_question - time_taken) / game.time_per_question)
            points = int(500 + 500 * ratio)   # entre 500 et 1000 points
        else:
            points = 0

        GameAnswer.objects.create(
            player      = player,
            question_id = q.id,
            answer      = ans,
            is_correct  = is_correct,
            time_taken  = time_taken,
            points      = points,
        )
        player.score += points
        player.save()

        return redirect('game_play', code=code)

    # Classement en cours pour affichage pendant le jeu
    ranking = game.players.select_related('user').order_by('-score')[:5]

    return render(request, 'game/play.html', {
        'game':       game,
        'question':   q,
        'options':    options,
        'answered':   answered_count,
        'total':      len(my_ids),
        'progress':   round(answered_count / len(my_ids) * 100) if my_ids else 0,
        'ranking':    ranking,
        'player':     player,
    })


# ── Résultats ────────────────────────────────────────────────────────────────

@login_required
def game_result(request, code):
    game    = get_object_or_404(Game, code=code)
    players = game.players.select_related('user').order_by('-score')
    my_player = game.players.filter(user=request.user).first()

    # Rang du joueur actuel
    my_rank = list(players).index(my_player) + 1 if my_player else 0

    # Stats de chaque joueur
    players_stats = []
    for p in players:
        answers = GameAnswer.objects.filter(player=p)
        correct = answers.filter(is_correct=True).count()
        total   = answers.count()
        avg_time = round(
            sum(a.time_taken for a in answers) / total, 1
        ) if total > 0 else 0
        players_stats.append({
            'player':   p,
            'correct':  correct,
            'total':    total,
            'accuracy': round(correct / total * 100) if total > 0 else 0,
            'avg_time': avg_time,
        })

    invite_url  = request.build_absolute_uri(f'/game/join/?code={game.code}')
    share_links = build_share_links(game, invite_url, result=True)

    return render(request, 'game/result.html', {
        'game':          game,
        'players_stats': players_stats,
        'my_player':     my_player,
        'my_rank':       my_rank,
        'share_links':   share_links,
    })


# ── API : statut du lobby (pour auto-refresh AJAX) ──────────────────────────

def lobby_status(request, code):
    """Retourne le statut du lobby en JSON pour l'auto-refresh"""
    game = get_object_or_404(Game, code=code)
    players = list(game.players.select_related('user').values(
        'user__username', 'score', 'is_ready', 'finished'
    ))
    return JsonResponse({
        'status':       game.status,
        'player_count': game.players.count(),
        'players':      players,
    })


# ── Helpers ──────────────────────────────────────────────────────────────────

def generate_qr_code(url):
    """Génère un QR code en base64 pour affichage HTML"""
    try:
        qr = qrcode.QRCode(version=1, box_size=6, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(fill_color='#1a2744', back_color='white')
        buf = BytesIO()
        img.save(buf, format='PNG')
        return base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return ''


def build_share_links(game, invite_url, result=False):
    """Construit les liens de partage pour toutes les plateformes"""
    if result:
        text = f"🏆 Je viens de jouer au Génie Biblique ! Code de la partie : {game.code}"
    else:
        text = (
            f"✝️ Je t'invite à jouer au Génie Biblique !\n"
            f"Code : {game.code}\n"
            f"Clique ici pour rejoindre :"
        )

    from urllib.parse import quote
    text_enc = quote(text)
    url_enc  = quote(invite_url)

    return {
        'whatsapp': f"https://wa.me/?text={text_enc}%20{url_enc}",
        'facebook': f"https://www.facebook.com/sharer/sharer.php?u={url_enc}",
        'telegram': f"https://t.me/share/url?url={url_enc}&text={text_enc}",
        'twitter':  f"https://twitter.com/intent/tweet?text={text_enc}&url={url_enc}",
        'email':    f"mailto:?subject=Invitation+Génie+Biblique&body={text_enc}%20{url_enc}",
    }
