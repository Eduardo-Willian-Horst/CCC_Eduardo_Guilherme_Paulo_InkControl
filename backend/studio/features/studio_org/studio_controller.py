"""
Tenant: registro publico de estudio + admin (POST /api/studios/register/) e PATCH do proprio Studio.
"""

from django.contrib.auth.models import User
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.features.auth.token_activity import issue_token_for_user
from studio.features.auth.utils import serialize_auth_user
from studio.features.studio_org.org_services import create_studio_with_org, get_settings_for_studio
from studio.models import Studio, UserProfile
from studio.permissions import get_user_role
from studio.serializers import StudioSerializer
from studio.studio_scope import get_user_studio_id


class RegisterStudioSerializer(serializers.Serializer):
    studio_name = serializers.CharField(max_length=120)
    admin_name = serializers.CharField(max_length=150)
    admin_email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)

    def validate_admin_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("Este e-mail ja esta em uso.")
        return value.lower()


class RegisterStudioView(APIView):
    """Cadastro publico de novo estudio (tenant) + administrador."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        ser = RegisterStudioSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        studio = create_studio_with_org(data["studio_name"])
        email = data["admin_email"]
        user = User.objects.create_user(
            username=email,
            first_name=data["admin_name"],
            email=email,
            password=data["password"],
        )
        UserProfile.objects.create(
            user=user,
            role=UserProfile.ROLE_STUDIO,
            studio=studio,
        )
        token = issue_token_for_user(user)
        settings = get_settings_for_studio(studio.pk)
        return Response(
            {
                "token": token.key,
                "user": serialize_auth_user(user),
                "studio": StudioSerializer(studio).data,
                "settings": {
                    "offers_consultation": settings.offers_consultation,
                    "opens_at": settings.opens_at,
                    "closes_at": settings.closes_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class StudioViewSet(viewsets.ModelViewSet):
    queryset = Studio.objects.all()
    serializer_class = StudioSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        qs = super().get_queryset()
        role = get_user_role(self.request.user)
        if role == UserProfile.ROLE_STUDIO:
            sid = get_user_studio_id(self.request.user)
            return qs.filter(pk=sid)
        return qs.none()

    def partial_update(self, request, *args, **kwargs):
        if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().partial_update(request, *args, **kwargs)


__all__ = ["RegisterStudioView", "StudioViewSet", "RegisterStudioSerializer"]
