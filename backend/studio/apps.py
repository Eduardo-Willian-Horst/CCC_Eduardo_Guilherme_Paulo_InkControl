import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StudioConfig(AppConfig):
    """App principal; inicia APScheduler se ENABLE_EMAIL_SCHEDULER=true."""
    default_auto_field = "django.db.models.BigAutoField"
    name = "studio"

    def ready(self):
        # Evita import circular: scheduler so sobe apos apps carregadas.
        try:
            from studio.scheduler import start_scheduler

            start_scheduler()
        except Exception:
            logger.exception(
                "Falha ao iniciar APScheduler (ENABLE_EMAIL_SCHEDULER); "
                "use cron com run_scheduled_tasks em producao."
            )
