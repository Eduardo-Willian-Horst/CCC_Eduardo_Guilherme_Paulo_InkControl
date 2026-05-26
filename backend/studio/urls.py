"""
Rotas da API REST (/api/...). Organizacao por feature em studio/features/.
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

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
from studio.features.auth.password_reset import (
    PasswordResetConfirmView,
    PasswordResetRequestView,
)
from studio.features.clients.controller import ClientViewSet
from studio.features.common.health_controller import health
from studio.features.health_forms.controller import ClientHealthFormViewSet
from studio.features.notifications.controller import InAppNotificationViewSet
from studio.features.studio_org.studio_controller import RegisterStudioView, StudioViewSet
from studio.features.studio_org.studio_settings_controller import StudioSettingsView
from studio.features.studio_org.subscription_controller import (
    StudioSubscriptionCancelView,
    StudioSubscriptionPayView,
    StudioSubscriptionStatusView,
)
from studio.features.tattooers.controller import TattooerViewSet
from studio.features.users.controller import AccountUserViewSet, SystemUserListView

# --- ViewSets (CRUD paginado) ---
router = DefaultRouter()
router.register("clients", ClientViewSet, basename="client")
router.register("tattooers", TattooerViewSet, basename="tattooer")
router.register("appointments", AppointmentViewSet, basename="appointment")
router.register(
    "appointment-change-requests",
    AppointmentChangeRequestViewSet,
    basename="appointment-change-request",
)
router.register("notifications", InAppNotificationViewSet, basename="notification")
router.register("health-forms", ClientHealthFormViewSet, basename="health-form")
router.register("accounts", AccountUserViewSet, basename="account")
router.register("studios", StudioViewSet, basename="studio")

# --- Rotas avulsas: auth, tenant, assinatura ---
urlpatterns = [
    path("health/", health, name="health"),
    path("studios/register/", RegisterStudioView.as_view(), name="studio-register"),
    path("system-users/", SystemUserListView.as_view(), name="system-users"),
    path("auth/register/", RegisterView.as_view(), name="register"),
    path("auth/login/", LoginView.as_view(), name="login"),
    path("auth/me/", MeView.as_view(), name="me"),
    path("auth/logout/", LogoutView.as_view(), name="logout"),
    path(
        "auth/password-reset/request/",
        PasswordResetRequestView.as_view(),
        name="password-reset-request",
    ),
    path(
        "auth/password-reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="password-reset-confirm",
    ),
    path("auth/link-tattooer-profile/", LinkTattooerProfileView.as_view(), name="link-tattooer-profile"),
    path("studio-settings/", StudioSettingsView.as_view(), name="studio-settings"),
    path("studio/subscription/", StudioSubscriptionStatusView.as_view(), name="studio-subscription"),
    path("studio/subscription/pay/", StudioSubscriptionPayView.as_view(), name="studio-subscription-pay"),
    path(
        "studio/subscription/cancel/",
        StudioSubscriptionCancelView.as_view(),
        name="studio-subscription-cancel",
    ),
    path("", include(router.urls)),
]
