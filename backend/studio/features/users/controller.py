"""
Contas de login do tenant (HU07/HU08): listar, editar, inativar e excluir.

GET /api/system-users/ agrega clientes, tatuadores e perfis vinculados (HU05).
"""

from django.contrib.auth.models import User
from django.db.models import Q
from rest_framework import permissions, status, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.models import UserProfile
from studio.permissions import get_user_role
from studio.serializers import AccountUserSerializer
from studio.studio_scope import (
    account_user_has_blocking_appointments,
    cleanup_linked_records_for_account,
    get_user_studio_id,
)

from .system_users import build_system_users_queryset


class SystemUserListView(APIView):
    """HU05: GET /api/system-users/?q=&role=client|tattooer|studio&is_active=true|false"""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        q = request.query_params.get("q")
        role = request.query_params.get("role")
        is_active = request.query_params.get("is_active")
        sid = get_user_studio_id(request.user)
        entries = build_system_users_queryset(q, role, is_active, studio_id=sid)
        page_size = 10
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except ValueError:
            page = 1
        start = (page - 1) * page_size
        end = start + page_size
        results = entries[start:end]
        return Response(
            {
                "count": len(entries),
                "next": page + 1 if end < len(entries) else None,
                "previous": page - 1 if page > 1 else None,
                "results": results,
            }
        )


class AccountUserViewSet(viewsets.GenericViewSet):
    """HU07-08: contas de login (User) — inativar/excluir com bloqueio por agendamentos."""

    queryset = User.objects.select_related("profile").order_by("first_name", "email")
    serializer_class = AccountUserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if get_user_role(self.request.user) != UserProfile.ROLE_STUDIO:
            return User.objects.none()
        qs = super().get_queryset()
        q = self.request.query_params.get("q")
        role = self.request.query_params.get("role")
        is_active = self.request.query_params.get("is_active")
        if role in {r[0] for r in UserProfile.ROLE_CHOICES}:
            qs = qs.filter(profile__role=role)
        if is_active in {"true", "false"}:
            qs = qs.filter(is_active=(is_active == "true"))
        if q:
            qs = qs.filter(
                Q(first_name__icontains=q)
                | Q(email__icontains=q)
                | Q(username__icontains=q)
            )
        sid = get_user_studio_id(self.request.user)
        return qs.filter(profile__studio_id=sid)

    def retrieve(self, request, pk=None):
        user = self.get_object()
        return Response(self.get_serializer(user).data)

    def partial_update(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk and request.data.get("is_active") is False:
            raise ValidationError(
                {"is_active": "Nao e possivel inativar a propria conta por esta rota."}
            )
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def destroy(self, request, pk=None):
        user = self.get_object()
        if user.pk == request.user.pk:
            raise ValidationError({"detail": "Nao e possivel excluir a propria conta."})
        if account_user_has_blocking_appointments(user):
            raise ValidationError(
                "Nao e possivel excluir usuario com agendamentos que nao estejam cancelados."
            )
        cleanup_linked_records_for_account(user)
        user.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


__all__ = ["SystemUserListView", "AccountUserViewSet"]
