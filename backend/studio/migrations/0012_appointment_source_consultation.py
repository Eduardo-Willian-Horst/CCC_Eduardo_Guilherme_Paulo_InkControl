import django.db.models.deletion
from django.db import migrations, models


def enable_consultations(apps, schema_editor):
    StudioSettings = apps.get_model("studio", "StudioSettings")
    StudioSettings.objects.update(offers_consultation=True)


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0010_appointment_budget_fields"),
        ("studio", "0011_legacy_studio_schema_fixup"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="source_consultation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="sessions_from_consultation",
                to="studio.appointment",
            ),
        ),
        migrations.AlterField(
            model_name="studiosettings",
            name="offers_consultation",
            field=models.BooleanField(
                default=True,
                help_text="HU12: permite agendar avaliacao antes do servico.",
            ),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="health_snapshot",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="reminder_email_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="studiobilling",
            name="paid_until",
            field=models.DateTimeField(),
        ),
        migrations.RunPython(enable_consultations, migrations.RunPython.noop),
    ]
