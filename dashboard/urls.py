from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),

    # Utilisateurs
    path('utilisateurs/', views.dashboard_users, name='dashboard_users'),
    path('utilisateurs/<int:user_id>/', views.dashboard_user_detail, name='dashboard_user_detail'),
    path('utilisateurs/<int:user_id>/toggle-actif/', views.dashboard_toggle_active, name='dashboard_toggle_active'),
    path('utilisateurs/<int:user_id>/toggle-admin/', views.dashboard_toggle_staff, name='dashboard_toggle_staff'),

    # Questions
    path('questions/', views.dashboard_questions, name='dashboard_questions'),
    path('questions/<int:question_id>/supprimer/', views.dashboard_delete_question, name='dashboard_delete_question'),

    # Parties
    path('parties/', views.dashboard_games, name='dashboard_games'),
]
