from django.urls import path
from . import views
urlpatterns = [
    path("",            views.splash,      name="splash"),
    path("accueil/",    views.home,        name="home"),
    path("start/",      views.start_quiz,  name="start"),
    path("question/",   views.question_view, name="question"),
    path("result/",     views.result_view, name="result"),
    path("leaderboard/",views.leaderboard, name="leaderboard"),
]