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
from django.utils import timezone


# ════════════════════════════════════════════════════════════════════════════
# HELPERS
# ════════════════════════════════════════════════════════════════════════════

def creer_utilisateur(username='sam', password='motdepasse123'):
    return User.objects.create_user(username=username, password=password)


def creer_livre_et_questions(nb=5, difficulte='moyen'):
    from quiz.models import Book, Question
    book = Book.objects.create(name=f'Livre_{difficulte}_{nb}', testament='AT')
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
        user = User.objects.get(username='nouveau_joueur')
        self.assertTrue(user.check_password('MotDePasse123'))
        self.assertNotEqual(user.password, 'MotDePasse123')
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

    def test_inscription_mot_de_passe_trop_court_refuse(self):
        response = self.client.post(reverse('register'), {
            'username': 'mot_de_passe_court',
            'email': 'court@test.com',
            'password': '1234567',
            'password2': '1234567',
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            'Le mot de passe doit contenir au moins 8 caractères.',
            response.content.decode(),
        )
        self.assertFalse(User.objects.filter(username='mot_de_passe_court').exists())

    def test_inscription_accepte_un_mot_de_passe_de_huit_caracteres(self):
        response = self.client.post(reverse('register'), {
            'username': 'huit_caracteres',
            'email': 'huit@test.com',
            'password': 'G7!kP2zQ',
            'password2': 'G7!kP2zQ',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username='huit_caracteres').exists())

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

    def test_creation_affiche_tous_les_livres_et_applique_le_filtre(self):
        self.client.login(username='organisateur', password='pass1234')
        response = self.client.get(reverse('create_game'))
        self.assertContains(response, 'Genèse')
        self.assertContains(response, self.book.name)

        response = self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'book': self.book.name, 'count': '5', 'time': '15',
        })
        from game.models import Game
        game = Game.objects.get(organizer=self.organizer)
        self.assertRedirects(response, reverse('game_lobby', args=[game.code]))
        self.assertEqual(game.book_filter, self.book.name)
        self.assertEqual(
            set(game.get_questions()),
            {question.pk for question in self.questions},
        )

    def test_partie_en_attente_expiree_ne_peut_plus_etre_rejointe(self):
        from datetime import timedelta
        from game.models import Game

        game = Game.objects.create(organizer=self.organizer, status='waiting')
        Game.objects.filter(pk=game.pk).update(created_at=timezone.now() - timedelta(hours=25))
        self.client.force_login(self.joueur2)

        response = self.client.get(reverse('join_game'), {'code': game.code})

        game.refresh_from_db()
        self.assertEqual(game.status, 'expired')
        self.assertFalse(game.players.filter(user=self.joueur2).exists())
        self.assertRedirects(response, reverse('game_home'))


