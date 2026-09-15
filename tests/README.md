# Tests — Génie Biblique

## Lancer les tests

```bash
# Tous les tests
python manage.py test tests -v 2

# Unitaires uniquement
python manage.py test tests.test_unitaires -v 2

# Intégration uniquement
python manage.py test tests.test_integration -v 2

# Un seul test précis
python manage.py test tests.test_integration.TestQuizSolo.test_badge_debloque_au_bon_moment -v 2
```

## Contenu

**test_unitaires.py** (23 tests) — modèles et fonctions isolés :
- Book, Question, Score (quiz)
- calculate_xp (protection division par zéro, multiplicateurs, bonus)
- UserProfile, niveaux, précision
- Badges (attribution, non-doublon, xp_reward)
- Game, GamePlayer (codes uniques, unicité par partie)
- DailyReading, ReadingProgress (bible)

**test_integration.py** (33 tests) — flux HTTP complets :
- Inscription / connexion / déconnexion
- Quiz solo de bout en bout (démarrage → réponses → résultat → XP → badge)
- Leaderboard (scores + top XP)
- Game multijoueur (créer, rejoindre, démarrer, code invalide)
- Bible (marquer comme lu, streak)
- Profil (accès protégé)
- Dashboard admin (accès staff uniquement, activer/désactiver, auto-protection)

## Placement

Place le dossier `tests/` à la racine du projet, à côté de `manage.py`.
