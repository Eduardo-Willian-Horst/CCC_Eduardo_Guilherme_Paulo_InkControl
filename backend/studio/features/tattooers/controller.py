"""CRUD de tatuadores vinculados ao estudio (tenant)."""

from django.db.models import Q
from rest_framework import permissions, viewsets
from rest_framework.exceptions import ValidationError

from studio.models import Tattooer, UserProfile
from studio.studio_scope import filter_tattooers_for_user, tattooer_has_blocking_appointments
from studio.permissions import RoleByActionPermission
from studio.serializers import TattooerSerializer


class TattooerViewSet(viewsets.ModelViewSet):
    queryset = Tattooer.objects.all()
    serializer_class = TattooerSerializer
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
        "create": {UserProfile.ROLE_STUDIO},
        "update": {UserProfile.ROLE_STUDIO},
        "partial_update": {UserProfile.ROLE_STUDIO},
        "destroy": {UserProfile.ROLE_STUDIO},
    }

    def get_queryset(self):
        queryset = super().get_queryset()
        q = self.request.query_params.get("q")
        is_active = self.request.query_params.get("is_active")

        if q:
            queryset = queryset.filter(
                Q(name__icontains=q)
                | Q(artistic_style__icontains=q)
                | Q(contact__icontains=q)
            )
        if is_active in {"true", "false"}:
            queryset = queryset.filter(is_active=(is_active == "true"))
        queryset = filter_tattooers_for_user(
            queryset,
            self.request.user,
            self.request.query_params.get("studio"),
        )
        return queryset

    def perform_destroy(self, instance):
        if tattooer_has_blocking_appointments(instance):
            raise ValidationError(
                "Nao e possivel excluir tatuador com agendamentos que nao estejam cancelados."
            )
        super().perform_destroy(instance)


__all__ = ["TattooerViewSet"]
