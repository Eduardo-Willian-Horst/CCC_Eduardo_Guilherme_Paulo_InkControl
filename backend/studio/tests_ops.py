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
from studio.models import Appointment, ClientPortfolioImage, UserProfile
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
                "status": "done",
                "reference_image": upload,
            },
            format="multipart",
        )
        self.assertEqual(appt.status_code, status.HTTP_201_CREATED)
        appt_obj = Appointment.objects.get(pk=appt.data["id"])
        Appointment.objects.filter(pk=appt_obj.pk).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        self.assertTrue(appt_obj.reference_image)
        call_command("purge_expired_appointment_reference_images")
        appt_obj.refresh_from_db()
        self.assertFalse(bool(appt_obj.reference_image))

    def test_purge_client_portfolio_image(self):
        r = register_studio_admin(self.client, "purgep@inkcontrol.dev", "Purge P")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {r.data['token']}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "purgep.c@inkcontrol.dev"},
            format="json",
        ).data
        buf = BytesIO()
        Image.new("RGB", (4, 4), color="green").save(buf, format="PNG")
        upload = SimpleUploadedFile("p.png", buf.getvalue(), content_type="image/png")
        self.client.post(
            reverse("portfolio-image-list"),
            {"client": client["id"], "image": upload},
            format="multipart",
        )
        self.assertEqual(ClientPortfolioImage.objects.filter(client_id=client["id"]).count(), 1)
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        appt_resp = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-07-01T10:00:00-03:00",
                "status": "done",
            },
            format="json",
        )
        self.assertEqual(appt_resp.status_code, status.HTTP_201_CREATED)
        Appointment.objects.filter(pk=appt_resp.data["id"]).update(
            updated_at=timezone.now() - timedelta(days=8)
        )
        call_command("purge_expired_client_portfolio_images")
        self.assertEqual(ClientPortfolioImage.objects.filter(client_id=client["id"]).count(), 0)


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
