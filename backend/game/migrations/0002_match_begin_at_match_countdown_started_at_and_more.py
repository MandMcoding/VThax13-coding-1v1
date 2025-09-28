from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("game", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="p1_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="match",
            name="p2_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="match",
            name="countdown_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="begin_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="match",
            name="kind",
            field=models.CharField(
                max_length=6,
                choices=[("mcq", "Multiple Choice"), ("coding", "Coding")],
                default="mcq",
            ),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="match",
            name="first_question",
            field=models.ForeignKey(
                to="game.question",
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="first_in_matches",
            ),
        ),
        migrations.AddConstraint(
            model_name="match",
            constraint=models.CheckConstraint(
                name="match_not_self",
                condition=models.Q(("player1_id", models.F("player2_id")), _negated=True),
            ),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["status", "created_at"], name="idx_match_status_created"),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["player1_id"], name="idx_match_p1"),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["player2_id"], name="idx_match_p2"),
        ),
        migrations.AddIndex(
            model_name="match",
            index=models.Index(fields=["kind"], name="idx_match_kind"),
        ),
    ]
