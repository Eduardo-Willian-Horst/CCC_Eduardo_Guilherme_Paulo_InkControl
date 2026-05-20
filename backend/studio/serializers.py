"""
Serializers DRF: validacao de entrada/saida da API.

Regras de negocio em studio/services/; serializers fazem I/O e chamam os servicos.
"""

from django.contrib.auth.models import User
from rest_framework import serializers
from .booking_utils import can_respond_to_change_request, user_appointment_scope_queryset
from studio.services.appointment_service import (
    prepare_appointment_create,
    service_error_to_drf,
    validate_appointment_write,
)
from studio.services.change_request_service import validate_change_request_write
from studio.services.exceptions import ServiceValidationError
from studio.services.image_validation import validate_uploaded_image
from studio.services.registration_service import register_app_user
from .models import (
    Appointment,
    AppointmentChangeRequest,
    Client,
    ClientHealthForm,
    ClientPortfolioImage,
    InAppNotification,
    Studio,
    StudioSettings,
    Tattooer,
    UserProfile,
)
from .permissions import get_user_role
from .studio_scope import (
    account_user_has_blocking_appointments,
    client_has_blocking_appointments,
    get_user_studio_id,
    tattooer_has_blocking_appointments,
)


class RegisterSerializer(serializers.Serializer):
    """Cadastro publico de cliente ou tatuador (nao cria estudio — use /api/studios/register/)."""

    name = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    role = serializers.ChoiceField(
        choices=[UserProfile.ROLE_CLIENT, UserProfile.ROLE_TATTOOER],
        default=UserProfile.ROLE_CLIENT,
    )

    def validate_email(self, value):
        return value.lower()

    def create(self, validated_data):
        try:
            return register_app_user(
                name=validated_data["name"],
                email=validated_data["email"],
                password=validated_data["password"],
                role=validated_data["role"],
            )
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class ClientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = [
            "id",
            "studio",
            "name",
            "phone",
            "email",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "studio", "created_at", "updated_at"]

    def update(self, instance, validated_data):
        if validated_data.get("is_active") is False and instance.is_active:
            if client_has_blocking_appointments(instance):
                raise serializers.ValidationError(
                    {
                        "is_active": (
                            "Nao e possivel inativar cliente com agendamentos "
                            "que nao estejam cancelados."
                        )
                    }
                )
        return super().update(instance, validated_data)


class TattooerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tattooer
        fields = [
            "id",
            "name",
            "artistic_style",
            "contact",
            "studio",
            "is_active",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def create(self, validated_data):
        request = self.context.get("request")
        if request and request.user.is_authenticated and not validated_data.get("studio"):
            from .models import Studio

            validated_data["studio"] = Studio.objects.get(
                pk=get_user_studio_id(request.user)
            )
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if validated_data.get("is_active") is False and instance.is_active:
            if tattooer_has_blocking_appointments(instance):
                raise serializers.ValidationError(
                    {
                        "is_active": (
                            "Nao e possivel inativar tatuador com agendamentos "
                            "que nao estejam cancelados."
                        )
                    }
                )
        return super().update(instance, validated_data)


class AccountUserSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="profile.role", read_only=True)
    studio_id = serializers.IntegerField(source="profile.studio_id", read_only=True)
    tattooer_id = serializers.IntegerField(source="profile.tattooer_id", read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "name",
            "email",
            "role",
            "is_active",
            "studio_id",
            "tattooer_id",
        ]
        read_only_fields = ["id", "email", "role", "studio_id", "tattooer_id"]

    name = serializers.CharField(source="first_name", required=False)

    def update(self, instance, validated_data):
        first_name = validated_data.pop("first_name", None)
        if first_name is not None:
            instance.first_name = first_name
        is_active = validated_data.get("is_active")
        if is_active is False and instance.is_active:
            if account_user_has_blocking_appointments(instance):
                raise serializers.ValidationError(
                    {
                        "is_active": (
                            "Nao e possivel inativar usuario com agendamentos "
                            "que nao estejam cancelados."
                        )
                    }
                )
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance

    def to_representation(self, instance):
        data = super().to_representation(instance)
        data["name"] = instance.first_name or instance.username
        return data


