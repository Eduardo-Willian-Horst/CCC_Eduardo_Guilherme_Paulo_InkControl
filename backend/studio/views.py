"""
Re-export legado para imports antigos. Rotas canonicas: studio/urls.py.
"""

from studio.features.appointments.controller import (
    AppointmentChangeRequestViewSet,
    AppointmentViewSet,
)
from studio.features.auth.controller import (
    LinkTattooerProfileView,
    LoginView,
    LogoutView,
    MeView,
    RegisterView,
)
from studio.features.clients.controller import ClientViewSet
from studio.features.common.health_controller import health
from studio.features.health_forms.controller import ClientHealthFormViewSet
from studio.features.notifications.controller import InAppNotificationViewSet
from studio.features.studio_org.studio_settings_controller import StudioSettingsView
from studio.features.tattooers.controller import TattooerViewSet

__all__ = [
    "AppointmentChangeRequestViewSet",
    "AppointmentViewSet",
    "ClientHealthFormViewSet",
    "ClientViewSet",
    "InAppNotificationViewSet",
    "LinkTattooerProfileView",
    "LoginView",
    "LogoutView",
    "MeView",
    "RegisterView",
    "StudioSettingsView",
    "TattooerViewSet",
    "health",
]
