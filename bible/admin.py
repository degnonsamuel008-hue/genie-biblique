from django.contrib import admin
from .models import ReadingProgress,DailyReading
# Register your models here.
@admin.register(DailyReading)
class DailyReadingAdmin(admin.ModelAdmin):
    list_display=["day_number","title","reference"]
    ordering=["day_number"]
    
admin.site.register(ReadingProgress)