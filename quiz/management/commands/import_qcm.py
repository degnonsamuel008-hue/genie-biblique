import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from quiz.models import Book, Question


class Command(BaseCommand):
    help = "Importe un fichier CSV de questions QCM"

    def add_arguments(self, parser):
        parser.add_argument(
            "csv_file",
            type=str,
            help="Chemin du fichier CSV"
        )

        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime les questions du testament concerné avant l'importation"
        )

    def handle(self, *args, **options):

        csv_file = Path(options["csv_file"])

        if not csv_file.exists():
            raise CommandError(
                f"Fichier introuvable : {csv_file}"
            )

        # Déterminer le testament à partir du nom du fichier
        nom_fichier = csv_file.name.lower()

        if "nouveau" in nom_fichier or "testament_nt" in nom_fichier:
            testament = "NT"

        elif "ancien" in nom_fichier or "testament_at" in nom_fichier:
            testament = "AT"

        else:
            raise CommandError(
                "Impossible de déterminer le testament.\n"
                "Le nom du fichier doit contenir 'ancien' ou 'nouveau'."
            )

        colonnes_attendues = [
            "book",
            "question",
            "option1",
            "option2",
            "option3",
            "option4",
            "correct_answer",
            "difficulty",
            "time_limit",
            "explanation",
        ]

        questions = []
        erreurs = []

        self.stdout.write(
            self.style.NOTICE(
                f"📂 Fichier : {csv_file}"
            )
        )

        self.stdout.write(
            self.style.NOTICE(
                f"📖 Testament : {testament}"
            )
        )

        with open(
            csv_file,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as fichier:

            reader = csv.DictReader(fichier)

            if reader.fieldnames != colonnes_attendues:
                raise CommandError(
                    "Les colonnes du CSV sont incorrectes.\n\n"
                    f"Attendu : {colonnes_attendues}\n\n"
                    f"Trouvé : {reader.fieldnames}"
                )

            for numero, row in enumerate(reader, start=2):

                try:
                    book_name = row["book"].strip()
                    question_text = row["question"].strip()

                    option1 = row["option1"].strip()
                    option2 = row["option2"].strip()
                    option3 = row["option3"].strip()
                    option4 = row["option4"].strip()

                    correct_answer = row[
                        "correct_answer"
                    ].strip()

                    difficulty = row[
                        "difficulty"
                    ].strip().lower()

                    time_limit = int(
                        row["time_limit"]
                    )

                    explanation = row[
                        "explanation"
                    ].strip()

                    # -----------------------------
                    # Vérification difficulté
                    # -----------------------------

                    temps_attendu = {
                        "facile": 10,
                        "moyen": 20,
                        "difficile": 30,
                        "expert": 40,
                    }

                    if difficulty not in temps_attendu:
                        raise ValueError(
                            f"Difficulté invalide : {difficulty}"
                        )

                    if time_limit != temps_attendu[difficulty]:
                        raise ValueError(
                            f"time_limit={time_limit} incorrect "
                            f"pour difficulté={difficulty}"
                        )

                    # -----------------------------
                    # Vérification des options
                    # -----------------------------

                    options_qcm = [
                        option1,
                        option2,
                        option3,
                        option4
                    ]

                    if len(set(options_qcm)) != 4:
                        raise ValueError(
                            "Les 4 options doivent être différentes."
                        )

                    if correct_answer not in options_qcm:
                        raise ValueError(
                            "correct_answer ne correspond "
                            "à aucune des 4 options."
                        )

                    # -----------------------------
                    # Récupérer / créer le livre
                    # -----------------------------

                    book, created = Book.objects.get_or_create(
                        name=book_name,
                        defaults={
                            "testament": testament
                        }
                    )

                    # Vérification si le livre existe déjà
                    if not created and book.testament != testament:
                        raise ValueError(
                            f"Le livre '{book_name}' existe déjà "
                            f"dans le testament {book.testament}."
                        )

                    # -----------------------------
                    # Créer la question
                    # -----------------------------

                    questions.append(
                        Question(
                            book=book,
                            question=question_text,
                            option1=option1,
                            option2=option2,
                            option3=option3,
                            option4=option4,
                            correct_answer=correct_answer,
                            difficulty=difficulty,
                            time_limit=time_limit,
                            explanation=explanation,
                            verse_ref=explanation,
                        )
                    )

                except Exception as e:

                    erreurs.append(
                        f"Ligne {numero} : {e}"
                    )

        # -----------------------------
        # Gestion des erreurs
        # -----------------------------

        if erreurs:

            self.stdout.write(
                self.style.ERROR(
                    f"\n❌ {len(erreurs)} erreur(s) détectée(s)."
                )
            )

            for erreur in erreurs[:20]:
                self.stdout.write(
                    self.style.ERROR(
                        f"   {erreur}"
                    )
                )

            if len(erreurs) > 20:
                self.stdout.write(
                    self.style.WARNING(
                        f"   ... et "
                        f"{len(erreurs) - 20} autres erreurs."
                    )
                )

            raise CommandError(
                "Importation annulée."
            )

        # -----------------------------
        # Importation
        # -----------------------------

        with transaction.atomic():

            if options["clear"]:

                questions_a_supprimer = Question.objects.filter(
                    book__testament=testament
                )

                nombre = questions_a_supprimer.count()

                questions_a_supprimer.delete()

                self.stdout.write(
                    self.style.WARNING(
                        f"🗑️ {nombre} questions "
                        f"du testament {testament} supprimées."
                    )
                )

            Question.objects.bulk_create(
                questions,
                batch_size=500
            )

        # -----------------------------
        # Résultat
        # -----------------------------

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"✅ {len(questions)} questions "
                f"importées avec succès !"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"📖 Testament : {testament}"
            )
        )