from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView,
    PasswordResetConfirmView, PasswordResetCompleteView,
)
from django.contrib import messages
from django.urls import reverse_lazy
from .forms import (
    RegisterForm, ProfileForm,
    MonPasswordChangeForm, MonPasswordResetForm, MonSetPasswordForm,
)
from .models import UserProfile, Badge, UserBadge, AVATARS
from quiz.models import Score


# ── Inscription ──────────────────────────────────────────────────────────────

def register_view(request):
    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save(commit=False)
        user.set_password(form.cleaned_data['password'])
        user.save()  # le signal crée le profil automatiquement
        login(request, user)
        messages.success(request, f"Bienvenue {user.username} ! Ton compte a été créé.")
        return redirect('home')
    return render(request, 'accounts/register.html', {'form': form})


# ── Connexion ────────────────────────────────────────────────────────────────

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    error = None
    if request.method == 'POST':
        user = authenticate(
            username=request.POST.get('username', ''),
            password=request.POST.get('password', ''),
        )
        if user:
            login(request, user)
            next_url = request.GET.get('next', 'home')
            return redirect(next_url)
        error = "Nom d'utilisateur ou mot de passe incorrect."
    return render(request, 'accounts/login.html', {'error': error})


# ── Déconnexion ──────────────────────────────────────────────────────────────

def logout_view(request):
    logout(request)
    messages.info(request, "Tu as été déconnecté.")
    return redirect('home')


# ── Profil ───────────────────────────────────────────────────────────────────

@login_required
def profile_view(request):
    profile = request.user.profile
    form    = ProfileForm(
        request.POST   or None,
        request.FILES  or None,   # ← important pour les photos
        instance=profile,
    )

    if request.method == 'POST' and form.is_valid():
        # Si l'utilisateur choisit l'avatar → supprimer la photo
        if form.cleaned_data['photo_type'] == 'avatar':
            if profile.photo:
                profile.photo.delete(save=False)
            profile.photo = None

        form.save()
        messages.success(request, "Profil mis à jour !")
        return redirect('profile')

    user_badges   = UserBadge.objects.filter(user=request.user).select_related('badge')
    recent_scores = Score.objects.filter(user=request.user).order_by('-created_at')[:10]
    all_badges    = Badge.objects.filter()
    earned_ids    = [ub.badge_id for ub in user_badges]

    return render(request, 'accounts/profile.html', {
        'profile':       profile,
        'form':          form,
        'user_badges':   user_badges,
        'recent_scores': recent_scores,
        'all_badges':    all_badges,
        'earned_ids':    earned_ids,
        'avatars':       AVATARS,
    })


# ── Changer le mot de passe (utilisateur connecté) ───────────────────────────

@login_required
def change_password_view(request):
    form = MonPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)  # garder la session active
        messages.success(request, "Mot de passe changé avec succès !")
        return redirect('profile')
    return render(request, 'accounts/change_password.html', {'form': form})


# ════════════════════════════════════════════════════════════════════════════
# RÉINITIALISATION DU MOT DE PASSE (utilisateur NON connecté)
# ════════════════════════════════════════════════════════════════════════════
# Django gère tout le flux email → token → lien.
# On surcharge juste les vues pour utiliser nos templates.

class ResetPasswordView(PasswordResetView):
    """Étape 1 : l'utilisateur entre son email"""
    template_name      = 'accounts/password_reset.html'
    email_template_name = 'accounts/emails/reset_email.txt'
    html_email_template_name= 'accounts/emails/reset_email.html'
    subject_template_name='accounts/emails/reset_subject.txt'
    form_class         = MonPasswordResetForm
    success_url        = reverse_lazy('password_reset_done')


class ResetPasswordDoneView(PasswordResetDoneView):
    """Étape 2 : confirmation que l'email a été envoyé"""
    template_name = 'accounts/password_reset_done.html'


class ResetPasswordConfirmView(PasswordResetConfirmView):
    """Étape 3 : l'utilisateur entre son nouveau mot de passe (depuis le lien)"""
    template_name = 'accounts/password_reset_confirm.html'
    form_class    = MonSetPasswordForm
    success_url   = reverse_lazy('password_reset_complete')


class ResetPasswordCompleteView(PasswordResetCompleteView):
    """Étape 4 : confirmation que le mot de passe a été changé"""
    template_name = 'accounts/password_reset_complete.html'
