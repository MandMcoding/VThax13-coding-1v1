from django.db import models


# Match model for 1v1 games
class Match(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("finished", "finished"),
        ("cancelled", "cancelled"),
    )
    player1_id = models.IntegerField()
    player2_id = models.IntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Match {self.id}: {self.player1_id} vs {self.player2_id} ({self.status})"