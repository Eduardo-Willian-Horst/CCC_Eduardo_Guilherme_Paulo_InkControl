"""RF04: imagens de referencia no perfil do cliente (portfólio); purge apos sessao antiga (HU10)."""

from rest_framework import permissions, viewsets

from studio.models import ClientPortfolioImage, UserProfile
from studio.permissions import RoleByActionPermission, get_user_role
from studio.serializers import ClientPortfolioImageSerializer
from studio.studio_scope import filter_clients_for_user, get_user_studio_id

from studio.features.auth.utils import get_or_create_client_for_app_user


class ClientPortfolioImageViewSet(viewsets.ModelViewSet):
    """RF04: imagens de referencia no perfil do cliente."""

    queryset = ClientPortfolioImage.objects.select_related("client").all()
    serializer_class = ClientPortfolioImageSerializer
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
        "create": {
            UserProfile.ROLE_STUDIO,
            UserProfile.ROLE_CLIENT,
        },
        "update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "partial_update": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
        "destroy": {UserProfile.ROLE_STUDIO, UserProfile.ROLE_CLIENT},
    }

    def perform_create(self, serializer):
        role = get_user_role(self.request.user)
        if role == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            if client is None:
                from rest_framework.exceptions import ValidationError

                raise ValidationError("Cliente nao vinculado ao perfil.")
            serializer.save(client=client)
        else:
            client = serializer.validated_data["client"]
            if client.studio_id != get_user_studio_id(self.request.user):
                from rest_framework.exceptions import ValidationError

                raise ValidationError("Cliente nao pertence ao seu estudio.")
            serializer.save()

    def get_queryset(self):
        qs = super().get_queryset()
        client_id = self.request.query_params.get("client")
        if client_id and str(client_id).isdigit():
            qs = qs.filter(client_id=int(client_id))
        role = get_user_role(self.request.user)
        if role == UserProfile.ROLE_CLIENT:
            client = get_or_create_client_for_app_user(self.request.user)
            return qs.filter(client_id=client.id) if client else qs.none()
        if role in (UserProfile.ROLE_STUDIO, UserProfile.ROLE_TATTOOER):
            from studio.models import Client

            client_ids = filter_clients_for_user(
                Client.objects.all(), self.request.user
            ).values_list("id", flat=True)
            return qs.filter(client_id__in=client_ids)
        return qs.none()


__all__ = ["ClientPortfolioImageViewSet"]
