import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StudioConfig(AppConfig):
    """App principal; inicia o scheduler interno junto do runserver."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "studio"

    def ready(self):
        # Evita import circular: scheduler so sobe apos apps carregadas.
        try:
            from studio.scheduler import start_scheduler

            start_scheduler()
        except Exception:
            logger.exception(
                "Falha ao iniciar scheduler interno do InkControl."
            )
