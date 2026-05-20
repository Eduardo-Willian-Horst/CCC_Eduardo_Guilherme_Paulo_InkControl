"""Health check publico (RNF01); usado por monitoramento e testes de tempo de resposta."""

from rest_framework import permissions

from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def health(request):
    return Response({"status": "ok", "service": "inkcontrol-api"})
