"""
Ficha de saude do cliente (HU06).

Leitura/escrita filtrada por studio_scope: estudio/tatuador so veem clientes ja atendidos.
"""

from django.db.models import Q
from rest_framework import permissions, viewsets

from studio.models import ClientHealthForm, UserProfile
from studio.studio_scope import filter_health_forms_by_studio_access
from studio.permissions import RoleByActionPermission, get_user_role
from studio.serializers import ClientHealthFormSerializer

from studio.features.auth.utils import get_or_create_client_for_app_user


class ClientHealthFormViewSet(viewsets.ModelViewSet):
    queryset = ClientHealthForm.objects.select_related("client").all()
    serializer_class = ClientHealthFormSerializer
    permission_classes = [permissions.IsAuthenticated, RoleByActionPermission]
    role_permissions = {
        "list": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "retrieve": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
        "create": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "partial_update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def get_serializer_context(self):
        ctx = super().get_serializer_context()
        if getattr(self, "action", None) == "create" and self.request.user.is_authenticated:
            ctx["client_health_booking"] = (
                get_user_role(self.request.user) == UserProfile.ROLE_CLIENT
            )
        return ctx

    def perform_create(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    def perform_update(self, serializer):
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            serializer.save(client=client)
        else:
            serializer.save()

    def get_queryset(self):
        queryset = super().get_queryset()
        client_filter = self.request.query_params.get("client")
        q = self.request.query_params.get("q")
        if client_filter and client_filter.isdigit():
            if get_user_role(self.request.user) != UserProfile.ROLE_CLIENT:
                queryset = queryset.filter(client_id=int(client_filter))
        if q:
            queryset = queryset.filter(
                Q(client__name__icontains=q)
                | Q(allergies__icontains=q)
                | Q(chronic_diseases__icontains=q)
                | Q(healing_history__icontains=q)
            )
        if get_user_role(self.request.user) == UserProfile.ROLE_CLIENT:
            email = (self.request.user.email or "").strip()
            if email:
                queryset = queryset.filter(client__email__iexact=email)
        elif get_user_role(self.request.user) in (
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_STUDIO,
        ):
            queryset = filter_health_forms_by_studio_access(
                queryset, self.request.user
            )
        return queryset


__all__ = ["ClientHealthFormViewSet"]
