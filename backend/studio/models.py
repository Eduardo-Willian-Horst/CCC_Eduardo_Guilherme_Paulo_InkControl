"""
Modelos de dominio do InkControl.

Papeis (UserProfile.role): studio, tattooer, client.
Agendamento (Appointment): maquina de status + studio (tenant) + snapshot de saude (HU06).
Configuracao e cobranca por estudio: StudioSettings / StudioBilling (OneToOne com Studio).
"""

from datetime import time, timedelta

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from rest_framework.authtoken.models import Token


class Studio(models.Model):
    """Tenant: cada estudio de tatuagem no sistema (multi-estudio)."""
    name = models.CharField(max_length=120)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class TokenActivity(models.Model):
    """RNF05: ultima atividade do token; inatividade apaga o token na proxima requisicao."""
    token = models.OneToOneField(
        Token,
        on_delete=models.CASCADE,
        related_name="activity",
    )
    last_activity = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name_plural = "Token activities"

    def __str__(self) -> str:
        return f"Atividade token {self.token_id}"


class UserProfile(models.Model):
    ROLE_STUDIO = "studio"
    ROLE_CLIENT = "client"
    ROLE_TATTOOER = "tattooer"
    ROLE_CHOICES = (
        (ROLE_STUDIO, "Studio"),
        (ROLE_CLIENT, "Client"),
        (ROLE_TATTOOER, "Tattooer"),
    )

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_CLIENT)
    tattooer = models.ForeignKey(
        "Tattooer",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="linked_profiles",
    )
    studio = models.ForeignKey(
        Studio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="profiles",
    )
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    login_locked_until = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return f"{self.user.email or self.user.username} ({self.role})"


class Client(models.Model):
    """Cadastro operacional do cliente (pode existir sem conta de login)."""

    studio = models.ForeignKey(
        Studio,
        on_delete=models.PROTECT,
        related_name="clients",
    )
    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Tattooer(models.Model):
    name = models.CharField(max_length=120)
    artistic_style = models.CharField(max_length=120)
    contact = models.CharField(max_length=120)
    studio = models.ForeignKey(
        Studio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="tattooers",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Appointment(models.Model):
    STATUS_REQUESTED = "requested"
    STATUS_WAITING_BUDGET = "waiting_budget"
    STATUS_CONFIRMED = "confirmed"
    STATUS_IN_PROGRESS = "in_progress"
    STATUS_DONE = "done"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = (
        (STATUS_REQUESTED, "Solicitado"),
        (STATUS_WAITING_BUDGET, "Aguardando Orcamento"),
        (STATUS_CONFIRMED, "Sessao Confirmada"),
        (STATUS_IN_PROGRESS, "Em Andamento"),
        (STATUS_DONE, "Concluido"),
        (STATUS_CANCELLED, "Cancelado"),
    )
    # Transicoes de status permitidas (maquina de estados do agendamento).
    ALLOWED_STATUS_TRANSITIONS = {
        STATUS_REQUESTED: {STATUS_WAITING_BUDGET, STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_WAITING_BUDGET: {STATUS_CONFIRMED, STATUS_CANCELLED},
        STATUS_CONFIRMED: {STATUS_IN_PROGRESS, STATUS_CANCELLED},
        STATUS_IN_PROGRESS: {STATUS_DONE, STATUS_CANCELLED},
        STATUS_DONE: set(),
        STATUS_CANCELLED: set(),
    }

    client = models.ForeignKey(Client, on_delete=models.PROTECT, related_name="appointments")
    tattooer = models.ForeignKey(
        Tattooer,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    studio = models.ForeignKey(
        Studio,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="appointments",
    )
    scheduled_at = models.DateTimeField()
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_REQUESTED,
    )
    KIND_SERVICE = "service"
    KIND_CONSULTATION = "consultation"
    KIND_CHOICES = (
        (KIND_SERVICE, "Servico"),
        (KIND_CONSULTATION, "Avaliacao"),
    )
    appointment_kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_SERVICE,
    )
    reference_image = models.ImageField(
        upload_to="appointment_refs/",
        null=True,
        blank=True,
    )
    source_consultation = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sessions_from_consultation",
    )
    duration_minutes = models.PositiveSmallIntegerField(default=60)
    # Orcamento (fluxo waiting_budget): enviado pelo estudio/tatuador ao cliente.
    budget_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    budget_currency = models.CharField(max_length=3, default="BRL")
    budget_notes = models.TextField(blank=True)
    budget_sent_at = models.DateTimeField(null=True, blank=True)
    budget_sent_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="budgets_sent",
    )
    # HU06: copia imutavel da ficha no create; alteracoes futuras na ficha nao mudam o historico.
    health_snapshot = models.JSONField(default=dict, blank=True)
    reminder_email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-scheduled_at"]

    def __str__(self) -> str:
        return f"{self.client.name} com {self.tattooer.name} em {self.scheduled_at}"

    @classmethod
    def can_transition(cls, from_status: str, to_status: str) -> bool:
        if from_status == to_status:
            return True
        return to_status in cls.ALLOWED_STATUS_TRANSITIONS.get(from_status, set())


class ClientHealthForm(models.Model):
    client = models.OneToOneField(
        Client,
        on_delete=models.CASCADE,
        related_name="health_form",
    )
    allergies = models.TextField(blank=True)
    chronic_diseases = models.TextField(blank=True)
    healing_history = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["client__name"]

    def __str__(self) -> str:
        return f"Ficha de saude de {self.client.name}"


class StudioSettings(models.Model):
    studio = models.OneToOneField(
        Studio,
        on_delete=models.CASCADE,
        related_name="settings",
    )
    opens_at = models.TimeField(default=time(9, 0))
    closes_at = models.TimeField(default=time(18, 0))
    offers_consultation = models.BooleanField(
        default=True,
        help_text="HU12: permite agendar avaliacao antes do servico.",
    )

    class Meta:
        verbose_name_plural = "Studio settings"

    def __str__(self) -> str:
        return f"Expediente {self.studio.name} {self.opens_at}–{self.closes_at}"


class StudioBilling(models.Model):
    studio = models.OneToOneField(
        Studio,
        on_delete=models.CASCADE,
        related_name="billing",
    )
    paid_until = models.DateTimeField()
    payment_cancelled_at = models.DateTimeField(null=True, blank=True)
    last_payment_attempt_at = models.DateTimeField(null=True, blank=True)
    last_payment_attempt_ok = models.BooleanField(null=True, blank=True)
    last_payment_attempt_note = models.CharField(max_length=500, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Studio billing"

    def __str__(self) -> str:
        return f"Mensalidade {self.studio.name} ate {self.paid_until}"

    def is_access_allowed(self, at=None) -> bool:
        at = at or timezone.now()
        return self.paid_until >= at


class AppointmentChangeRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = (
        (STATUS_PENDING, "Pendente"),
        (STATUS_ACCEPTED, "Aceito"),
        (STATUS_REJECTED, "Recusado"),
    )

    appointment = models.ForeignKey(
        Appointment,
        on_delete=models.CASCADE,
        related_name="change_requests",
    )
    requested_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="appointment_change_requests",
    )
    proposed_scheduled_at = models.DateTimeField(null=True, blank=True)
    proposed_payload = models.JSONField(default=dict, blank=True)
    proposed_reference_image = models.ImageField(
        upload_to="appointment_change_refs/",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Alteracao #{self.pk} agendamento {self.appointment_id}"


class InAppNotification(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="in_app_notifications",
    )
    message = models.TextField()
    read = models.BooleanField(default=False)
    link = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Notificacao para {self.user_id}"
