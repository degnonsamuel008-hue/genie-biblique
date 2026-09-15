import csv
from django.core.management.base import BaseCommand
from accounts.models import Badge


class Command(BaseCommand):
    help = "Importe les badges depuis data/badges.csv"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='data/badges.csv',
            help='Chemin vers le fichier CSV (par défaut : data/badges.csv)'
        )

    def handle(self, *args, **options):
        filepath = options['file']
        created_count = 0
        updated_count = 0
        error_count = 0

        try:
            with open(filepath, encoding='utf-8') as f:
                reader = csv.DictReader(f)

                for row_number, row in enumerate(reader, start=2):
                    try:
                        badge, created = Badge.objects.update_or_create(
                            name=row['name'].strip(),
                            defaults={
                                'description':     row['description'].strip(),
                                'icon':            row['icon'].strip(),
                                'badge_type':      row['badge_type'].strip(),
                                'condition_key':   row['condition_key'].strip(),
                                'condition_value': int(row['condition_value']),
                                'xp_reward':       int(row['xp_reward']),
                            }
                        )
                        if created:
                            created_count += 1
                            self.stdout.write(self.style.SUCCESS(
                                f"  + Créé : {badge.icon} {badge.name}"
                            ))
                        else:
                            updated_count += 1
                            self.stdout.write(f"  ~ Mis à jour : {badge.icon} {badge.name}")

                    except (KeyError, ValueError) as e:
                        error_count += 1
                        self.stdout.write(self.style.ERROR(
                            f"  ✗ Ligne {row_number} ignorée : {e}"
                        ))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(
                f"Fichier introuvable : {filepath}\n"
                f"Place badges.csv dans le dossier data/ ou précise le chemin avec --file"
            ))
            return

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé — {created_count} créés, {updated_count} mis à jour"
            + (f", {error_count} erreurs" if error_count else "")
            + f" ({Badge.objects.count()} badges au total en base)."
        ))