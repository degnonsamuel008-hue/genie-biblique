from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Avg, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta
import json

from quiz.models import Question, Score, Book
from accounts.models import UserProfile, Badge, UserBadge
from game.models import Game, GamePlayer
from game.utils import expire_stale_games
from bible.models import DailyReading, ReadingProgress


def is_admin(user):
    """Seuls les staff/superuser accèdent au dashboard"""
    return user.is_authenticated and user.is_staff


# ── Tableau de bord principal ────────────────────────────────────────────────

@user_passes_test(is_admin, login_url='home')
def dashboard_home(request):
    expire_stale_games()
    now = timezone.now()
    last_7_days = now - timedelta(days=7)
    last_30_days = now - timedelta(days=30)

    # ── Stats globales ──
    stats = {
        'total_users': User.objects.count(),
        'new_users_week': User.objects.filter(date_joined__gte=last_7_days).count(),
        'total_questions': Question.objects.count(),
        'total_scores': Score.objects.count(),
        'scores_week': Score.objects.filter(created_at__gte=last_7_days).count(),
        'total_games': Game.objects.count(),
        'active_games': Game.objects.filter(status='playing').count(),
        'total_xp_distributed': UserProfile.objects.aggregate(s=Sum('total_xp'))['s'] or 0,
        'avg_accuracy': 0,
        'total_badges_earned': UserBadge.objects.count(),
        'active_readers': ReadingProgress.objects.filter(completed=True).values('user').distinct().count(),
    }

    # Précision moyenne globale
    profiles = UserProfile.objects.filter(total_questions_answered__gt=0)
    if profiles.exists():
        total_correct = sum(p.total_correct for p in profiles)
        total_answered = sum(p.total_questions_answered for p in profiles)
        stats['avg_accuracy'] = round(total_correct / total_answered * 100) if total_answered else 0

    # ── Graphique : inscriptions par jour (30 derniers jours) ──
    signups = (
        User.objects.filter(date_joined__gte=last_30_days)
        .annotate(day=TruncDate('date_joined'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    signups_labels = [s['day'].strftime('%d/%m') for s in signups]
    signups_data = [s['count'] for s in signups]

    # ── Graphique : parties jouées par jour (30 derniers jours) ──
    scores_by_day = (
        Score.objects.filter(created_at__gte=last_30_days)
        .annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(count=Count('id'))
        .order_by('day')
    )
    scores_labels = [s['day'].strftime('%d/%m') for s in scores_by_day]
    scores_data = [s['count'] for s in scores_by_day]

    # ── Graphique : répartition par difficulté ──
    diff_data = Score.objects.values('difficulty').annotate(count=Count('id')).order_by('-count')
    diff_labels = [d['difficulty'] for d in diff_data]
    diff_counts = [d['count'] for d in diff_data]

    # ── Graphique : questions par livre (top 10) ──
    books_data = (
        Question.objects.values('book__name')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    books_labels = [b['book__name'] for b in books_data]
    books_counts = [b['count'] for b in books_data]

    # ── Top joueurs ──
    top_players = UserProfile.objects.select_related('user').order_by('-total_xp')[:10]

    # ── Dernières inscriptions ──
    recent_users = User.objects.order_by('-date_joined')[:8]

    # ── Dernières parties organisées ──
    recent_games = Game.objects.select_related('organizer').order_by('-created_at')[:8]

    context = {
        'stats': stats,
        'signups_labels': json.dumps(signups_labels),
        'signups_data': json.dumps(signups_data),
        'scores_labels': json.dumps(scores_labels),
        'scores_data': json.dumps(scores_data),
        'diff_labels': json.dumps(diff_labels),
        'diff_counts': json.dumps(diff_counts),
        'books_labels': json.dumps(books_labels),
        'books_counts': json.dumps(books_counts),
        'top_players': top_players,
        'recent_users': recent_users,
        'recent_games': recent_games,
    }
    return render(request, 'dashboard/home.html', context)


# ── Gestion des utilisateurs ──────────────────────────────────────────────────

@user_passes_test(is_admin, login_url='home')
def dashboard_users(request):
    search = request.GET.get('q', '')
    users = User.objects.select_related('profile').order_by('-date_joined')

    if search:
        users = users.filter(
            Q(username__icontains=search) | Q(email__icontains=search)
        )

    # Filtre par statut
    status = request.GET.get('status', '')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    elif status == 'staff':
        users = users.filter(is_staff=True)

    # Pagination simple
    from django.core.paginator import Paginator
    paginator = Paginator(users, 25)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)

    return render(request, 'dashboard/users.html', {
        'page_obj': page_obj,
        'search': search,
        'status': status,
        'total_users': User.objects.count(),
    })


@user_passes_test(is_admin, login_url='home')
def dashboard_user_detail(request, user_id):
    target_user = get_object_or_404(User, id=user_id)
    profile, _ = UserProfile.objects.get_or_create(user=target_user)
    scores = Score.objects.filter(user=target_user).order_by('-created_at')[:20]
    badges = UserBadge.objects.filter(user=target_user).select_related('badge')
    games = GamePlayer.objects.filter(user=target_user).select_related('game')[:10]

    return render(request, 'dashboard/user_detail.html', {
        'target_user': target_user,
        'profile': profile,
        'scores': scores,
        'badges': badges,
        'games': games,
    })


@user_passes_test(is_admin, login_url='home')
def dashboard_toggle_active(request, user_id):
    """Activer / désactiver un compte"""
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "Tu ne peux pas te désactiver toi-même.")
    else:
        target_user.is_active = not target_user.is_active
        target_user.save()
        action = "activé" if target_user.is_active else "désactivé"
        messages.success(request, f"Compte de {target_user.username} {action}.")
    return redirect('dashboard_user_detail', user_id=user_id)


@user_passes_test(is_admin, login_url='home')
def dashboard_toggle_staff(request, user_id):
    """Promouvoir / rétrograder un admin"""
    target_user = get_object_or_404(User, id=user_id)
    if target_user == request.user:
        messages.error(request, "Tu ne peux pas modifier ton propre statut admin.")
    else:
        target_user.is_staff = not target_user.is_staff
        target_user.save()
        action = "promu administrateur" if target_user.is_staff else "rétrogradé utilisateur"
        messages.success(request, f"{target_user.username} a été {action}.")
    return redirect('dashboard_user_detail', user_id=user_id)


# ── Gestion des questions ────────────────────────────────────────────────────

@user_passes_test(is_admin, login_url='home')
def dashboard_questions(request):
    search = request.GET.get('q', '')
    book_filter = request.GET.get('book', '')
    diff_filter = request.GET.get('difficulty', '')

    questions = Question.objects.select_related('book').order_by('-id')
    if search:
        questions = questions.filter(question__icontains=search)
    if book_filter:
        questions = questions.filter(book__name=book_filter)
    if diff_filter:
        questions = questions.filter(difficulty=diff_filter)

    from django.core.paginator import Paginator
    paginator = Paginator(questions, 30)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    books = Book.objects.all()

    return render(request, 'dashboard/questions.html', {
        'page_obj': page_obj,
        'search': search,
        'book_filter': book_filter,
        'diff_filter': diff_filter,
        'books': books,
        'total_questions': Question.objects.count(),
    })


@user_passes_test(is_admin, login_url='home')
def dashboard_delete_question(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    if request.method == 'POST':
        question.delete()
        messages.success(request, "Question supprimée.")
    return redirect('dashboard_questions')


# ── Gestion des parties (Game) ────────────────────────────────────────────────

@user_passes_test(is_admin, login_url='home')
def dashboard_games(request):
    expire_stale_games()
    status_filter = request.GET.get('status', '')
    games = Game.objects.select_related('organizer').annotate(
        nb_players=Count('players')
    ).order_by('-created_at')

    if status_filter:
        games = games.filter(status=status_filter)

    from django.core.paginator import Paginator
    paginator = Paginator(games, 25)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'dashboard/games.html', {
        'page_obj': page_obj,
        'status_filter': status_filter,
    })
