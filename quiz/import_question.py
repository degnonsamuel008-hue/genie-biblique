import csv
import os
from quiz.models import Question

# Votre dossier sur le bureau
DOSSIER_CSV = r'C:\Users\hp\Desktop\question\\'

def importer_tous_les_livres():
    if not os.path.exists(DOSSIER_CSV):
        print(f"Erreur : Le dossier '{DOSSIER_CSV}' est introuvable.")
        return

    fichiers = [f for f in os.listdir(DOSSIER_CSV) if f.endswith('.csv')]
    
    for nom_fichier in fichiers:
        # Nettoyage du nom du livre (garder seulement le nom sans extension)
        nom_livre = os.path.splitext(nom_fichier)[0]
        chemin = os.path.join(DOSSIER_CSV, nom_fichier)
        
        print(f"--- Importation du livre : {nom_livre} ---")
        
        with open(chemin, newline='', encoding='utf-8') as file:
            # CORRECTION ICI : Utilisez DictReader
            reader = csv.DictReader(file)
            
            for row in reader:
                # Création du dictionnaire de données
                data = {
                    'livre': nom_livre, # Enregistre le nom du livre (string sans extension)
                    'question': row.get('Question') or row.get('verset') or "",
                    'option1': row.get('Option A') or "",
                    'option2': row.get('Option B') or "",
                    'option3': row.get('Option C') or "",
                    'option4': row.get('Option D') or "",
                    'correct_answer': row.get('Bonne Réponse') or "",
                    'difficulty': 'Facile',
                    'timer': 30
                }
                
                # Insertion dans la base uniquement si une question est présente
                if data['question']:
                    Question.objects.create(**data)

    print("Importation terminée avec succès.")

if __name__ == "__main__":
    importer_tous_les_livres()