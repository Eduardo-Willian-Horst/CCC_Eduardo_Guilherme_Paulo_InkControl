"""
Expediente e flags do estudio (HU11/HU12).

GET aceita ?studio=id para clientes consultarem horario e offers_consultation ao agendar.
PATCH apenas admin do proprio tenant.
"""

from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from studio.features.studio_org.org_services import get_settings_for_studio
from studio.models import UserProfile
from studio.permissions import get_user_role
from studio.serializers import StudioSettingsSerializer
from studio.studio_scope import get_user_studio_id


class StudioSettingsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        studio_id = request.query_params.get("studio")
        if studio_id and str(studio_id).isdigit():
            sid = int(studio_id)
        else:
            sid = get_user_studio_id(request.user)
        obj = get_settings_for_studio(sid)
        return Response(StudioSettingsSerializer(obj).data)

    def patch(self, request):
        if get_user_role(request.user) != UserProfile.ROLE_STUDIO:
            return Response(status=status.HTTP_403_FORBIDDEN)
        sid = get_user_studio_id(request.user)
        obj = get_settings_for_studio(sid)
        serializer = StudioSettingsSerializer(obj, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


__all__ = ["StudioSettingsView"]
