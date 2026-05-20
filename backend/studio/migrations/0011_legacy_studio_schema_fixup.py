"""
Corrige studio_studio legado (default_open_time, etc.) quando 0007 foi faked.

Deve rodar antes de 0008 (que consulta Studio via ORM).
"""

from django.db import migrations


def _column_names(schema_editor, table: str) -> set[str]:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(f'PRAGMA table_info("{table}")')
        return {row[1] for row in cursor.fetchall()}


def _table_exists(schema_editor, table: str) -> bool:
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=%s LIMIT 1",
            [table],
        )
        return cursor.fetchone() is not None


def upgrade_legacy_studio_table(apps, schema_editor):
    if not _table_exists(schema_editor, "studio_studio"):
        return
    cols = _column_names(schema_editor, "studio_studio")
    if "default_open_time" not in cols:
        return

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            "SELECT id, name, created_at FROM studio_studio ORDER BY id"
        )
        rows = cursor.fetchall()

        cursor.execute('ALTER TABLE "studio_studio" RENAME TO "studio_studio_legacy"')
        cursor.execute(
            """
            CREATE TABLE "studio_studio" (
                "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                "name" varchar(120) NOT NULL,
                "is_active" bool NOT NULL,
                "created_at" datetime NOT NULL
            )
            """
        )
        for pk, name, created_at in rows:
            cursor.execute(
                'INSERT INTO "studio_studio" (id, name, is_active, created_at) '
                "VALUES (%s, %s, 1, %s)",
                [pk, (name or "Estudio principal")[:120], created_at],
            )
        cursor.execute('DROP TABLE "studio_studio_legacy"')

    if _table_exists(schema_editor, "studio_studiosubscription"):
        schema_editor.execute('DROP TABLE "studio_studiosubscription"')


def ensure_missing_0007_artifacts(apps, schema_editor):
    """Tabelas/colunas de 0007 ausentes quando a migracao foi apenas faked."""
    Studio = apps.get_model("studio", "Studio")
    studio_id = Studio.objects.order_by("pk").values_list("pk", flat=True).first() or 1

    with schema_editor.connection.cursor() as cursor:
        if not _table_exists(schema_editor, "studio_tokenactivity"):
            cursor.execute(
                """
                CREATE TABLE "studio_tokenactivity" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "last_activity" datetime NOT NULL,
                    "token_id" bigint NOT NULL UNIQUE REFERENCES "authtoken_token" ("key")
                )
                """
            )

        if not _table_exists(schema_editor, "studio_clientportfolioimage"):
            cursor.execute(
                """
                CREATE TABLE "studio_clientportfolioimage" (
                    "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
                    "image" varchar(100) NOT NULL,
                    "caption" varchar(200) NOT NULL,
                    "created_at" datetime NOT NULL,
                    "client_id" bigint NOT NULL REFERENCES "studio_client" ("id")
                )
                """
            )

        if "studio_id" not in _column_names(schema_editor, "studio_tattooer"):
            cursor.execute(
                'ALTER TABLE "studio_tattooer" ADD COLUMN "studio_id" bigint NULL '
                'REFERENCES "studio_studio" ("id") DEFERRABLE INITIALLY DEFERRED'
            )
        if "studio_id" not in _column_names(schema_editor, "studio_appointment"):
            cursor.execute(
                'ALTER TABLE "studio_appointment" ADD COLUMN "studio_id" bigint NULL '
                'REFERENCES "studio_studio" ("id") DEFERRABLE INITIALLY DEFERRED'
            )
        if "failed_login_count" not in _column_names(schema_editor, "studio_userprofile"):
            cursor.execute(
                'ALTER TABLE "studio_userprofile" ADD COLUMN "failed_login_count" '
                "integer unsigned NOT NULL DEFAULT 0"
            )
        if "login_locked_until" not in _column_names(schema_editor, "studio_userprofile"):
            cursor.execute(
                'ALTER TABLE "studio_userprofile" ADD COLUMN "login_locked_until" datetime NULL'
            )

    Tattooer = apps.get_model("studio", "Tattooer")
    Appointment = apps.get_model("studio", "Appointment")
    UserProfile = apps.get_model("studio", "UserProfile")
    Tattooer.objects.filter(studio_id__isnull=True).update(studio_id=studio_id)
    Appointment.objects.filter(studio_id__isnull=True).update(studio_id=studio_id)
    UserProfile.objects.filter(studio_id__isnull=True).update(studio_id=studio_id)


class Migration(migrations.Migration):

    dependencies = [
        ("authtoken", "0004_alter_tokenproxy_options"),
        ("studio", "0007_studio_portfolio_security"),
    ]

    operations = [
        migrations.RunPython(upgrade_legacy_studio_table, migrations.RunPython.noop),
        migrations.RunPython(ensure_missing_0007_artifacts, migrations.RunPython.noop),
    ]
