"""Agendador em processo (APScheduler) quando ENABLE_EMAIL_SCHEDULER=true."""

_scheduler = None


def start_scheduler():
    global _scheduler
    if _scheduler is not None:
        return
    from django.conf import settings

    if not getattr(settings, "ENABLE_EMAIL_SCHEDULER", False):
        return
    from apscheduler.schedulers.background import BackgroundScheduler
    from django.core.management import call_command

    tz = getattr(settings, "TIME_ZONE", "UTC")

    def run_all():
        call_command("run_scheduled_tasks")

    sched = BackgroundScheduler(timezone=tz)
    sched.add_job(
        run_all,
        "interval",
        minutes=int(getattr(settings, "SCHEDULER_INTERVAL_MINUTES", 5)),
        id="inkcontrol_scheduled_tasks",
        replace_existing=True,
    )
    sched.start()
    _scheduler = sched
