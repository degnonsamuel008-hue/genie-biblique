"""
TESTS D'INTÉGRATION — Génie Biblique
======================================
Simulent un vrai utilisateur cliquant dans l'application :
requête HTTP → vue → base de données → réponse.

Lancer avec :
    python manage.py test tests.test_integration
"""

from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def creer_utilisateur(username='sam', password='motdepasse123'):
    return User.objects.create_user(username=username, password=password)


def creer_livre_et_questions(nb=5, difficulte='moyen'):
    from quiz.models import Book, Question
    book = Book.objects.create(name=f'Livre_{difficulte}_{nb}')
    questions = []
    for i in range(nb):
        q = Question.objects.create(
            book=book,
            question=f"Question {i} ?",
            option1="Bonne réponse", option2="B", option3="C", option4="D",
            correct_answer="Bonne réponse",
            difficulty=difficulte,
            time_limit=20,
        )
        questions.append(q)
    return book, questions


# ════════════════════════════════════════════════════════════════════════════
# ACCOUNTS — INSCRIPTION & CONNEXION
# ════════════════════════════════════════════════════════════════════════════

class TestInscription(TestCase):

    def setUp(self):
        self.client = Client()

    def test_page_inscription_accessible(self):
        response = self.client.get(reverse('register'))
        self.assertEqual(response.status_code, 200)

    def test_inscription_valide_cree_utilisateur_et_connecte(self):
        response = self.client.post(reverse('register'), {
            'username': 'nouveau_joueur',
            'email': 'joueur@test.com',
            'password': 'MotDePasse123',
            'password2': 'MotDePasse123',
        })
        self.assertTrue(User.objects.filter(username='nouveau_joueur').exists())
        self.assertEqual(response.status_code, 302)

    def test_inscription_cree_profil_automatiquement(self):
        self.client.post(reverse('register'), {
            'username': 'avec_profil',
            'email': 'profil@test.com',
            'password': 'MotDePasse123',
            'password2': 'MotDePasse123',
        })
        user = User.objects.get(username='avec_profil')
        self.assertTrue(hasattr(user, 'profile'))

    def test_inscription_mots_de_passe_differents_refusee(self):
        self.client.post(reverse('register'), {
            'username': 'test_mdp',
            'email': 'test@test.com',
            'password': 'MotDePasse123',
            'password2': 'AutreMotDePasse',
        })
        self.assertFalse(User.objects.filter(username='test_mdp').exists())

    def test_username_deja_pris_refuse(self):
        creer_utilisateur('existant')
        self.client.post(reverse('register'), {
            'username': 'existant',
            'email': 'autre@test.com',
            'password': 'MotDePasse123',
            'password2': 'MotDePasse123',
        })
        self.assertEqual(User.objects.filter(username='existant').count(), 1)


