"""Notificacoes in-app (lista e marcar como lida) por usuario autenticado."""

from rest_framework import permissions, viewsets


from studio.models import InAppNotification, UserProfile
from studio.permissions import RoleByActionPermission
from studio.serializers import InAppNotificationSerializer


class InAppNotificationViewSet(viewsets.ModelViewSet):
    queryset = InAppNotification.objects.all()
    http_method_names = ["get", "patch", "head", "options"]
    serializer_class = InAppNotificationSerializer
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
        "partial_update": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_TATTOOER,
            UserProfile.ROLE_CLIENT,
        },
    }

    def get_queryset(self):
        return InAppNotification.objects.filter(user=self.request.user)


__all__ = ["InAppNotificationViewSet"]
