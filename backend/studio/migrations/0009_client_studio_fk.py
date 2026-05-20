from django.db import migrations, models
import django.db.models.deletion


def backfill_client_studio(apps, schema_editor):
    Client = apps.get_model("studio", "Client")
    Appointment = apps.get_model("studio", "Appointment")
    Studio = apps.get_model("studio", "Studio")
    default_id = Studio.objects.order_by("pk").values_list("pk", flat=True).first() or 1
    for client in Client.objects.filter(studio_id__isnull=True).iterator():
        appt = (
            Appointment.objects.filter(client_id=client.pk)
            .exclude(status="cancelled")
            .order_by("-scheduled_at")
            .first()
        )
        client.studio_id = appt.studio_id if appt and appt.studio_id else default_id
        client.save(update_fields=["studio_id"])


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0008_studio_tenant_settings_billing"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="studio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="clients",
                to="studio.studio",
            ),
        ),
        migrations.RunPython(backfill_client_studio, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="client",
            name="studio",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="clients",
                to="studio.studio",
            ),
        ),
    ]
