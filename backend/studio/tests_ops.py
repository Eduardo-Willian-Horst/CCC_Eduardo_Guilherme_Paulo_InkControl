"""
Testes operacionais: gate 402, purge, pagamento com e-mail, orcamento, RNF01.
"""

import json
from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework import status
from rest_framework.test import APITestCase

from studio.features.studio_org.org_services import get_billing_for_studio
from studio.models import Appointment, Client, ClientHealthForm, InAppNotification, UserProfile
from studio.tests import register_studio_admin


class SubscriptionGateTests(APITestCase):
    @override_settings(SUBSCRIPTION_GATE_ENABLED=True)
    def test_expired_subscription_returns_402(self):
        r = register_studio_admin(self.client, "gate@inkcontrol.dev", "Gate Studio")
        token = r.data["token"]
        studio_id = r.data["studio"]["id"]
        billing = get_billing_for_studio(studio_id)
        billing.paid_until = timezone.now() - timedelta(days=1)
        billing.save(update_fields=["paid_until", "updated_at"])
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        blocked = self.client.get(reverse("client-list"))
        self.assertEqual(blocked.status_code, 402)
        payload = json.loads(blocked.content.decode())
        self.assertEqual(payload.get("code"), "subscription_required")
        allowed = self.client.get(reverse("studio-subscription"))
        self.assertEqual(allowed.status_code, status.HTTP_200_OK)


class PurgeCommandsTests(APITestCase):
    def test_purge_appointment_reference_image(self):
        r = register_studio_admin(self.client, "purge@inkcontrol.dev", "Purge Studio")
        token = r.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "purge.c@inkcontrol.dev"},
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        buf = BytesIO()
        Image.new("RGB", (4, 4), color="blue").save(buf, format="PNG")
        upload = SimpleUploadedFile("ref.png", buf.getvalue(), content_type="image/png")
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-08-01T10:00:00-03:00",
                "reference_image": upload,
            },
            format="multipart",
        )
        self.assertEqual(appt.status_code, status.HTTP_201_CREATED)
        appt_obj = Appointment.objects.get(pk=appt.data["id"])
        Appointment.objects.filter(pk=appt_obj.pk).update(
            status=Appointment.STATUS_DONE,
            updated_at=timezone.now() - timedelta(days=8)
        )
        appt_obj.refresh_from_db()
        self.assertTrue(appt_obj.reference_image)
        call_command("purge_expired_appointment_reference_images")
        appt_obj.refresh_from_db()
        self.assertFalse(bool(appt_obj.reference_image))

class PaymentEmailTests(APITestCase):
    def test_payment_failure_sends_email(self):
        r = register_studio_admin(self.client, "payfail@inkcontrol.dev", "Pay Fail")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        with patch("studio.services.billing_notifications.send_plain_email") as send_mock:
            resp = self.client.post(
                reverse("studio-subscription-pay"),
                {"simulate_failure": True, "note": "Cartao recusado"},
                format="json",
            )
        self.assertEqual(resp.status_code, 402)
        self.assertTrue(send_mock.called)
        self.assertIn("falha", send_mock.call_args[0][0].lower())


