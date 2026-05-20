"""Admin Django para suporte operacional em desenvolvimento."""

from django.contrib import admin

from .models import (
    Appointment,
    AppointmentChangeRequest,
    Client,
    ClientHealthForm,
    ClientPortfolioImage,
    InAppNotification,
    Studio,
    StudioBilling,
    StudioSettings,
    Tattooer,
    TokenActivity,
    UserProfile,
)

admin.site.register(Studio)
admin.site.register(Client)
admin.site.register(UserProfile)
admin.site.register(Tattooer)
admin.site.register(Appointment)
admin.site.register(ClientHealthForm)
admin.site.register(StudioSettings)
admin.site.register(StudioBilling)
admin.site.register(AppointmentChangeRequest)
admin.site.register(InAppNotification)
admin.site.register(ClientPortfolioImage)
admin.site.register(TokenActivity)
