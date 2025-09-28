from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models

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
    difficulty = models.CharField(
        max_length=8,
        choices=Difficulty.choices,
        default=Difficulty.EASY,
    )
    question_kind = models.CharField(
        max_length=6,
        choices=Kind.choices,
    )
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
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="mcq",
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
        # Ensure model-level validation runs on direct saves.
        self.full_clean()
        return super().save(*args, **kwargs)
    def __str__(self):
        return f"MCQ #{self.pk}"

class Coding(models.Model):
    """Coding questions linked 1-1 to Question."""
    question = models.OneToOneField(
        Question,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="coding",
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

# Match model for 1v1 games
class Match(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ACTIVE = "active", "Active"
        FINISHED = "finished", "Finished"
        CANCELLED = "cancelled", "Cancelled"

    player1_id = models.IntegerField()
    player2_id = models.IntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"Match {self.id}: {self.player1_id} vs {self.player2_id} ({self.status})"
