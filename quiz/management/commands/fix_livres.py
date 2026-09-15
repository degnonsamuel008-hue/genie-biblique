from django.core.management.base import BaseCommand
from quiz.models import Question, Livre
import re
import os


def clean_livre(name):
    if not name:
        return name

    # Cas où le champ a été enregistré comme tuple string: ("Genese", ".csv")
    m = re.match(r"^\('(.+?)',\s*'(.+?)'\)$", name)
    if m:
        name = m.group(1)

    # Enlever préfixes de type '123_Questions_'
    name = re.sub(r'^\d+_Questions_', '', name)

    # Enlever extension si présente
    name = os.path.splitext(name)[0]

    # Remplacer underscore par espaces et trim
    return name.replace('_', ' ').strip()


class Command(BaseCommand):
    help = 'Nettoie le champ livre des questions (supprime tuples et extensions)'

    def handle(self, *args, **kwargs):
        for q in Question.objects.all():
            cleaned = clean_livre(q.livre)
            livre_obj, created = Livre.objects.get_or_create(nom=cleaned)
            # Conserver la valeur string correcte dans Question.livre
            q.livre = livre_obj.nom
            q.save()

        self.stdout.write(self.style.SUCCESS("Nettoyage des livres terminé"))