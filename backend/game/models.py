from datetime import timedelta

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Question(models.Model):
    """Question metadata shared by MCQ and coding problem types."""
    class Difficulty(models.TextChoices):
        EASY = "easy", "Easy"
        MEDIUM = "medium", "Medium"
        HARD = "hard", "Hard"

    class Kind(models.TextChoices):
        MCQ = "mcq", "Multiple Choice"
        CODING = "coding", "Coding"

    title = models.TextField()
    descriptor = models.TextField(blank=True, null=True)
    difficulty = models.CharField(max_length=8, choices=Difficulty.choices, default=Difficulty.EASY)
    question_kind = models.CharField(max_length=6, choices=Kind.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "questions"
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.title} ({self.get_question_kind_display()})"


class MCQ(models.Model):
    """Multiple choice questions linked 1-1 to Question."""
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, primary_key=True, related_name="mcq"
    )
    choices = models.JSONField()
    answer_index = models.PositiveIntegerField()

    class Meta:
        db_table = "mcq"
        indexes = [GinIndex(fields=["choices"], name="idx_mcq_choices_gin")]

    def clean(self):
        super().clean()
        if not isinstance(self.choices, list):
            raise ValidationError({"choices": "Choices must be stored as a JSON array."})
        if self.answer_index >= len(self.choices):
            raise ValidationError({"answer_index": "Answer index must point to an existing choice."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"MCQ #{self.pk}"


class Coding(models.Model):
    """Coding questions linked 1-1 to Question."""
    question = models.OneToOneField(
        Question, on_delete=models.CASCADE, primary_key=True, related_name="coding"
    )
    template_code = models.TextField()
    prompt = models.TextField()
    test_cases = models.JSONField()
    time_threshold = models.IntegerField(blank=True, null=True)
    space_threshold = models.IntegerField(blank=True, null=True)

    class Meta:
        db_table = "coding"
        indexes = [GinIndex(fields=["test_cases"], name="idx_coding_cases_gin")]

    def clean(self):
        super().clean()
        if not isinstance(self.test_cases, list):
            raise ValidationError({"test_cases": "Test cases must be stored as a JSON array."})

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Coding #{self.pk}"


class Match(models.Model):
    """1v1 game match."""
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

    # ↓ NEW fields for Ready → 3-2-1 → Active
    p1_ready = models.BooleanField(default=False)
    p2_ready = models.BooleanField(default=False)
    countdown_started_at = models.DateTimeField(null=True, blank=True)
    begin_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        # Table name stays the default "game_match" to match your existing DB
        constraints = [
            models.CheckConstraint(
                check=~models.Q(player1_id=models.F("player2_id")),
                name="match_not_self",
            )
        ]

    # Helpers for views
    def side_for(self, user_id: int):
        if self.player1_id == user_id:
            return 1
        if self.player2_id == user_id:
            return 2
        return None

    def both_ready(self) -> bool:
        return self.p1_ready and self.p2_ready

    def start_countdown_if_ready(self, seconds: int = 3) -> bool:
        """Set countdown once, returns True if it changed the model."""
        if self.both_ready() and not self.begin_at:
            now = timezone.now()
            self.countdown_started_at = now
            self.begin_at = now + timedelta(seconds=seconds)
            return True
        return False

    def maybe_promote_to_active(self) -> bool:
        """Flip to active once begin_at has passed. Returns True if changed."""
        if self.begin_at and self.status != "active" and timezone.now() >= self.begin_at:
            self.status = "active"
            self.save(update_fields=["status"])
            return True
        return False

    def __str__(self):
        return f"Match {self.id}: {self.player1_id} vs {self.player2_id} ({self.status})"