class TestDashboardGames(TestCase):

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username='dashboard_admin', email='admin@example.test', password='pass1234',
        )
        from game.models import Game
        self.game = Game.objects.create(organizer=self.admin)

    def test_admin_accede_aux_parties_organisees(self):
        self.client.force_login(self.admin)
        response = self.client.get(reverse('dashboard_games'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.game.code)
        self.assertEqual(response.context['page_obj'].object_list[0], self.game)

    def test_utilisateur_non_administrateur_ne_peut_pas_voir_les_parties(self):
        user = creer_utilisateur('simple_joueur')
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard_games'))

        self.assertEqual(response.status_code, 302)

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

    def test_tous_les_joueurs_recoivent_les_memes_questions_dans_le_meme_ordre(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '5', 'time': '15',
        })
        from game.models import Game, GamePlayer
        game = Game.objects.first()
        GamePlayer.objects.create(game=game, user=self.joueur2)
        game.status = 'playing'
        game.save()

        organizer_client = Client()
        organizer_client.login(username='organisateur', password='pass1234')
        invitee_client = Client()
        invitee_client.login(username='joueur2', password='pass1234')

        organizer_response = organizer_client.get(reverse('game_play', args=[game.code]))
        invitee_response = invitee_client.get(reverse('game_play', args=[game.code]))

        self.assertEqual(
            organizer_response.context['question'].id,
            invitee_response.context['question'].id,
        )
        self.assertEqual(
            organizer_response.context['question'].question,
            invitee_response.context['question'].question,
        )
        self.assertEqual(organizer_response.context['options'], invitee_response.context['options'])
        self.assertEqual(
            organizer_client.get(reverse('game_play', args=[game.code])).context['options'],
            organizer_response.context['options'],
        )

    def test_reponse_correcte_verrouillee_par_le_serveur_et_score_non_falsifiable(self):
        from game.models import Game, GamePlayer, GameAnswer

        game = Game.objects.create(organizer=self.organizer, status='playing', time_per_question=15)
        game.set_questions([question.pk for question in self.questions[:2]])
        game.question_started_at = timezone.now()
        game.save()
        first_player = GamePlayer.objects.create(game=game, user=self.organizer)
        GamePlayer.objects.create(game=game, user=self.joueur2)
        first_client = Client()
        first_client.force_login(self.organizer)
        second_client = Client()
        second_client.force_login(self.joueur2)

        first_client.post(reverse('game_play', args=[game.code]), {
            'answer': 'Bonne réponse', 'question_index': '0',
            'time_taken': '0', 'score': '999999', 'is_correct': 'true',
        })
        first_player.refresh_from_db()
        game.refresh_from_db()
        self.assertEqual(first_player.score, 1)
        self.assertEqual(game.question_winner, first_player)
        self.assertEqual(GameAnswer.objects.get(player=first_player).points, 1)

        second_client.post(reverse('game_play', args=[game.code]), {
            'answer': 'Bonne réponse', 'question_index': '0', 'time_taken': '0',
        })
        self.assertEqual(GamePlayer.objects.get(game=game, user=self.joueur2).score, 0)
        self.assertEqual(GameAnswer.objects.filter(player__game=game, question_id=game.get_questions()[0]).count(), 1)

    def test_reponse_a_une_ancienne_question_est_refusee(self):
        from game.models import Game, GamePlayer, GameAnswer

        game = Game.objects.create(organizer=self.organizer, status='playing', time_per_question=15)
        game.set_questions([question.pk for question in self.questions[:2]])
        game.question_started_at = timezone.now()
        game.save()
        player = GamePlayer.objects.create(game=game, user=self.organizer)
        self.client.force_login(self.organizer)

        self.client.post(reverse('game_play', args=[game.code]), {
            'answer': 'Bonne réponse', 'question_index': '1',
        })

        player.refresh_from_db()
        self.assertEqual(player.score, 0)
        self.assertFalse(GameAnswer.objects.filter(player=player).exists())

    def test_reponse_apres_delai_serveur_est_refusee(self):
        from datetime import timedelta
        from game.models import Game, GamePlayer, GameAnswer

        game = Game.objects.create(organizer=self.organizer, status='playing', time_per_question=10)
        game.set_questions([self.questions[0].pk])
        game.question_started_at = timezone.now() - timedelta(seconds=11)
        game.save()
        player = GamePlayer.objects.create(game=game, user=self.organizer)
        self.client.force_login(self.organizer)

        self.client.post(reverse('game_play', args=[game.code]), {
            'answer': 'Bonne réponse', 'question_index': '0', 'time_taken': '0',
        })

        player.refresh_from_db()
        game.refresh_from_db()
        self.assertEqual(player.score, 0)
        self.assertIsNotNone(game.question_closed_at)
        self.assertFalse(GameAnswer.objects.filter(player=player).exists())

    def test_etat_commun_expose_la_manche_et_le_classement_aux_joueurs(self):
        from game.models import Game, GamePlayer

        game = Game.objects.create(organizer=self.organizer, status='playing')
        game.set_questions([question.pk for question in self.questions[:2]])
        game.question_started_at = timezone.now()
        game.save()
        GamePlayer.objects.create(game=game, user=self.organizer, score=1)
        GamePlayer.objects.create(game=game, user=self.joueur2)
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('game_state', args=[game.code]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['question_index'], 0)
        self.assertEqual(response.json()['ranking'][0]['username'], self.organizer.username)

    def test_progression_synchronisee_et_fin_avec_podium(self):
        from datetime import timedelta
        from game.models import Game, GamePlayer

        game = Game.objects.create(organizer=self.organizer, status='playing', time_per_question=10)
        game.set_questions([question.pk for question in self.questions[:2]])
        game.question_started_at = timezone.now()
        game.save()
        GamePlayer.objects.create(game=game, user=self.organizer)
        GamePlayer.objects.create(game=game, user=self.joueur2)
        organizer_client = Client()
        organizer_client.force_login(self.organizer)
        invitee_client = Client()
        invitee_client.force_login(self.joueur2)

        first_state = organizer_client.get(reverse('game_state', args=[game.code])).json()
        invitee_state = invitee_client.get(reverse('game_state', args=[game.code])).json()
        self.assertEqual(first_state['question_index'], invitee_state['question_index'])

        game.refresh_from_db()
        game.question_started_at = timezone.now() - timedelta(seconds=20)
        game.save(update_fields=['question_started_at'])
        next_state = organizer_client.get(reverse('game_state', args=[game.code])).json()
        invitee_next_state = invitee_client.get(reverse('game_state', args=[game.code])).json()
        self.assertEqual(next_state['question_index'], 1)
        self.assertEqual(next_state['question_index'], invitee_next_state['question_index'])

        game.refresh_from_db()
        game.question_started_at = timezone.now() - timedelta(seconds=20)
        game.save(update_fields=['question_started_at'])
        final_state = organizer_client.get(reverse('game_state', args=[game.code])).json()
        game.refresh_from_db()
        self.assertEqual(final_state['status'], 'finished')
        self.assertEqual(game.status, 'finished')

        result = organizer_client.get(reverse('game_result', args=[game.code]))
        self.assertEqual(result.status_code, 200)
        self.assertContains(result, 'Classement complet')

    def test_resultat_non_affiche_avant_fin_de_partie(self):
        from game.models import Game, GamePlayer

        game = Game.objects.create(organizer=self.organizer, status='playing')
        GamePlayer.objects.create(game=game, user=self.organizer)
        self.client.force_login(self.organizer)

        response = self.client.get(reverse('game_result', args=[game.code]))

        self.assertRedirects(
            response,
            reverse('game_play', args=[game.code]),
            fetch_redirect_response=False,
        )

    def test_seul_le_premier_joueur_correct_gagne_le_point(self):
        self.client.login(username='organisateur', password='pass1234')
        self.client.post(reverse('create_game'), {
            'difficulty': 'moyen', 'count': '2', 'time': '15',
        })
        from game.models import Game, GamePlayer
        game = Game.objects.first()
        GamePlayer.objects.create(game=game, user=self.joueur2)
        game.status = 'playing'
        game.save()

        first_question_id = game.get_questions()[0]
        first_question = self.questions[0]
        if first_question.id != first_question_id:
            first_question = self.questions[0]

        organizer_client = Client()
        organizer_client.login(username='organisateur', password='pass1234')
        invitee_client = Client()
        invitee_client.login(username='joueur2', password='pass1234')

        organizer_response = organizer_client.post(
            reverse('game_play', args=[game.code]),
            {'answer': 'Bonne réponse', 'time_taken': '1.00', 'question_index': '0'},
            follow=True,
        )
        self.assertEqual(organizer_response.status_code, 200)

        organizer_player = game.players.get(user=self.organizer)
        invitee_player = game.players.get(user=self.joueur2)
        self.assertGreater(organizer_player.score, 0)
        self.assertEqual(invitee_player.score, 0)

        invitee_client.post(
            reverse('game_play', args=[game.code]),
            {'answer': 'Bonne réponse', 'time_taken': '1.00'},
        )
        invitee_player.refresh_from_db()
        self.assertEqual(invitee_player.score, 0)


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
