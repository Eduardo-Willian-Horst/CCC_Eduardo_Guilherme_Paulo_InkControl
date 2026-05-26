"""Endpoints legados de usuarios bloqueados para estudios."""

from django.contrib.auth.models import User
from rest_framework import permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.serializers import AccountUserSerializer


class SystemUserListView(APIView):
    """Estudios nao podem listar usuarios cadastrados no sistema."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {"detail": "Estudios nao podem acessar usuarios cadastrados no sistema."},
            status=status.HTTP_403_FORBIDDEN,
        )


class AccountUserViewSet(viewsets.GenericViewSet):
    """Estudios nao podem gerenciar contas de login do sistema."""

    queryset = User.objects.none()
    serializer_class = AccountUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def _forbidden(self):
        return Response(
            {"detail": "Estudios nao podem gerenciar usuarios cadastrados no sistema."},
            status=status.HTTP_403_FORBIDDEN,
        )

    def retrieve(self, request, pk=None):
        return self._forbidden()

    def partial_update(self, request, pk=None):
        return self._forbidden()

    def destroy(self, request, pk=None):
        return self._forbidden()


__all__ = ["SystemUserListView", "AccountUserViewSet"]
