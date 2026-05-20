"""
Corrige db.sqlite3 com schema antigo de studio_studio (default_open_time, etc.).

Aplica a migracao 0011 e as pendentes (0008–0010). Uso (na pasta backend):
    python manage.py reconcile_legacy_database
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

LEGACY_STUDIO_MARKERS = frozenset(
    {
        "default_open_time",
        "default_close_time",
        "booking_cutoff_minutes_before_close",
        "offers_evaluation_appointments",
    }
)


def _legacy_studio_columns() -> set[str]:
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s LIMIT 1",
            ["studio_studio"],
        )
        if not cursor.fetchone():
            return set()
        cursor.execute('PRAGMA table_info("studio_studio")')
        return {row[1] for row in cursor.fetchall()}


class Command(BaseCommand):
    help = "Detecta studio_studio legado e executa migrate studio (0011 + 0008–0010)."

    def handle(self, *args, **options):
        if connection.vendor != "sqlite":
            raise CommandError(
                "Este comando e para SQLite de desenvolvimento (db.sqlite3)."
            )

        cols = _legacy_studio_columns()
        if not (LEGACY_STUDIO_MARKERS & cols):
            self.stdout.write(
                self.style.WARNING(
                    "Nenhum schema legado em studio_studio. Executando migrate studio."
                )
            )
        else:
            self.stdout.write(
                "Schema legado detectado; convertendo via migracao 0011..."
            )

        call_command("migrate", "studio", verbosity=1)
        self.stdout.write(self.style.SUCCESS("Migrations studio aplicadas."))
