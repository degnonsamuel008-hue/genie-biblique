"""
TESTS UNITAIRES — Génie Biblique
=================================
Testent modèles et fonctions isolément, sans passer par les vues.

Lancer avec :
    python manage.py test tests.test_unitaires
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta


# ════════════════════════════════════════════════════════════════════════════
# QUIZ — MODÈLES
# ════════════════════════════════════════════════════════════════════════════

class TestBookModel(TestCase):

    def setUp(self):
        from quiz.models import Book
        self.book = Book.objects.create(name='Genèse', testament='AT')

    def test_creation_book(self):
        self.assertEqual(self.book.name, 'Genèse')

    def test_str_book(self):
        self.assertEqual(str(self.book), 'Genèse')

    def test_unicite_nom_book(self):
        from quiz.models import Book
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            Book.objects.create(name='Genèse', testament='AT')


class TestQuestionModel(TestCase):

    def setUp(self):
        from quiz.models import Book, Question
        self.book = Book.objects.create(name='Exode', testament='AT')
        self.question = Question.objects.create(
            book=self.book,
            question="Combien de plaies ont frappé l'Égypte ?",
            option1="7", option2="10", option3="12", option4="5",
            correct_answer="10",
            difficulty="moyen",
            time_limit=20,
        )

    def test_creation_question(self):
        self.assertEqual(self.question.correct_answer, "10")
        self.assertEqual(self.question.difficulty, "moyen")

    def test_taux_reussite_zero_par_defaut(self):
        self.assertEqual(self.question.success_rate, 0)

    def test_taux_reussite_calcule(self):
        self.question.times_answered = 10
        self.question.times_correct = 7
        self.assertEqual(self.question.success_rate, 70)

    def test_champs_disponibles(self):
        """Vérifie que le modèle a bien les champs attendus (pas de created_at)"""
        field_names = [f.name for f in self.question._meta.get_fields()]
        self.assertIn('verse_ref', field_names)
        self.assertNotIn('created_at', field_names)


class TestScoreModel(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='sam', password='pass1234')

    def test_pourcentage_score(self):
        from quiz.models import Score
        score = Score.objects.create(user=self.user, score=8, total=10, difficulty='moyen')
        self.assertEqual(score.percentage, 80)

    def test_pourcentage_zero_si_total_zero(self):
        from quiz.models import Score
        score = Score.objects.create(user=self.user, score=0, total=0, difficulty='facile')
        self.assertEqual(score.percentage, 0)


class TestCalculXP(TestCase):

    def test_xp_zero_si_total_zero(self):
        """total<=0 doit toujours renvoyer 0 (protection contre division par zéro)"""
        from quiz.views import calculate_xp
        self.assertEqual(calculate_xp(0, 0, 'moyen'), 0)

    def test_xp_multiplicateur_expert_superieur_facile(self):
        from quiz.views import calculate_xp
        xp_facile = calculate_xp(10, 10, 'facile')
        xp_expert = calculate_xp(10, 10, 'expert')
        self.assertGreater(xp_expert, xp_facile)

    def test_xp_bonus_score_parfait(self):
        from quiz.views import calculate_xp
        xp_parfait = calculate_xp(10, 10, 'moyen')
        xp_incomplet = calculate_xp(9, 10, 'moyen')
        self.assertGreater(xp_parfait, xp_incomplet)

    def test_xp_gere_valeurs_none(self):
        """La fonction doit gérer score/total à None sans planter"""
        from quiz.views import calculate_xp
        xp = calculate_xp(None, None, 'moyen')
        self.assertEqual(xp, 0)

    def test_xp_ne_devient_jamais_negatif(self):
        from quiz.views import calculate_xp
        xp = calculate_xp(0, 10, 'facile')
        self.assertGreaterEqual(xp, 0)


# ════════════════════════════════════════════════════════════════════════════
# ACCOUNTS — PROFIL ET BADGES
# ════════════════════════════════════════════════════════════════════════════

class TestUserProfile(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='sam_test', password='pass1234')

    def test_profil_cree_automatiquement(self):
        """Le signal post_save doit créer le UserProfile à l'inscription"""
        self.assertTrue(hasattr(self.user, 'profile'))

    def test_niveau_neophyte_par_defaut(self):
        self.assertIn('Néophyte', self.user.profile.level)

    def test_niveau_change_avec_xp(self):
        profile = self.user.profile
        profile.total_xp = 1000
        self.assertIn('Sage', profile.level)

    def test_taux_precision_zero_si_aucune_reponse(self):
        self.assertEqual(self.user.profile.accuracy_rate, 0)

    def test_taux_precision_calcule(self):
        profile = self.user.profile
        profile.total_questions_answered = 20
        profile.total_correct = 15
        self.assertEqual(profile.accuracy_rate, 75)


