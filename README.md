# ✝ Génie Biblique

Application web de quiz bibliques avec entraînement solo, parties multijoueurs en temps réel,
plan de lecture de la Bible en 1 an, badges, XP et classements.

**Développé par TOGNON Eléazar Dègnon Samuel** — Étudiant en IA/ML, AMA / INSPEI-UNSTIM, Bénin.

---

## Fonctionnalités

- 🔐 Comptes utilisateurs (inscription, connexion, réinitialisation de mot de passe par email)
- 📖 Entraînement solo avec choix du livre biblique et de la difficulté
- 🏆 Génie Biblique organisé — parties multijoueurs avec code d'invitation, QR code, partage réseaux sociaux
- 📅 Plan de lecture de la Bible en 365 jours avec suivi de streak
- 🏅 Système de badges et XP
- 📊 Classement général
- 🛠 Tableau de bord administrateur avec statistiques et graphiques

---

## Stack technique

- **Backend** : Django 4.2
- **Base de données** : PostgreSQL (production) / SQLite (développement)
- **Frontend** : Bootstrap 5, Chart.js, JavaScript vanilla
- **Déploiement** : Render (Gunicorn + Whitenoise)

---

## Installation locale

### 1. Cloner le projet
```bash
git clone https://github.com/degnonsamuel008-hue/geniebiblique.git
cd geniebiblique
```

### 2. Créer l'environnement virtuel
```bash
python -m venv env
source env/bin/activate       # Linux / Mac
env\Scripts\activate          # Windows
```

### 3. Installer les dépendances
```bash
pip install -r requirements.txt
```

### 4. Configurer les variables d'environnement
```bash
cp .env.example .env
```
Ouvre `.env` et remplis tes vraies valeurs (clé secrète, base de données, email).

### 5. Appliquer les migrations
```bash
python manage.py migrate
```

### 6. Créer un compte administrateur
```bash
python manage.py createsuperuser
```

### 7. Importer les données de base
```bash
python manage.py import_badges          # crée les 28 badges
python manage.py import_questions       # importe les questions depuis data/questions.csv
python manage.py import_reading         # importe le plan de lecture 365 jours
```

### 8. Lancer le serveur
```bash
python manage.py runserver
```
Le site est accessible sur `http://127.0.0.1:8000/`

---

## Structure du projet

```
biblegame/
├── biblegame/          # Configuration Django (settings, urls, wsgi)
├── accounts/           # Comptes, profils, avatars, badges
├── quiz/                # Entraînement solo
├── game/                # Génie biblique organisé (multijoueur)
├── bible/               # Plan de lecture en 1 an
├── dashboard/           # Tableau de bord administrateur
├── pages/                # Pages statiques (à propos, FAQ, mentions légales)
├── templates/            # Templates HTML globaux (base.html)
├── static/               # CSS, JS, images
├── data/                  # Fichiers CSV (questions, badges, plan de lecture)
├── requirements.txt
├── Procfile
├── build.sh
└── manage.py
```

---

## Déploiement (Render)

Voir la section **Déploiement** plus bas ou le fichier `DEPLOY.md`.

---

## Tests

```bash
python manage.py test tests -v 2
```

---

## Licence

Projet personnel — tous droits réservés © 2026 TOGNON Samuel.
