import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("studio", "0009_client_studio_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="budget_amount",
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="budget_currency",
            field=models.CharField(default="BRL", max_length=3),
        ),
        migrations.AddField(
            model_name="appointment",
            name="budget_notes",
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="budget_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="budget_sent_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="budgets_sent",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