class TestBadges(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='badge_test', password='pass1234')
        from accounts.models import Badge
        self.badge = Badge.objects.create(
            name='Premier pas',
            description='Répondre à sa première question',
            icon='🌱',
            badge_type='milestone',
            condition_key='total_questions_answered',
            condition_value=1,
            xp_reward=20,
        )

    def test_badge_attribue_si_condition_remplie(self):
        from accounts.utils import check_badges
        profile = self.user.profile
        profile.total_questions_answered = 1
        profile.save()
        nouveaux = check_badges(self.user, profile)
        self.assertEqual(len(nouveaux), 1)
        self.assertEqual(nouveaux[0].name, 'Premier pas')

    def test_badge_non_attribue_si_condition_non_remplie(self):
        from accounts.utils import check_badges
        profile = self.user.profile
        nouveaux = check_badges(self.user, profile)
        self.assertEqual(len(nouveaux), 0)

    def test_badge_jamais_attribue_deux_fois(self):
        from accounts.utils import check_badges
        from accounts.models import UserBadge
        profile = self.user.profile
        profile.total_questions_answered = 5
        profile.save()
        check_badges(self.user, profile)
        check_badges(self.user, profile)
        count = UserBadge.objects.filter(user=self.user, badge=self.badge).count()
        self.assertEqual(count, 1)

    def test_xp_reward_ajoute_lors_du_badge(self):
        from accounts.utils import check_badges
        profile = self.user.profile
        profile.total_questions_answered = 1
        profile.save()
        xp_avant = profile.total_xp
        check_badges(self.user, profile)
        profile.refresh_from_db()
        self.assertEqual(profile.total_xp, xp_avant + self.badge.xp_reward)


# ════════════════════════════════════════════════════════════════════════════
# GAME — MODÈLES
# ════════════════════════════════════════════════════════════════════════════

class TestGameModel(TestCase):

    def setUp(self):
        self.organizer = User.objects.create_user(username='organisateur', password='pass1234')
        from game.models import Game
        self.game = Game.objects.create(organizer=self.organizer, time_per_question=15)

    def test_code_genere_automatiquement(self):
        self.assertEqual(len(self.game.code), 6)

    def test_statut_initial_waiting(self):
        self.assertEqual(self.game.status, 'waiting')

    def test_set_get_questions(self):
        ids = [1, 2, 3]
        self.game.set_questions(ids)
        self.game.save()
        self.assertEqual(self.game.get_questions(), ids)

    def test_codes_uniques_entre_parties(self):
        from game.models import Game
        game2 = Game.objects.create(organizer=self.organizer)
        self.assertNotEqual(self.game.code, game2.code)

    def test_player_count(self):
        from game.models import GamePlayer
        self.assertEqual(self.game.player_count, 0)
        GamePlayer.objects.create(game=self.game, user=self.organizer)
        self.assertEqual(self.game.player_count, 1)