class BudgetEndpointTests(APITestCase):
    def _studio_client_tattooer(self):
        r = register_studio_admin(self.client, "budget-base@inkcontrol.dev", "Budget Base")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "budget.base.c@inkcontrol.dev"},
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        return client, tattooer

    def test_submit_budget_moves_to_waiting_budget(self):
        r = register_studio_admin(self.client, "budget@inkcontrol.dev", "Budget Studio")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "budget.c@inkcontrol.dev"},
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-01T10:00:00-03:00",
                "status": "requested",
            },
            format="json",
        ).data
        budget = self.client.post(
            reverse("appointment-budget", kwargs={"pk": appt["id"]}),
            {"budget_amount": "350.00", "budget_notes": "Sessao 2h"},
            format="json",
        )
        self.assertEqual(budget.status_code, status.HTTP_200_OK)
        self.assertEqual(budget.data["status"], Appointment.STATUS_WAITING_BUDGET)
        self.assertEqual(Decimal(budget.data["budget_amount"]), Decimal("350.00"))

    def test_budget_actions_notify_the_other_side(self):
        r = register_studio_admin(self.client, "budget-notif@inkcontrol.dev", "Budget Notif")
        studio_token = r.data["token"]
        studio_user = User.objects.get(email="budget-notif@inkcontrol.dev")

        self.client.credentials()
        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Notificacao Orcamento",
                "email": "budget.notif.c@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        client_user = User.objects.get(email="budget.notif.c@inkcontrol.dev")
        client = Client.objects.get(email="budget.notif.c@inkcontrol.dev")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client.id,
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-05T10:00:00-03:00",
                "status": "requested",
            },
            format="json",
        ).data

        InAppNotification.objects.all().delete()
        budget = self.client.post(
            reverse("appointment-budget", kwargs={"pk": appt["id"]}),
            {"budget_amount": "350.00", "budget_notes": "Sessao 2h"},
            format="json",
        )
        self.assertEqual(budget.status_code, status.HTTP_200_OK, budget.data)
        self.assertTrue(
            InAppNotification.objects.filter(
                user=client_user,
                message__icontains="orcamento",
                link=f"/agendamentos/{appt['id']}/editar",
            ).exists()
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        accepted = self.client.post(
            reverse("appointment-accept-budget", kwargs={"pk": appt["id"]}),
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        self.assertTrue(
            InAppNotification.objects.filter(
                user=studio_user,
                message__icontains="confirmado",
                link=f"/agendamentos/{appt['id']}/editar",
            ).exists()
        )

    def test_appointment_update_notifies_the_other_side(self):
        r = register_studio_admin(self.client, "update-notif@inkcontrol.dev", "Update Notif")
        studio_token = r.data["token"]

        self.client.credentials()
        self.client.post(
            reverse("register"),
            {
                "name": "Cliente Update Notif",
                "email": "update.notif.c@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        )
        client_user = User.objects.get(email="update.notif.c@inkcontrol.dev")
        client = Client.objects.get(email="update.notif.c@inkcontrol.dev")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client.id,
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-06T10:00:00-03:00",
                "appointment_kind": "consultation",
                "status": "requested",
            },
            format="json",
        ).data
        confirmed = self.client.post(
            reverse("appointment-confirm", kwargs={"pk": appt["id"]}),
            format="json",
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)

        InAppNotification.objects.all().delete()
        updated = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appt["id"]}),
            {"description": "Descricao atualizada"},
            format="json",
        )

        self.assertEqual(updated.status_code, status.HTTP_200_OK, updated.data)
        self.assertTrue(
            InAppNotification.objects.filter(
                user=client_user,
                message__icontains="atualizado",
                link=f"/agendamentos/{appt['id']}/editar",
            ).exists()
        )

    def test_create_rejects_manual_status(self):
        client, tattooer = self._studio_client_tattooer()
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-03T10:00:00-03:00",
                "status": "confirmed",
            },
            format="json",
        )
        self.assertEqual(appt.status_code, status.HTTP_400_BAD_REQUEST)

    def test_budget_only_for_service(self):
        client, tattooer = self._studio_client_tattooer()
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-04T10:00:00-03:00",
                "appointment_kind": "consultation",
            },
            format="json",
        ).data
        budget = self.client.post(
            reverse("appointment-budget", kwargs={"pk": appt["id"]}),
            {"budget_amount": "350.00"},
            format="json",
        )
        self.assertEqual(budget.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_can_upload_reference_image_when_requesting_consultation(self):
        r = register_studio_admin(self.client, "client-image@inkcontrol.dev", "Client Image")
        studio_token = r.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data

        self.client.credentials()
        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Imagem",
                "email": "client.image@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        client = Client.objects.get(email="client.image@inkcontrol.dev")
        ClientHealthForm.objects.create(client=client, allergies="Nenhuma")

        buf = BytesIO()
        Image.new("RGB", (4, 4), color="green").save(buf, format="PNG")
        upload = SimpleUploadedFile("ref.png", buf.getvalue(), content_type="image/png")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        response = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-07T10:00:00-03:00",
                "appointment_kind": "consultation",
                "reference_image": upload,
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        appointment = Appointment.objects.get(pk=response.data["id"])
        self.assertTrue(appointment.reference_image)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        confirmed = self.client.post(
            reverse("appointment-confirm", kwargs={"pk": response.data["id"]}),
            format="json",
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK, confirmed.data)

        buf = BytesIO()
        Image.new("RGB", (4, 4), color="yellow").save(buf, format="PNG")
        service_upload = SimpleUploadedFile(
            "service-ref.png",
            buf.getvalue(),
            content_type="image/png",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        service_response = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-08T10:00:00-03:00",
                "appointment_kind": "service",
                "reference_image": service_upload,
            },
            format="multipart",
        )

        self.assertEqual(service_response.status_code, status.HTTP_201_CREATED, service_response.data)
        service = Appointment.objects.get(pk=service_response.data["id"])
        self.assertTrue(service.reference_image)

    def test_client_accepts_or_rejects_budget_response(self):
        r = register_studio_admin(self.client, "budget-flow@inkcontrol.dev", "Budget Flow")
        studio_token = r.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "Cliente Orcamento", "phone": "1", "email": "budget.flow.c@inkcontrol.dev"},
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        appt = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-01T10:00:00-03:00",
                "status": "requested",
            },
            format="json",
        ).data
        budget = self.client.post(
            reverse("appointment-budget", kwargs={"pk": appt["id"]}),
            {"budget_amount": "350.00", "budget_notes": "Sessao 2h"},
            format="json",
        )
        self.assertEqual(budget.status_code, status.HTTP_200_OK)

        direct_confirm = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appt["id"]}),
            {"status": "confirmed"},
            format="json",
        )
        self.assertEqual(direct_confirm.status_code, status.HTTP_400_BAD_REQUEST)

        self.client.credentials()
        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Orcamento",
                "email": "budget.flow.c@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        accepted = self.client.post(
            reverse("appointment-accept-budget", kwargs={"pk": appt["id"]}),
            format="json",
        )
        self.assertEqual(accepted.status_code, status.HTTP_200_OK, accepted.data)
        self.assertEqual(accepted.data["status"], Appointment.STATUS_CONFIRMED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        appt_rejected = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-09-02T10:00:00-03:00",
                "status": "requested",
            },
            format="json",
        ).data
        self.client.post(
            reverse("appointment-budget", kwargs={"pk": appt_rejected["id"]}),
            {"budget_amount": "400.00"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        rejected = self.client.post(
            reverse("appointment-reject-budget", kwargs={"pk": appt_rejected["id"]}),
            format="json",
        )
        self.assertEqual(rejected.status_code, status.HTTP_200_OK, rejected.data)
        self.assertEqual(rejected.data["status"], Appointment.STATUS_CANCELLED)


class RNF01ResponseTimeTests(APITestCase):
    @override_settings(API_RESPONSE_TIME_BUDGET_MS=2000)
    def test_health_within_budget(self):
        import time

        from django.conf import settings

        start = time.perf_counter()
        r = self.client.get(reverse("health"))
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertLess(elapsed_ms, settings.API_RESPONSE_TIME_BUDGET_MS)
        self.assertIn("X-Response-Time-Ms", r)
