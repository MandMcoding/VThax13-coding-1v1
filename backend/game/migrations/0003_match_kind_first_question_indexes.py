from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        # 👇 Use your actual 0002 filename (without .py)
        ("game", "0002_match_begin_at_match_countdown_started_at_and_more"),
    ]

    operations = [
        # Add the game mode (mcq|coding)
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
        # Attach the first selected question to the match
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
        # Helpful indexes (optional but nice)
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