class TestConnexion(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = creer_utilisateur()

    def test_connexion_valide_redirige(self):
        response = self.client.post(reverse('login'), {
            'username': 'sam', 'password': 'motdepasse123',
        })
        self.assertEqual(response.status_code, 302)

    def test_connexion_invalide_reste_sur_page(self):
        response = self.client.post(reverse('login'), {
            'username': 'sam', 'password': 'mauvais_mdp',
        })
        self.assertEqual(response.status_code, 200)

    def test_deconnexion(self):
        self.client.login(username='sam', password='motdepasse123')
        response = self.client.get(reverse('logout'))
        self.assertEqual(response.status_code, 302)


# ════════════════════════════════════════════════════════════════════════════
# QUIZ — ENTRAÎNEMENT SOLO
# ════════════════════════════════════════════════════════════════════════════

class TestQuizSolo(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = creer_utilisateur()
        self.book, self.questions = creer_livre_et_questions(nb=3)
        self.client.login(username='sam', password='motdepasse123')

    def test_start_requiert_connexion(self):
        client_anon = Client()
        response = client_anon.get(reverse('start'))
        self.assertEqual(response.status_code, 302)

    def test_demarrer_quiz_redirige_vers_question(self):
        response = self.client.post(reverse('start'), {
            'difficulty': 'moyen', 'book': '', 'count': '3',
        })
        self.assertRedirects(response, reverse('question'))

    def test_session_initialisee_apres_start(self):
        self.client.post(reverse('start'), {
            'difficulty': 'moyen', 'count': '3',
        })
        session = self.client.session
        self.assertIn('questions', session)
        self.assertEqual(session['score'], 0)

    def test_bonne_reponse_incremente_score(self):
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        self.assertEqual(self.client.session['score'], 1)

    def test_mauvaise_reponse_ne_change_pas_score(self):
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'B'})
        self.assertEqual(self.client.session['score'], 0)

    def test_fin_quiz_redirige_vers_resultat(self):
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        response = self.client.get(reverse('question'))
        self.assertRedirects(response, reverse('result'))

    def test_score_sauvegarde_en_base(self):
        from quiz.models import Score
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        self.client.get(reverse('result'))
        self.assertTrue(Score.objects.filter(user=self.user).exists())

    def test_xp_ajoutes_au_profil_apres_quiz(self):
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        self.client.get(reverse('result'))
        self.user.profile.refresh_from_db()
        self.assertGreater(self.user.profile.total_xp, 0)

    def test_stats_profil_mises_a_jour(self):
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        self.client.get(reverse('result'))
        self.user.profile.refresh_from_db()
        self.assertEqual(self.user.profile.total_questions_answered, 1)
        self.assertEqual(self.user.profile.total_correct, 1)

    def test_badge_debloque_au_bon_moment(self):
        """Le badge Premier pas doit se débloquer DANS ce même quiz, pas au suivant"""
        from accounts.models import Badge
        Badge.objects.create(
            name='Premier pas', description='Test', icon='🌱',
            badge_type='milestone', condition_key='total_questions_answered',
            condition_value=1, xp_reward=20,
        )
        self.client.post(reverse('start'), {'difficulty': 'moyen', 'count': '1'})
        self.client.post(reverse('question'), {'answer': 'Bonne réponse'})
        response = self.client.get(reverse('result'))
        self.assertEqual(len(response.context['new_badges']), 1)


