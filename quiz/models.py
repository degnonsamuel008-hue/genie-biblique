from django.db import models

from django.contrib.auth.models import User
class Book(models.Model):
    name=models.CharField(max_length=100,unique=True)
    testament=models.CharField(max_length=2,choices=[("AT","Ancien Testament"),("NT","Nouveau Testament")])
    
    def __str__(self):
        return self.name
class Question(models.Model):
    DIFF = [
        ("facile", "Facile"),
        ("moyen", "Moyen"),
        ("difficile", "Difficile"),
        ("expert", "Expert"),
    ]

    book = models.ForeignKey(Book, on_delete=models.CASCADE)

    question = models.TextField()

    option1 = models.TextField()
    option2 = models.TextField()
    option3 = models.TextField()
    option4 = models.TextField()

    correct_answer = models.TextField()

    difficulty = models.CharField(
        max_length=20,
        choices=DIFF
    )

    time_limit = models.IntegerField(default=30)

    times_answered = models.PositiveIntegerField(default=0)
    times_correct = models.PositiveIntegerField(default=0)

    explanation = models.TextField(blank=True)

    verse_ref = models.CharField(
        max_length=100,
        blank=True
    )

    @property
    def success_rate(self):
        if self.times_answered == 0:
            return 0
        return round(
            (self.times_correct / self.times_answered) * 100
        )

    def __str__(self):
        return self.question[:60]

class Score(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE, null=True, blank=True)
    score=models.IntegerField()
    total=models.IntegerField()
    difficulty=models.CharField(max_length=20)
    xp_earned=models.IntegerField(default=0)
    created_at=models.DateTimeField(auto_now_add=True) 
    
    @property
    def  percentage(self):
        return round(self.score/self.total *100) if self.total else 0
    
    class Meta:
        ordering=["-score","-created_at"]
      