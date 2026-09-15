from django.urls import path
from bible.views import plan_view, mark_done

urlpatterns = [
    path("", plan_view, name="bible_plan"),
    path("done/<int:day_number>/", mark_done, name="mark_done"),
]
