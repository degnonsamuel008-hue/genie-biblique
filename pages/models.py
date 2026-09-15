from django.db import models
from django.db import models


class ContactMessage(models.Model):
    name = models.CharField(
        max_length=100,
        verbose_name="Nom complet"
    )

    email = models.EmailField(
        verbose_name="Adresse email"
    )

    subject = models.CharField(
        max_length=200,
        verbose_name="Sujet"
    )

    message = models.TextField(
        verbose_name="Message"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name="Lu"
    )

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Message"
        verbose_name_plural = "Messages"

    def __str__(self):
        return f"{self.name} - {self.subject}"
