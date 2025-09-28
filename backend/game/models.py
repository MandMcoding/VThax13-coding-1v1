# game/models.py
from __future__ import annotations
from datetime import timedelta

from django.contrib.postgres.indexes import GinIndex
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Question(models.Model):
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
    question = models.OneToOneField(Question, on_delete=models.CASCADE, primary_key=True, related_name="mcq")
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
    question = models.OneToOneField(Question, on_delete=models.CASCADE, primary_key=True, related_name="coding")
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


# Hard limit for each match after it becomes active
MATCH_DURATION_SECONDS = 60


class Match(models.Model):
    STATUS_CHOICES = (
        ("pending", "pending"),
        ("active", "active"),
        ("finished", "finished"),
        ("cancelled", "cancelled"),
    )

    # who
    player1_id = models.IntegerField()
    player2_id = models.IntegerField()

    # mode
    kind = models.CharField(max_length=6, choices=Question.Kind.choices, default=Question.Kind.MCQ)

    # status/timestamps
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)
    p1_ready = models.BooleanField(default=False)
    p2_ready = models.BooleanField(default=False)
    countdown_started_at = models.DateTimeField(null=True, blank=True)
    begin_at = models.DateTimeField(null=True, blank=True)  # set after both Ready (+3s)

    # JSONB list of question ids (matches DB)
    question_ids = models.JSONField(default=list)

    # Scores (match DB: NOT NULL)
    p1_score = models.IntegerField(default=0)
    p2_score = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(player1_id=models.F("player2_id")), name="match_not_self"),
        ]
        indexes = [
            models.Index(fields=["status", "created_at"], name="idx_match_status_created"),
            models.Index(fields=["player1_id"], name="idx_match_p1"),
            models.Index(fields=["player2_id"], name="idx_match_p2"),
            models.Index(fields=["kind"], name="idx_match_kind"),
        ]

    # Helpers
    def side_for(self, user_id: int):
        if self.player1_id == user_id:
            return 1
        if self.player2_id == user_id:
            return 2
        return None

    def both_ready(self) -> bool:
        return self.p1_ready and self.p2_ready

    def start_countdown_if_ready(self, seconds: int = 3) -> bool:
        if self.both_ready() and not self.begin_at:
            now = timezone.now()
            self.countdown_started_at = now
            self.begin_at = now + timedelta(seconds=seconds)
            return True
        return False

    def time_left_seconds(self, duration: int = MATCH_DURATION_SECONDS) -> int | None:
        """Seconds remaining once match is active; None if not started."""
        if not self.begin_at:
            return None
        remain = int((self.begin_at + timedelta(seconds=duration) - timezone.now()).total_seconds())
        return max(0, remain)

    def maybe_promote_to_active(self) -> bool:
        if self.begin_at and self.status != "active" and timezone.now() >= self.begin_at:
            self.status = "active"
            self.save(update_fields=["status"])
            return True
        return False

    def maybe_finish_if_expired(self, duration: int = MATCH_DURATION_SECONDS) -> bool:
        """
        When time is up, compute p1/p2 scores from game_results and finish the match.
        Safe to call repeatedly (idempotent).
        """
        if not self.begin_at or self.status == "finished":
            return False
        if timezone.now() < self.begin_at + timedelta(seconds=duration):
            return False

        from .models import GameResult  # local import to avoid ordering issues

        p1 = GameResult.objects.filter(match_id=self.id, player_id=self.player1_id, is_correct=True).count()
        p2 = GameResult.objects.filter(match_id=self.id, player_id=self.player2_id, is_correct=True).count()

        self.p1_score = p1
        self.p2_score = p2
        self.status = "finished"
        self.save(update_fields=["p1_score", "p2_score", "status"])
        return True

    # Back-compat helper: first question id from the list
    @property
    def first_question_id(self):
        try:
            return (self.question_ids or [])[0]
        except Exception:
            return None

    def __str__(self):
        return f"Match {self.id}: {self.player1_id} vs {self.player2_id} ({self.status})"


class GameResult(models.Model):
    """
    ORM mapping for the existing public.game_results table.
    managed=False so Django won't try to create/alter it.
    """
    match = models.ForeignKey(
        Match,
        on_delete=models.CASCADE,
        db_column="match_id",
        related_name="results",
    )
    player_id = models.IntegerField()
    question = models.ForeignKey(
        Question,
        on_delete=models.PROTECT,   # DB has RESTRICT; PROTECT is closest in Django
        db_column="question_id",
        related_name="results",
    )
    question_kind = models.CharField(
        max_length=6,
        choices=Question.Kind.choices,
    )
    answer = models.JSONField(null=True, blank=True)
    is_correct = models.BooleanField()
    elapsed_ms = models.IntegerField(null=True, blank=True)
    # DB column is NOT NULL with default now(); leave nullable here so DB default fills it.
    created_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "game_results"
        managed = False  # table already exists; don't let Django manage it
        unique_together = (("match", "player_id", "question"),)
        indexes = [
            models.Index(fields=["match", "player_id", "created_at"], name="idx_results_match_player"),
            models.Index(fields=["player_id", "created_at"], name="idx_results_player_time"),
        ]

    def __str__(self) -> str:
        return f"Result m{self.match_id} u{self.player_id} q{self.question_id} ({'✓' if self.is_correct else '✗'})"

# game/models.py (add at bottom, after GameResult)

class MatchEvent(models.Model):
    class Kind(models.TextChoices):
        MATCHED = "matched", "Matched"
        READY = "ready", "Ready toggled"
        COUNTDOWN = "countdown_started", "Countdown started"
        ACTIVATED = "activated", "Match activated"
        ANSWER = "answer", "Answer submitted"
        FINISHED = "finished", "Match finished"

    match = models.ForeignKey("Match", on_delete=models.CASCADE, related_name="events")
    actor_id = models.IntegerField(null=True, blank=True)   # user who caused it (if any)
    event = models.CharField(max_length=32, choices=Kind.choices)
    payload = models.JSONField(null=True, blank=True)       # any extra context
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "match_events"
        indexes = [models.Index(fields=["match", "created_at"], name="idx_event_match_time")]

from django.db import models

class EloRating(models.Model):
    user_id = models.IntegerField(unique=True, db_index=True)
    elo = models.IntegerField(default=1000, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "elo_ratings"

    def __str__(self):
        return f"user {self.user_id} — {self.elo}"