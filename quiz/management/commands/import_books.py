"""
Commande : python manage.py import_books

Crée les 66 livres de la Bible dans la table Book.
Aucun fichier CSV nécessaire — tout est écrit directement ici.
Utilise get_or_create donc aucun doublon possible,
même si tu relances la commande plusieurs fois.
"""

from django.core.management.base import BaseCommand
from quiz.models import Book


LIVRES = [
    # ── Ancien Testament (39 livres) ──
    "Genèse", "Exode", "Lévitique", "Nombres", "Deutéronome",
    "Josué", "Juges", "Ruth", "1 Samuel", "2 Samuel",
    "1 Rois", "2 Rois", "1 Chroniques", "2 Chroniques", "Esdras",
    "Néhémie", "Esther", "Job", "Psaumes", "Proverbes",
    "Ecclésiaste", "Cantique des Cantiques", "Ésaïe", "Jérémie", "Lamentations",
    "Ézéchiel", "Daniel", "Osée", "Joël", "Amos",
    "Abdias", "Jonas", "Michée", "Nahoum", "Habacuc",
    "Sophonie", "Aggée", "Zacharie", "Malachie",

    # ── Nouveau Testament (27 livres) ──
    "Matthieu", "Marc", "Luc", "Jean", "Actes",
    "Romains", "1 Corinthiens", "2 Corinthiens", "Galates", "Éphésiens",
    "Philippiens", "Colossiens", "1 Thessaloniciens", "2 Thessaloniciens",
    "1 Timothée", "2 Timothée", "Tite", "Philémon", "Hébreux",
    "Jacques", "1 Pierre", "2 Pierre", "1 Jean", "2 Jean",
    "3 Jean", "Jude", "Apocalypse",
]


class Command(BaseCommand):
    help = "Crée les 66 livres de la Bible dans la table Book (sans CSV)"

    def handle(self, *args, **kwargs):
        created_count = 0
        existing_count = 0

        for name in LIVRES:
            book, created = Book.objects.get_or_create(name=name)
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Créé : {book.name}"))
            else:
                existing_count += 1
                self.stdout.write(f"  = Déjà présent : {book.name}")

        self.stdout.write(self.style.SUCCESS(
            f"\nTerminé — {created_count} créés, {existing_count} déjà existants "
            f"({Book.objects.count()} livres au total en base)."
        ))
