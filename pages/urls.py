from django.urls import path
from . import views
urlpatterns = [
       
           path("faq/",      views.faq,  name="faq"),
            path("termes/",   views.terms, name="terms"),
            path("a propos/",     views.about, name="about"),
            path("vie privée/",views.privacy, name="privacy"),
            path("nous contacter/",views.contact, name="contact")
            ]