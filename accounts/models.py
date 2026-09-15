from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.validators import FileExtensionValidator
from django.core.exceptions import ValidationError
# ── Avatars prédéfinis ──────────────────────────────────────────────────────
AVATARS = [
    ('lion',     '🦁', 'Lion'),
    ('colombe',  '🕊️', 'Colombe'),
    ('agneau',   '🐑', 'Agneau'),
    ('etoile',   '⭐', 'Étoile'),
    ('feu',      '🔥', 'Feu'),
    ('couronne', '👑', 'Couronne'),
    ('livre',    '📖', 'Livre'),
    ('croix',    '✝️',  'Croix'),
    ('arc',      '🌈', 'Arc-en-ciel'),
    ('ancre',    '⚓', 'Ancre'),
    ('epee',     '⚔️',  'Épée'),
    ('lumiere',  '💡', 'Lumière'),
]

AVATAR_CHOICES = [(key, label) for key, emoji, label in AVATARS]
AVATAR_EMOJIS  = {key: emoji for key, emoji, label in AVATARS}

def taille_maximun(fichier):
    if fichier.size > 2*1024*1024:
        raise ValidationError("Le fichier ne doit pas dépasser 2 Mo ")

class UserProfileManager(models.Manager):
    def get_or_create(self, **kwargs):
        if 'user' in kwargs:
            return super().get_or_create(**kwargs)
        return super().get_or_create(**kwargs)

    def create(self, **kwargs):
        if 'user' in kwargs:
            existing = self.filter(user=kwargs['user']).first()
            if existing:
                return existing
        return super().create(**kwargs)


class UserProfile(models.Model):
    objects = UserProfileManager()
    user   = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # ── Photo ou avatar ──
    photo_type = models.CharField(
        max_length=10,
        choices=[('avatar', 'Avatar'), ('photo', 'Photo')],
        default='avatar',
    )
    avatar = models.CharField(
        max_length=30, default='lion',
    )
    photo  = models.ImageField(
        upload_to='photos_profil/', null=True, blank=True,
        help_text="Photo personnelle (optionnel)",
        validators=[FileExtensionValidator(allowed_extensions=["jpg","jpeg","png","webp"]),taille_maximun],
    
    )

    # ── Stats ──
    total_xp                  = models.IntegerField(default=0)
    total_questions_answered  = models.IntegerField(default=0)
    total_correct             = models.IntegerField(default=0)
    streak_days               = models.IntegerField(default=0)
    last_played               = models.DateField(null=True, blank=True)
    bio                       = models.TextField(blank=True)
    created_at                = models.DateTimeField(auto_now_add=True)

    # ── Propriétés ──────────────────────────────────────────────────────────
    LEVELS = [
        (0,    'Néophyte',    '🌱'),
        (100,  'Disciple',   '📖'),
        (300,  'Apôtre',     '✝️'),
        (600,  'Prophète',   '🔥'),
        (1000, 'Sage',       '⚡'),
        (1500, 'Patriarche', '👑'),
        (2500, 'Maître',     '💎'),
    ]

    @property
    def level(self):
        name = 'Néophyte'
        for xp, n, i in self.LEVELS:
            if self.total_xp >= xp:
                name = n
        return name

    @property
    def level_name(self):
        return self.level

    @property
    def xp_progress_percent(self):
        prev_xp, next_xp = 0, self.LEVELS[-1][0]
        for i, (xp, n, ic) in enumerate(self.LEVELS):
            if self.total_xp >= xp:
                prev_xp = xp
                if i + 1 < len(self.LEVELS):
                    next_xp = self.LEVELS[i + 1][0]
        if next_xp == prev_xp:
            return 100
        return round((self.total_xp - prev_xp) / (next_xp - prev_xp) * 100)

    @property
    def accuracy_rate(self):
        if self.total_questions_answered == 0:
            return 0
        return round(self.total_correct / self.total_questions_answered * 100)

    @property
    def avatar_emoji(self):
        return AVATAR_EMOJIS.get(self.avatar, '👤')

    @property
    def display_photo(self):
        """Retourne l'emoji avatar ou l'URL de la photo"""
        if self.photo_type == 'photo' and self.photo:
            return {'type': 'photo', 'url': self.photo.url}
        return {'type': 'avatar', 'emoji': self.avatar_emoji}

    def update_streak(self):
        from django.utils import timezone
        today = timezone.now().date()
        if self.last_played:
            diff = (today - self.last_played).days
            if diff == 1:
                self.streak_days += 1
            elif diff > 1:
                self.streak_days = 1
        else:
            self.streak_days = 1
        self.last_played = today
        self.save()

    def __str__(self):
        return f"Profil de {self.user.username}"


class Badge(models.Model):
    TYPES = [
        ('milestone',  'Étape'),
        ('streak',     'Régularité'),
        ('difficulty', 'Difficulté'),
        ('speed',      'Vitesse'),
        ('accuracy',   'Précision'),
        ('special',    'Spécial'),
    ]
    name            = models.CharField(max_length=100)
    description     = models.TextField()
    icon            = models.CharField(max_length=10)
    badge_type      = models.CharField(max_length=20, choices=TYPES)
    condition_key   = models.CharField(max_length=50)
    condition_value = models.IntegerField()
    xp_reward       = models.IntegerField(default=50)

    def __str__(self):
        return f"{self.icon} {self.name}"


class UserBadge(models.Model):
    user      = models.ForeignKey(User, on_delete=models.CASCADE, related_name='badges')
    badge     = models.ForeignKey(Badge, on_delete=models.CASCADE)
    earned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'badge']


# ── Signal : crée le profil automatiquement à l'inscription ─────────────────
@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
