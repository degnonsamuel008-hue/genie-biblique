from django.core.management.base import BaseCommand

from game.utils import expire_stale_games


class Command(BaseCommand):
    help = 'Expire les salles de jeu restées en attente pendant plus de 24 heures.'

    def handle(self, *args, **options):
        expired_count = expire_stale_games()
        self.stdout.write(self.style.SUCCESS(
            f'{expired_count} salle(s) d’attente expirée(s).'
        ))