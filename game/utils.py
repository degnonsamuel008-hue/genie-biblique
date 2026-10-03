from datetime import timedelta

from django.utils import timezone

from .models import Game


WAITING_GAME_MAX_AGE = timedelta(hours=24)


def expire_stale_games(now=None):
    now = now or timezone.now()
    cutoff = now - WAITING_GAME_MAX_AGE
    return Game.objects.filter(
        status='waiting',
        created_at__lt=cutoff,
    ).update(status='expired')