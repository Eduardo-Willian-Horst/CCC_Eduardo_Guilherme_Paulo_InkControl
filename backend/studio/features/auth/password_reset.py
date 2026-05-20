"""API de recuperacao de senha (request + confirm) com throttle para anonimos."""

from rest_framework import permissions, serializers, status

from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView

from studio.features.auth.password_reset_service import (
    confirm_password_reset,
    request_password_reset,
)


class PasswordResetRequestThrottle(AnonRateThrottle):
    rate = "5/hour"


class PasswordResetConfirmThrottle(AnonRateThrottle):
    rate = "10/hour"


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetRequestThrottle]

    def post(self, request):
        ser = PasswordResetRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        request_password_reset(ser.validated_data["email"])
        return Response(
            {
                "detail": "Se existir conta com este e-mail, enviaremos instrucoes para redefinir a senha."
            }
        )


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [PasswordResetConfirmThrottle]

    def post(self, request):
        ser = PasswordResetConfirmSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ok, err = confirm_password_reset(
            ser.validated_data["uid"],
            ser.validated_data["token"],
            ser.validated_data["new_password"],
        )
        if not ok:
            return Response({"detail": err}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"detail": "Senha redefinida com sucesso."})


__all__ = ["PasswordResetRequestView", "PasswordResetConfirmView"]
