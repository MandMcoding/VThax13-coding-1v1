# game/admin.py
from django.contrib import admin
from .models import Question, MCQ, Coding, Match

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "question_kind", "difficulty", "created_at", "updated_at")
    list_filter = ("question_kind", "difficulty")
    search_fields = ("title", "descriptor")

@admin.register(MCQ)
class MCQAdmin(admin.ModelAdmin):
    list_display = ("question", "answer_index")
    search_fields = ("question__title",)

@admin.register(Coding)
class CodingAdmin(admin.ModelAdmin):
    list_display = ("question", "time_threshold", "space_threshold")

@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ("id", "player1_id", "player2_id", "status", "created_at")
    list_filter = ("status",)
