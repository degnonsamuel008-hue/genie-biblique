from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.forms import (
    PasswordResetForm, SetPasswordForm, PasswordChangeForm
)
from .models import UserProfile, AVATAR_CHOICES


# ── Inscription ──────────────────────────────────────────────────────────────

class RegisterForm(forms.ModelForm):
    password  = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        min_length=8,
        error_messages={
            'min_length': 'Le mot de passe doit contenir au moins 8 caractères.',
        },
        label="Mot de passe",
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': '••••••••'}),
        label="Confirmer le mot de passe",
        required=False,
    )

    class Meta:
        model  = User
        fields = ['username', 'email', 'password']

    def clean(self):
        data = super().clean()
        password = data.get('password')
        password_confirm = data.get('password_confirm') or self.data.get('password2')
        if password and password_confirm and password != password_confirm:
            raise forms.ValidationError("Les mots de passe ne correspondent pas.")
        if password and not password_confirm:
            raise forms.ValidationError("La confirmation du mot de passe est obligatoire.")
        return data

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Ce nom d'utilisateur est déjà pris.")
        return username

    def clean_password(self):
        password = self.cleaned_data['password']
        validate_password(password, self.instance)
        return password

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            raise forms.ValidationError("Cet email est déjà utilisé.")
        return email


# ── Profil (avatar + photo) ──────────────────────────────────────────────────

class ProfileForm(forms.ModelForm):
    avatar = forms.CharField(required=False, max_length=30)
    photo_type = forms.ChoiceField(
        choices=[('avatar', 'Avatar'), ('photo', 'Photo')],
        required=False,
    )

    class Meta:
        model  = UserProfile
        fields = ['photo_type', 'avatar', 'photo', 'bio']
        widgets = {
            'bio': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Dis quelque chose sur toi...'}),
        }

    def clean(self):
        data       = super().clean()
        photo_type = data.get('photo_type') or 'avatar'
        photo      = data.get('photo')

        if photo_type == 'photo' and not photo and not self.instance.photo:
            raise forms.ValidationError(
                "Tu as choisi 'Photo personnelle' mais n'as pas uploadé de photo."
            )
        return data

    def clean_avatar(self):
        avatar = self.cleaned_data.get('avatar')
        return avatar or self.instance.avatar or 'lion'

    def clean_photo(self):
        photo = self.cleaned_data.get('photo')
        if photo:
            # Vérifier la taille (max 2 Mo)
            if photo.size > 2 * 1024 * 1024:
                raise forms.ValidationError("La photo ne doit pas dépasser 2 Mo.")
            # Vérifier le format
            ext = photo.name.split('.')[-1].lower()
            if ext not in ['jpg', 'jpeg', 'png', 'webp']:
                raise forms.ValidationError("Format accepté : JPG, PNG, WEBP.")
        return photo


# ── Changer le mot de passe (connecté) ───────────────────────────────────────

class MonPasswordChangeForm(PasswordChangeForm):
    """Surcharge pour appliquer notre style Bootstrap"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control form-control-lg rounded-xl',
            })


# ── Réinitialisation (email) ─────────────────────────────────────────────────

class MonPasswordResetForm(PasswordResetForm):
    """Formulaire "Mot de passe oublié ?" — envoie un email"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
            'class':       'form-control form-control-lg rounded-xl',
            'placeholder': 'ton@email.com',
        })

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                "Aucun compte n'est associé à cet email."
            )
        return email


# ── Nouveau mot de passe (depuis le lien email) ───────────────────────────────

class MonSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.update({
                'class': 'form-control form-control-lg rounded-xl',
            })
