from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("studio", "0012_appointment_source_consultation"),
    ]

    operations = [
        migrations.DeleteModel(
            name="ClientPortfolioImage",
        ),
    ]
