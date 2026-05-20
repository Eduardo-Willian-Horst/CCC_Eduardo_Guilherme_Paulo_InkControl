"""CRUD de clientes do estudio (cadastro operacional, tenant via Client.studio)."""

from django.db.models import Q
from rest_framework import permissions, viewsets

from studio.models import Client, UserProfile
from studio.studio_scope import (
    client_has_blocking_appointments,
    filter_clients_for_user,
    get_user_studio_id,
)
from studio.permissions import RoleByActionPermission, get_user_role
from studio.serializers import ClientSerializer


class ClientViewSet(viewsets.ModelViewSet):
    queryset = Client.objects.all()
    serializer_class = ClientSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "retrieve": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER},
        "create": {UserProfile.ROLE_STUDIO},
        "update": {UserProfile.ROLE_STUDIO},
        "partial_update": {UserProfile.ROLE_STUDIO},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def perform_create(self, serializer):
        serializer.save(studio_id=get_user_studio_id(self.request.user))

    def perform_destroy(self, instance):
        from rest_framework.exceptions import ValidationError

        if client_has_blocking_appointments(instance):
            raise ValidationError(
                "Nao e possivel excluir cliente com agendamentos que nao estejam cancelados."
            )
        super().perform_destroy(instance)

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get("q")
        is_active = self.request.query_params.get("is_active")

        if q:
            queryset = queryset.filter(
                Q(name__icontains=q) | Q(phone__icontains=q) | Q(email__icontains=q)
            )
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))

        queryset = filter_clients_for_user(queryset, self.request.user)
        return queryset


__all__ = ["ClientViewSet"]
