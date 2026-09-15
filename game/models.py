import json
import string
import random
from django.db import models
from django.contrib.auth.models import User


def generate_code():
    """Génère un code unique de 6 caractères ex: AB12CD"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=6))
        if not Game.objects.filter(code=code).exists():
            return code


class Game(models.Model):
    STATUS_CHOICES = [
        ('waiting',  'En attente'),
        ('playing',  'En cours'),
        ('finished', 'Terminé'),
    ]

    code               = models.CharField(max_length=6, unique=True, default=generate_code)
    organizer          = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_games')
    status             = models.CharField(max_length=20, choices=STATUS_CHOICES, default='waiting')
    time_per_question  = models.IntegerField(default=15, help_text="Secondes — anti-IA")
    question_count     = models.IntegerField(default=10)
    book_filter        = models.CharField(max_length=100, blank=True)
    difficulty_filter  = models.CharField(max_length=20, default='all')
    questions_json     = models.TextField(default='[]')
    created_at         = models.DateTimeField(auto_now_add=True)
    started_at         = models.DateTimeField(null=True, blank=True)
    finished_at        = models.DateTimeField(null=True, blank=True)

    def get_questions(self):
        return json.loads(self.questions_json)

    def set_questions(self, ids):
        self.questions_json = json.dumps(ids)

    def get_invite_link(self, request):
        """Retourne le lien complet d'invitation"""
        return request.build_absolute_uri(f'/game/join/?code={self.code}')

    @property
    def player_count(self):
        return self.players.count()

    def __str__(self):
        return f"Game {self.code} — {self.status}"


class GamePlayer(models.Model):
    game      = models.ForeignKey(Game, on_delete=models.CASCADE, related_name='players')
    user      = models.ForeignKey(User, on_delete=models.CASCADE)
    score     = models.IntegerField(default=0)
    is_ready  = models.BooleanField(default=False)
    finished  = models.BooleanField(default=False)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['game', 'user']
        ordering = ['-score']

    def __str__(self):
        return f"{self.user.username} dans {self.game.code} — {self.score} pts"


class GameAnswer(models.Model):
    player     = models.ForeignKey(GamePlayer, on_delete=models.CASCADE, related_name='answers')
    question_id= models.IntegerField()
    answer     = models.CharField(max_length=300, blank=True)
    is_correct = models.BooleanField(default=False)
    time_taken = models.FloatField(default=0, help_text="Secondes pour répondre")
    points     = models.IntegerField(default=0)
    answered_at= models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['player', 'question_id']

    def __str__(self):
        return f"{self.player.user.username} — Q{self.question_id} — {self.points}pts"