class TestGameRoundHelpers(TestCase):

    def setUp(self):
        from game.models import Game
        from quiz.models import Book, Question
        self.user = User.objects.create_user(username='round_test', password='pass1234')
        book = Book.objects.create(name='Psaumes', testament='AT')
        self.question = Question.objects.create(
            book=book, question='Question partagée ?',
            option1='A', option2='B', option3='C', option4='D',
            correct_answer='A', difficulty='moyen',
        )
        self.game = Game.objects.create(
            organizer=self.user, status='playing', time_per_question=10,
            questions_json=f'[{self.question.pk}]',
        )

    def test_ordre_options_est_persistant_pour_la_partie(self):
        from game.views import _ordered_options
        from unittest.mock import patch

        with patch('game.views.random.shuffle', side_effect=lambda options: options.reverse()):
            first_view = _ordered_options(self.game, self.question)
        self.game.refresh_from_db()
        with patch('game.views.random.shuffle', side_effect=AssertionError('ordre déjà persisté')):
            second_view = _ordered_options(self.game, self.question)

        self.assertEqual(first_view, second_view)
        self.assertEqual(first_view, ['D', 'C', 'B', 'A'])

    def test_manche_se_termine_a_partir_de_l_horloge_serveur(self):
        from game.views import advance_game_if_due

        started = timezone.now() - timedelta(seconds=11)
        self.game.question_started_at = started
        self.game.save(update_fields=['question_started_at'])
        advance_game_if_due(self.game, now=timezone.now())

        self.game.refresh_from_db()
        self.assertIsNotNone(self.game.question_closed_at)
        self.assertEqual(self.game.status, 'playing')


class TestWaitingGameExpiry(TestCase):

    def test_expire_seulement_les_parties_en_attente_de_plus_de_24_heures(self):
        from datetime import timedelta
        from game.models import Game
        from game.utils import expire_stale_games

        organizer = User.objects.create_user(username='expiry_admin', password='pass1234')
        old_waiting = Game.objects.create(organizer=organizer, status='waiting')
        old_playing = Game.objects.create(organizer=organizer, status='playing')
        recent_waiting = Game.objects.create(organizer=organizer, status='waiting')
        cutoff = timezone.now() - timedelta(hours=24, minutes=1)
        Game.objects.filter(pk__in=[old_waiting.pk, old_playing.pk]).update(created_at=cutoff)

        expired_count = expire_stale_games()

        old_waiting.refresh_from_db()
        old_playing.refresh_from_db()
        recent_waiting.refresh_from_db()
        self.assertEqual(expired_count, 1)
        self.assertEqual(old_waiting.status, 'expired')
        self.assertEqual(old_playing.status, 'playing')
        self.assertEqual(recent_waiting.status, 'waiting')


class TestGamePlayer(TestCase):

    def setUp(self):
        self.organizer = User.objects.create_user(username='org2', password='pass1234')
        self.user = User.objects.create_user(username='joueur1', password='pass1234')
        from game.models import Game, GamePlayer
        self.game = Game.objects.create(organizer=self.organizer)
        self.player = GamePlayer.objects.create(game=self.game, user=self.user)

    def test_score_initial_zero(self):
        self.assertEqual(self.player.score, 0)

    def test_un_joueur_ne_rejoint_pas_deux_fois(self):
        from game.models import GamePlayer
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            GamePlayer.objects.create(game=self.game, user=self.user)


# ════════════════════════════════════════════════════════════════════════════
# BIBLE — MODÈLES
# ════════════════════════════════════════════════════════════════════════════

class TestBibleModels(TestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='lecteur', password='pass1234')
        from bible.models import DailyReading
        self.reading = DailyReading.objects.create(
            day_number=1, title='La création',
            reference='Genèse 1-2', summary='Dieu crée le monde.'
        )

    def test_creation_reading(self):
        self.assertEqual(self.reading.day_number, 1)

    def test_jour_unique(self):
        from bible.models import DailyReading
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            DailyReading.objects.create(day_number=1, title='Doublon', reference='X')

    def test_progress_non_complete_par_defaut(self):
        from bible.models import ReadingProgress
        progress = ReadingProgress.objects.create(user=self.user, reading=self.reading)
        self.assertFalse(progress.completed)
