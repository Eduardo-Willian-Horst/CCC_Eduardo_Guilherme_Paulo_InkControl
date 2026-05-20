from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


def seed_default_studio(apps, schema_editor):
    Studio = apps.get_model("studio", "Studio")
    studio, _ = Studio.objects.get_or_create(
        pk=1,
        defaults={"name": "Estudio principal", "is_active": True},
    )
    UserProfile = apps.get_model("studio", "UserProfile")
    Tattooer = apps.get_model("studio", "Tattooer")
    Appointment = apps.get_model("studio", "Appointment")
    UserProfile.objects.filter(studio_id__isnull=True).update(studio_id=studio.pk)
    Tattooer.objects.filter(studio_id__isnull=True).update(studio_id=studio.pk)
    Appointment.objects.filter(studio_id__isnull=True).update(studio_id=studio.pk)


class Migration(migrations.Migration):

    dependencies = [
        ("authtoken", "0004_alter_tokenproxy_options"),
        ("studio", "0006_studio_billing_health_snapshot_reminder"),
    ]

    operations = [
        migrations.CreateModel(
            name="Studio",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.CreateModel(
            name="TokenActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("last_activity", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "token",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="activity",
                        to="authtoken.token",
                    ),
                ),
            ],
            options={"verbose_name_plural": "Token activities"},
        ),
        migrations.CreateModel(
            name="ClientPortfolioImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="client_portfolio/")),
                ("caption", models.CharField(blank=True, max_length=200)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "client",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="portfolio_images",
                        to="studio.client",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.AddField(
            model_name="userprofile",
            name="failed_login_count",
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="login_locked_until",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="studio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="profiles",
                to="studio.studio",
            ),
        ),
        migrations.AddField(
            model_name="tattooer",
            name="studio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="tattooers",
                to="studio.studio",
            ),
        ),
        migrations.AddField(
            model_name="appointment",
            name="studio",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="appointments",
                to="studio.studio",
            ),
        ),
        migrations.RunPython(seed_default_studio, migrations.RunPython.noop),
    ]
