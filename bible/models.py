from django.db import models

from django.contrib.auth.models import User

class  DailyReading(models.Model):
    day_number=models.IntegerField(unique=True)
    title=models.CharField(max_length=200)
    reference=models.CharField(max_length=200)
    summary=models.TextField(blank=True)
    
    
    class Meta:ordering=["day_number"]
    def __str__(self):
        return f"Jour {self.day_number}:{self.reference}"

class  ReadingProgress(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    reading=models.ForeignKey(DailyReading,on_delete=models.CASCADE)
    completed=models.BooleanField(default=False)
    completed_at=models.DateTimeField(null=True,blank=True)
    class Meta:
        unique_together=["user","reading"]