class ClientPortfolioImageSerializer(serializers.ModelSerializer):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ClientPortfolioImage
        fields = ["id", "client", "image", "image_url", "caption", "created_at"]
        read_only_fields = ["id", "image_url", "created_at"]
        extra_kwargs = {"image": {"required": True}}

    def get_image_url(self, obj):
        if not obj.image:
            return None
        request = self.context.get("request")
        url = obj.image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def validate_image(self, value):
        try:
            validate_uploaded_image(value)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc
        return value


class ClientBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Client
        fields = ["id", "name", "phone", "email"]


class TattooerBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tattooer
        fields = ["id", "name", "artistic_style", "contact"]


class AppointmentReadSerializer(serializers.ModelSerializer):
    client = ClientBriefSerializer(read_only=True)
    tattooer = TattooerBriefSerializer(read_only=True)
    reference_image = serializers.SerializerMethodField()
    health_summary = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "tattooer",
            "scheduled_at",
            "description",
            "status",
            "appointment_kind",
            "duration_minutes",
            "reference_image",
            "health_summary",
            "health_snapshot",
            "budget_amount",
            "budget_currency",
            "budget_notes",
            "budget_sent_at",
            "created_at",
            "updated_at",
        ]

    def get_reference_image(self, obj):
        if not obj.reference_image:
            return None
        request = self.context.get("request")
        url = obj.reference_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def get_health_summary(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        role = get_user_role(request.user)
        if role not in (UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER):
            return None
        hf = getattr(obj.client, "health_form", None)
        if hf is None:
            return None
        allergies = (hf.allergies or "").strip()
        chronic = (hf.chronic_diseases or "").strip()
        return {
            "allergies_preview": allergies[:280],
            "chronic_diseases_preview": chronic[:280],
            "has_alerts": bool(allergies or chronic),
        }


class AppointmentBudgetSerializer(serializers.Serializer):
    """Corpo de POST/PATCH /api/appointments/{id}/budget/."""

    budget_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    budget_notes = serializers.CharField(required=False, allow_blank=True, default="")
    move_to_waiting_budget = serializers.BooleanField(required=False, default=True)


class AppointmentSerializer(serializers.ModelSerializer):
    MAX_IMAGE_BYTES = 5 * 1024 * 1024

    class Meta:
        model = Appointment
        fields = [
            "id",
            "client",
            "tattooer",
            "scheduled_at",
            "description",
            "status",
            "appointment_kind",
            "duration_minutes",
            "reference_image",
            "health_snapshot",
            "budget_amount",
            "budget_currency",
            "budget_notes",
            "budget_sent_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "health_snapshot",
            "budget_amount",
            "budget_currency",
            "budget_notes",
            "budget_sent_at",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "reference_image": {"required": False},
            "description": {"required": False},
            "appointment_kind": {"required": False},
            "duration_minutes": {"required": False},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = self.context or {}
        if self.instance is None and ctx.get("client_booking"):
            self.fields["client"].required = False

    def create(self, validated_data):
        request = self.context.get("request")
        try:
            validated_data = prepare_appointment_create(validated_data, request)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc
        return super().create(validated_data)

    def update(self, instance, validated_data):
        old_status = instance.status
        inst = super().update(instance, validated_data)
        if old_status != inst.status:
            from studio.features.notifications.appointment_mail_events import (
                notify_appointment_status_change,
            )

            notify_appointment_status_change(inst, old_status)
        return inst

    def validate_reference_image(self, value):
        if not value:
            return value
        try:
            validate_uploaded_image(value, "reference_image")
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc
        return value

    def validate(self, attrs):
        try:
            return validate_appointment_write(attrs, self.instance, self.context)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc


class ClientHealthFormSerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientHealthForm
        fields = [
            "id",
            "client",
            "allergies",
            "chronic_diseases",
            "healing_history",
            "notes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ctx = self.context or {}
        if self.instance is None and ctx.get("client_health_booking"):
            self.fields["client"].required = False


class StudioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Studio
        fields = ["id", "name", "is_active", "created_at"]
        read_only_fields = ["id", "created_at"]


class StudioSettingsSerializer(serializers.ModelSerializer):
    studio_id = serializers.IntegerField(source="studio.id", read_only=True)
    studio_name = serializers.CharField(source="studio.name", read_only=True)

    class Meta:
        model = StudioSettings
        fields = [
            "id",
            "studio_id",
            "studio_name",
            "opens_at",
            "closes_at",
            "offers_consultation",
        ]
        read_only_fields = ["id", "studio_id", "studio_name"]


class AppointmentChangeRequestSerializer(serializers.ModelSerializer):
    requested_by_display = serializers.SerializerMethodField()
    you_requested = serializers.SerializerMethodField()
    can_respond = serializers.SerializerMethodField()
    proposed_changes = serializers.DictField(required=False, allow_empty=True, write_only=True)
    proposed_summary = serializers.SerializerMethodField()
    proposed_reference_image_url = serializers.SerializerMethodField()

    class Meta:
        model = AppointmentChangeRequest
        fields = [
            "id",
            "appointment",
            "requested_by_display",
            "you_requested",
            "can_respond",
            "proposed_scheduled_at",
            "proposed_payload",
            "proposed_changes",
            "proposed_summary",
            "proposed_reference_image",
            "proposed_reference_image_url",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requested_by_display",
            "you_requested",
            "can_respond",
            "proposed_summary",
            "proposed_reference_image_url",
            "proposed_payload",
            "status",
            "created_at",
            "updated_at",
        ]
        extra_kwargs = {
            "appointment": {"required": True},
            "proposed_scheduled_at": {"required": False, "allow_null": True},
            "proposed_reference_image": {"required": False, "allow_null": True},
        }

    def get_requested_by_display(self, obj):
        u = obj.requested_by
        name = (u.first_name or "").strip()
        email = (u.email or "").strip()
        if name and email:
            return f"{name} ({email})"
        return email or name or ""

    def get_you_requested(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return obj.requested_by_id == request.user.id

    def get_can_respond(self, obj):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return False
        return can_respond_to_change_request(request.user, obj)

    def get_proposed_summary(self, obj):
        parts = []
        payload = obj.proposed_payload or {}
        if payload.get("scheduled_at"):
            parts.append("Data/hora")
        if "description" in payload:
            parts.append("Descricao")
        if "appointment_kind" in payload:
            parts.append("Modalidade")
        if "tattooer" in payload:
            parts.append("Tatuador")
        if "duration_minutes" in payload:
            parts.append("Duracao")
        if payload.get("clear_reference_image"):
            parts.append("Remover imagem")
        if obj.proposed_reference_image:
            parts.append("Nova imagem")
        return ", ".join(parts) if parts else "Alteracao"

    def get_proposed_reference_image_url(self, obj):
        if not obj.proposed_reference_image:
            return None
        request = self.context.get("request")
        url = obj.proposed_reference_image.url
        if request:
            return request.build_absolute_uri(url)
        return url

    def validate_appointment(self, appointment):
        ctx = self.context or {}
        request = ctx.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Sessao invalida.")
        if not user_appointment_scope_queryset(request.user).filter(pk=appointment.pk).exists():
            raise serializers.ValidationError("Agendamento nao encontrado ou sem permissao.")
        return appointment

    def validate(self, attrs):
        try:
            return validate_change_request_write(attrs, self.context)
        except ServiceValidationError as exc:
            raise service_error_to_drf(exc) from exc


class InAppNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = InAppNotification
        fields = ["id", "message", "read", "link", "created_at"]
        read_only_fields = ["id", "message", "link", "created_at"]
