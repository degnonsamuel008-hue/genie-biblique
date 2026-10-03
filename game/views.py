import random
import json
import qrcode
import base64
from datetime import timedelta
from io import BytesIO
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils import timezone
from django.contrib import messages
from .models import Game, GamePlayer, GameAnswer
from .utils import expire_stale_games
from quiz.models import Question, Book
from django.core.management import call_command


QUESTION_REVEAL_SECONDS = 2


def _ordered_options(game, question):
    with transaction.atomic():
        game = Game.objects.select_for_update().get(pk=game.pk)
        options_by_question = json.loads(game.question_options_json or '{}')
        options = options_by_question.get(str(question.pk))
        if options is None:
            options = [question.option1, question.option2, question.option3, question.option4]
            random.shuffle(options)
            options_by_question[str(question.pk)] = options
            game.question_options_json = json.dumps(options_by_question)
            game.save(update_fields=['question_options_json'])
        return options


def advance_game_if_due(game, now=None):
    """Advance a round only from persisted server time and state."""
    now = now or timezone.now()
    if game.status != 'playing':
        return

    question_ids = game.get_questions()
    if game.current_question_index >= len(question_ids):
        game.status = 'finished'
        game.finished_at = game.finished_at or now
        game.save(update_fields=['status', 'finished_at'])
        return

    if game.question_started_at is None:
        game.question_started_at = now
        game.save(update_fields=['question_started_at'])

    deadline = game.question_started_at + timedelta(seconds=game.time_per_question)
    if game.question_closed_at is None and now >= deadline:
        game.question_closed_at = deadline
        game.save(update_fields=['question_closed_at'])

    if (game.question_closed_at is not None and
            now >= game.question_closed_at + timedelta(seconds=QUESTION_REVEAL_SECONDS)):
        game.current_question_index += 1
        game.question_started_at = now
        game.question_closed_at = None
        game.question_winner = None
        if game.current_question_index >= len(question_ids):
            game.status = 'finished'
            game.finished_at = now
        game.save(update_fields=[
            'current_question_index', 'question_started_at',
            'question_closed_at', 'question_winner', 'status', 'finished_at',
        ])


# ── Créer une partie ────────────────────────────────────────────────────────

@login_required
def create_game(request):
    expire_stale_games()
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
        options_by_question = {}
        for question in selected:
            options = [question.option1, question.option2, question.option3, question.option4]
            random.shuffle(options)
            options_by_question[str(question.pk)] = options
        game.question_options_json = json.dumps(options_by_question)
        game.save()

        # L'organisateur rejoint automatiquement
        GamePlayer.objects.create(game=game, user=request.user)

        return redirect('game_lobby', code=game.code)

    # Si aucun livre n'existe encore, tenter d'importer automatiquement
    # depuis les CSV dans /data via la commande management `importer_livres`.
    try:
        call_command('import_books')
    except Exception:
        pass

    books = Book.objects.order_by('testament', 'name')
    return render(request, 'game/create.html', {'books': books})


# ── Rejoindre par code ou lien ───────────────────────────────────────────────

