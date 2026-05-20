from datetime import time, timedelta

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def link_settings_billing_to_studios(apps, schema_editor):
    Studio = apps.get_model("studio", "Studio")
    StudioSettings = apps.get_model("studio", "StudioSettings")
    StudioBilling = apps.get_model("studio", "StudioBilling")

    legacy_settings = StudioSettings.objects.filter(studio__isnull=True).order_by("pk").first()
    legacy_billing = StudioBilling.objects.filter(studio__isnull=True).order_by("pk").first()

    for studio in Studio.objects.all():
        s_defaults = {
            "opens_at": time(9, 0),
            "closes_at": time(18, 0),
            "offers_consultation": False,
        }
        if legacy_settings and studio.pk == 1:
            s_defaults = {
                "opens_at": legacy_settings.opens_at,
                "closes_at": legacy_settings.closes_at,
                "offers_consultation": getattr(legacy_settings, "offers_consultation", False),
            }
        StudioSettings.objects.update_or_create(studio_id=studio.pk, defaults=s_defaults)

        b_defaults = {"paid_until": django.utils.timezone.now() + timedelta(days=3650)}
        if legacy_billing and studio.pk == 1:
            b_defaults = {
                "paid_until": legacy_billing.paid_until,
                "payment_cancelled_at": legacy_billing.payment_cancelled_at,
                "last_payment_attempt_at": legacy_billing.last_payment_attempt_at,
                "last_payment_attempt_ok": legacy_billing.last_payment_attempt_ok,
                "last_payment_attempt_note": legacy_billing.last_payment_attempt_note,
            }
        StudioBilling.objects.update_or_create(studio_id=studio.pk, defaults=b_defaults)

    StudioSettings.objects.filter(studio__isnull=True).delete()
    StudioBilling.objects.filter(studio__isnull=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0011_legacy_studio_schema_fixup"),
    ]

    operations = [
        migrations.AddField(
            model_name="studiosettings",
            name="offers_consultation",
            field=models.BooleanField(
                default=False,
                help_text="HU12: permite agendar avaliacao antes do servico.",
            ),
        ),
        migrations.AddField(
            model_name="studiosettings",
            name="studio",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="settings",
                to="studio.studio",
            ),
        ),
        migrations.AddField(
            model_name="studiobilling",
            name="studio",
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="billing",
                to="studio.studio",
            ),
        ),
        migrations.RunPython(link_settings_billing_to_studios, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="studiosettings",
            name="studio",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="settings",
                to="studio.studio",
            ),
        ),
        migrations.AlterField(
            model_name="studiobilling",
            name="studio",
            field=models.OneToOneField(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="billing",
                to="studio.studio",
            ),
        ),
    ]