class TestLeaderboard(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = creer_utilisateur()

    def test_leaderboard_accessible_sans_connexion(self):
        response = self.client.get(reverse('leaderboard'))
        self.assertEqual(response.status_code, 200)

    def test_leaderboard_affiche_les_scores(self):
        from quiz.models import Score
        Score.objects.create(user=self.user, score=8, total=10, difficulty='moyen')
        response = self.client.get(reverse('leaderboard'))
        self.assertIn('top_scores', response.context)
        self.assertEqual(len(response.context['top_scores']), 1)

    def test_leaderboard_affiche_top_joueurs_xp(self):
        self.user.profile.total_xp = 500
        self.user.profile.save()
        response = self.client.get(reverse('leaderboard'))
        self.assertIn('top_users', response.context)


# ════════════════════════════════════════════════════════════════════════════
# GAME — GÉNIE BIBLIQUE ORGANISÉ
# ════════════════════════════════════════════════════════════════════════════

class TestGame(TestCase):

    def setUp(self):
        self.client = Client()
        self.organizer = creer_utilisateur('organisateur', 'pass1234')
        self.joueur2 = creer_utilisateur('joueur2', 'pass1234')
        self.book, self.questions = creer_livre_et_questions(nb=10)

    def test_creer_partie_genere_code(self):
        self.client.login(username='organisateur', password='pass1234')
        response = self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'book': '', 'count': '5', 'time': '15',
        })
        from game.models import Game
        self.assertEqual(Game.objects.count(), 1)
        game = Game.objects.first()
        self.assertRedirects(response, reverse('game_lobby', args=[game.code]))

    def test_organisateur_rejoint_automatiquement(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game, GamePlayer
        game = Game.objects.first()
        self.assertTrue(GamePlayer.objects.filter(game=game, user=self.organizer).exists())

    def test_rejoindre_par_code(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game, GamePlayer
        game = Game.objects.first()

        self.client.logout()
        self.client.login(username='joueur2', password='pass1234')
        self.client.get(reverse('join_game') + f'?code={game.code}')
        self.assertTrue(GamePlayer.objects.filter(game=game, user=self.joueur2).exists())

    def test_rejoindre_code_invalide_redirige(self):
        self.client.login(username='joueur2', password='pass1234')
        response = self.client.get(reverse('join_game') + '?code=XXXXXX')
        self.assertRedirects(response, reverse('game_home'))

    def test_demarrer_partie_avec_deux_joueurs(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game, GamePlayer
        game = Game.objects.first()
        GamePlayer.objects.create(game=game, user=self.joueur2)

        self.client.post(reverse('game_lobby', args=[game.code]))
        game.refresh_from_db()
        self.assertEqual(game.status, 'playing')

    def test_impossible_demarrer_seul(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game
        game = Game.objects.first()
        self.client.post(reverse('game_lobby', args=[game.code]))
        game.refresh_from_db()
        self.assertEqual(game.status, 'waiting')

    def test_api_statut_lobby_retourne_json(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game
        game = Game.objects.first()
        response = self.client.get(reverse('lobby_status', args=[game.code]))
        data = response.json()
        self.assertIn('status', data)
        self.assertIn('player_count', data)


# ════════════════════════════════════════════════════════════════════════════
# BIBLE — PLAN DE LECTURE
# ════════════════════════════════════════════════════════════════════════════

class TestBiblePlan(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = creer_utilisateur()
        self.client.login(username='sam', password='motdepasse123')
        from bible.models import DailyReading
        self.reading = DailyReading.objects.create(
            day_number=1, title='La création', reference='Genèse 1-2',
        )

    def test_page_bible_accessible(self):
        response = self.client.get(reverse('bible_plan'))
        self.assertEqual(response.status_code, 200)

    def test_bible_requiert_connexion(self):
        self.client.logout()
        response = self.client.get(reverse('bible_plan'))
        self.assertEqual(response.status_code, 302)

    def test_marquer_comme_lu_cree_progress(self):
        from bible.models import ReadingProgress
        self.client.get(reverse('mark_done', args=[1]))
        self.assertTrue(
            ReadingProgress.objects.filter(
                user=self.user, reading=self.reading, completed=True
            ).exists()
        )

    def test_marquer_comme_lu_incremente_streak(self):
        self.client.get(reverse('mark_done', args=[1]))
        self.user.profile.refresh_from_db()
        self.assertGreaterEqual(self.user.profile.streak_days, 1)


# ════════════════════════════════════════════════════════════════════════════
# PROFIL
# ════════════════════════════════════════════════════════════════════════════

class TestProfil(TestCase):

    def setUp(self):
        self.client = Client()
        self.user = creer_utilisateur()
        self.client.login(username='sam', password='motdepasse123')

    def test_page_profil_accessible(self):
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 200)

    def test_profil_requiert_connexion(self):
        self.client.logout()
        response = self.client.get(reverse('profile'))
        self.assertEqual(response.status_code, 302)


# ════════════════════════════════════════════════════════════════════════════
# DASHBOARD ADMIN
# ════════════════════════════════════════════════════════════════════════════

class TestDashboard(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = creer_utilisateur('admin_test', 'pass1234')
        self.admin.is_staff = True
        self.admin.save()
        self.simple_user = creer_utilisateur('simple_user', 'pass1234')

    def test_dashboard_refuse_non_staff(self):
        self.client.login(username='simple_user', password='pass1234')
        response = self.client.get(reverse('dashboard_home'))
        self.assertNotEqual(response.status_code, 200)

    def test_dashboard_accessible_staff(self):
        self.client.login(username='admin_test', password='pass1234')
        response = self.client.get(reverse('dashboard_home'))
        self.assertEqual(response.status_code, 200)

    def test_toggle_active_utilisateur(self):
        self.client.login(username='admin_test', password='pass1234')
        self.client.post(reverse('dashboard_toggle_active', args=[self.simple_user.id]))
        self.simple_user.refresh_from_db()
        self.assertFalse(self.simple_user.is_active)

    def test_admin_ne_peut_pas_se_desactiver_lui_meme(self):
        self.client.login(username='admin_test', password='pass1234')
        self.client.post(reverse('dashboard_toggle_active', args=[self.admin.id]))
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
