from django.contrib import admin
from .models import Question,Book,Score
# Register your models here.
@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display=["question","book","difficulty","time_limit"]
    list_filter=["difficulty","book"]
    search_fields=["question"]
    
admin.site.register(Book)
admin.site.register(Score)
