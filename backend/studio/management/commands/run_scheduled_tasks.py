"""Orquestra lembretes (HU18) e purge de imagens (HU10) para uso interno/manual."""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Executa lembretes por e-mail e limpeza de imagens (HU18 / HU10)."

    def handle(self, *args, **options):
        call_command("send_appointment_reminders")
        call_command("purge_expired_appointment_reference_images")
        self.stdout.write(self.style.SUCCESS("Tarefas agendadas concluidas."))
