from django.contrib import admin
from .models import Game, GamePlayer, GameAnswer


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display  = ['code', 'organizer', 'status', 'player_count',
                     'question_count', 'time_per_question', 'created_at']
    list_filter   = ['status', 'difficulty_filter']
    search_fields = ['code', 'organizer__username']
    readonly_fields = ['code', 'created_at', 'started_at', 'finished_at']


@admin.register(GamePlayer)
class GamePlayerAdmin(admin.ModelAdmin):
    list_display  = ['user', 'game', 'score', 'finished', 'joined_at']
    list_filter   = ['finished']
    search_fields = ['user__username', 'game__code']


@admin.register(GameAnswer)
class GameAnswerAdmin(admin.ModelAdmin):
    list_display  = ['player', 'question_id', 'is_correct', 'points', 'time_taken']
    list_filter   = ['is_correct']
