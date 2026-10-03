from django.urls import path
from . import views

urlpatterns = [
    path('',                      views.game_home,    name='game_home'),
    path('create/',               views.create_game,  name='create_game'),
    path('join/',                 views.join_game,    name='join_game'),
    path('<str:code>/',           views.game_lobby,   name='game_lobby'),
    path('<str:code>/play/',      views.game_play,    name='game_play'),
    path('<str:code>/result/',    views.game_result,  name='game_result'),
    path('<str:code>/state/',     views.game_state,   name='game_state'),
    path('<str:code>/status/',    views.lobby_status, name='lobby_status'),
]
