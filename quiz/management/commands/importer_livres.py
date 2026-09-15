import csv
import os
from django.conf import settings  # Important pour localiser le projet
from django.core.management.base import BaseCommand
from quiz.models import Book, Question

class Command(BaseCommand):
    help = "Importe les questions depuis tous les fichiers CSV dans le dossier data/ à la racine du projet"

    def handle(self, *args, **kwargs):
        # Localise le dossier 'data' à la racine du projet, 
        # peu importe où se trouve l'application
        base_dir = settings.BASE_DIR
        data_dir = os.path.join(base_dir, 'data')
        
        if not os.path.exists(data_dir):
            self.stdout.write(self.style.ERROR(f"Le dossier '{data_dir}' est introuvable."))
            return

        for filename in os.listdir(data_dir):
            if filename.endswith(".csv"):
                file_path = os.path.join(data_dir, filename)
                self.stdout.write(f"Importation de : {filename}")
                
                with open(file_path, mode='r', encoding='utf-8') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if not row.get("question"):
                            continue
                            
                        book_name = row.get("book") or filename.replace(".csv", "")
                        book, _ = Book.objects.get_or_create(name=book_name)
                        
                        Question.objects.get_or_create(
                            question=row["question"],
                            defaults=dict(
                                book=book,
                                option1=row["option1"],
                                option2=row["option2"],
                                option3=row["option3"],
                                option4=row["option4"],
                                correct_answer=row["correct_answer"],
                                difficulty=row["difficulty"],
                                time_limit=int(row.get("time_limit", 30)),
                                explanation=row.get("explanation", ""),
                            )
                        )
        self.stdout.write(self.style.SUCCESS("Importation terminée avec succès !"))