@login_required
def join_game(request):
    expire_stale_games()
    # Rejoindre depuis un lien direct ?code=ABC123
    code = request.GET.get('code', '') or request.POST.get('code', '')
    code = code.upper().strip()

    if code:
        with transaction.atomic():
            game = Game.objects.select_for_update().filter(code=code).first()
            if not game:
                messages.error(request, f"Aucune partie avec le code « {code} ».")
                return redirect('game_home')
            if game.status != 'waiting':
                messages.error(request, "Cette partie n'accepte plus de joueurs.")
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
    expire_stale_games()
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
    expire_stale_games()
    game    = get_object_or_404(Game, code=code)
    if game.status == 'expired':
        messages.error(request, "Cette salle d'attente a expiré après 24 heures.")
        return redirect('game_home')
    players = game.players.select_related('user').all()
    is_organizer = (game.organizer == request.user)

    # Démarrer la partie (organisateur seulement)
    if request.method == 'POST' and is_organizer and game.status == 'waiting':
        if game.players.count() < 2:
            messages.error(request, "Il faut au moins 2 joueurs pour démarrer.")
        else:
            with transaction.atomic():
                game = Game.objects.select_for_update().get(pk=game.pk)
                if game.status == 'waiting' and game.players.count() >= 2:
                    started_at = timezone.now()
                    game.status = 'playing'
                    game.started_at = started_at
                    game.current_question_index = 0
                    game.question_started_at = started_at
                    game.question_closed_at = None
                    game.question_winner = None
                    game.save(update_fields=[
                        'status', 'started_at', 'current_question_index',
                        'question_started_at', 'question_closed_at', 'question_winner',
                    ])
            if game.status == 'playing':
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
    expire_stale_games()
    game   = get_object_or_404(Game, code=code)
    player = get_object_or_404(GamePlayer, game=game, user=request.user)
    if game.status == 'expired':
        messages.error(request, "Cette partie a expiré avant son démarrage.")
        return redirect('game_home')
    if game.status == 'waiting':
        return redirect('game_lobby', code=code)
    if game.status == 'finished':
        return redirect('game_result', code=code)

    if request.method == 'POST':
        with transaction.atomic():
            game = Game.objects.select_for_update().get(pk=game.pk)
            player = GamePlayer.objects.select_for_update().get(pk=player.pk)
            now = timezone.now()
            advance_game_if_due(game, now)
            question_ids = game.get_questions()
            posted_index = request.POST.get('question_index')

            if (game.status == 'playing' and
                    posted_index == str(game.current_question_index) and
                    game.current_question_index < len(question_ids)):
                question_id = question_ids[game.current_question_index]
                already_answered = GameAnswer.objects.filter(
                    player=player, question_id=question_id,
                ).exists()
                deadline = game.question_started_at + timedelta(seconds=game.time_per_question)
                answer = request.POST.get('answer', '')
                question = get_object_or_404(Question, pk=question_id)

                if (not already_answered and game.question_winner_id is None and
                        game.question_closed_at is None and now < deadline):
                    is_winner = answer == question.correct_answer
                    elapsed = max(0, (now - game.question_started_at).total_seconds())
                    GameAnswer.objects.create(
                        player=player,
                        question_id=question.pk,
                        answer=answer,
                        is_correct=is_winner,
                        time_taken=elapsed,
                        points=1 if is_winner else 0,
                    )
                    if is_winner:
                        player.score += 1
                        player.save(update_fields=['score'])
                        game.question_winner = player
                        game.question_closed_at = now
                        game.save(update_fields=['question_winner', 'question_closed_at'])
        return redirect('game_play', code=code)

    with transaction.atomic():
        game = Game.objects.select_for_update().get(pk=game.pk)
        advance_game_if_due(game)
    if game.status == 'finished':
        return redirect('game_result', code=code)

    question_ids = game.get_questions()
    question_id = question_ids[game.current_question_index]
    question = get_object_or_404(Question, pk=question_id)
    options = _ordered_options(game, question)
    ranking = game.players.select_related('user').order_by('-score', 'joined_at', 'pk')[:5]
    deadline = game.question_started_at + timedelta(seconds=game.time_per_question)
    remaining = max(0, (deadline - timezone.now()).total_seconds())

    return render(request, 'game/play.html', {
        'game':       game,
        'question':   question,
        'options':    options,
        'answered':   game.current_question_index,
        'question_index': game.current_question_index,
        'total':      len(question_ids),
        'progress':   round(game.current_question_index / len(question_ids) * 100) if question_ids else 0,
        'ranking':    ranking,
        'player':     player,
        'question_closed': game.question_closed_at is not None,
        'question_winner': game.question_winner,
        'remaining_seconds': remaining,
    })


# ── Résultats ────────────────────────────────────────────────────────────────

@login_required
def game_result(request, code):
    game = get_object_or_404(Game, code=code)
    if not game.players.filter(user=request.user).exists():
        return redirect('game_home')
    if game.status == 'waiting':
        return redirect('game_lobby', code=code)
    if game.status != 'finished':
        return redirect('game_play', code=code)
    players = game.players.select_related('user').annotate(
        won_count=Count('answers', filter=Q(answers__is_correct=True)),
        response_time=Sum('answers__time_taken', filter=Q(answers__is_correct=True)),
    ).order_by('-score', '-won_count', 'response_time', 'joined_at', 'pk')
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
        'players':       players,
        'players_stats': players_stats,
        'my_player':     my_player,
        'my_rank':       my_rank,
        'share_links':   share_links,
    })


# ── API : statut du lobby (pour auto-refresh AJAX) ──────────────────────────

@login_required
def game_state(request, code):
    expire_stale_games()
    game = get_object_or_404(Game, code=code)
    get_object_or_404(GamePlayer, game=game, user=request.user)
    with transaction.atomic():
        game = Game.objects.select_for_update().get(pk=game.pk)
        advance_game_if_due(game)

    players = game.players.select_related('user').order_by('-score', 'joined_at', 'pk')
    now = timezone.now()
    remaining = 0
    if game.status == 'playing' and game.question_started_at:
        deadline = game.question_started_at + timedelta(seconds=game.time_per_question)
        remaining = max(0, (deadline - now).total_seconds())
    return JsonResponse({
        'status': game.status,
        'question_index': game.current_question_index,
        'question_closed': game.question_closed_at is not None,
        'winner': game.question_winner.user.username if game.question_winner_id else None,
        'remaining_seconds': remaining,
        'ranking': [
            {'username': player.user.username, 'score': player.score}
            for player in players
        ],
    })


@login_required
def lobby_status(request, code):
    """Retourne le statut du lobby en JSON pour l'auto-refresh"""
    expire_stale_games()
    game = get_object_or_404(Game, code=code)
    get_object_or_404(GamePlayer, game=game, user=request.user)
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
