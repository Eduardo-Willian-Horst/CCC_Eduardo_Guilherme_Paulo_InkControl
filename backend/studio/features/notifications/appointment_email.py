"""
Destinatarios de e-mail transacional de agendamento (HU19).

Apenas admins do mesmo tenant (appointment.studio) recebem copia — nao todos os studios.
"""

from django.contrib.auth.models import User

from studio.models import Appointment, UserProfile


def recipient_emails_for_appointment(appointment: Appointment) -> list[str]:
    emails: set[str] = set()
    ce = (appointment.client.email or "").strip()
    if ce:
        emails.add(ce.lower())
    contact = (appointment.tattooer.contact or "").strip()
    if "@" in contact:
        emails.add(contact.lower())
    studio_id = appointment.studio_id
    admins = User.objects.filter(profile__role=UserProfile.ROLE_STUDIO)
    if studio_id:
        admins = admins.filter(profile__studio_id=studio_id)
    for u in admins.only("email"):
        e = (u.email or "").strip()
        if e:
            emails.add(e.lower())
    return sorted(emails)

