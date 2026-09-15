from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from .forms import MonPasswordResetForm # Importe ton formulaire
from accounts.views import register_view,login_view,logout_view,profile_view,change_password_view,ResetPasswordCompleteView,ResetPasswordView,ResetPasswordConfirmView,ResetPasswordDoneView
urlpatterns = [
  path("register/",register_view,name="register"),
  path("login/",login_view,name="login"),
  path("logout/",logout_view,name="logout"),    
  path("profile/",profile_view,name="profile"),
  path('password_reset/', ResetPasswordView.as_view(), name='password_reset'),
    path('password_reset/done/', ResetPasswordDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', ResetPasswordConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', ResetPasswordCompleteView.as_view(), name='password_reset_complete'),

     path("changer_mot_de_passe/",change_password_view,name="change_password"),

]

