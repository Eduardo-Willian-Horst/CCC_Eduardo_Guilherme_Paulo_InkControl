"""
Testes de API do app studio.

Helper register_studio_admin: cria tenant via POST /api/studios/register/.
"""

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from studio.models import (
    Appointment,
    Client,
    ClientHealthForm,
    InAppNotification,
    Tattooer,
    TokenActivity,
    UserProfile,
)


def register_studio_admin(client, email, studio_name="Estudio Teste", name="Admin"):
    return client.post(
        reverse("studio-register"),
        {
            "studio_name": studio_name,
            "admin_name": name,
            "admin_email": email,
            "password": "SenhaForte123",
        },
        format="json",
    )


class AuthAndClientsAPITests(APITestCase):
    def test_register_login_and_manage_clients(self):
        register_response = register_studio_admin(
            self.client, "studio.teste@inkcontrol.dev", "Estudio A"
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        me_response = self.client.get(reverse("me"))
        self.assertEqual(me_response.status_code, status.HTTP_200_OK)
        self.assertEqual(me_response.data["email"], "studio.teste@inkcontrol.dev")

        create_client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Maria",
                "phone": "54999999999",
                "email": "maria@cliente.com",
                "is_active": True,
            },
            format="json",
        )
        self.assertEqual(create_client_response.status_code, status.HTTP_201_CREATED)

        list_clients_response = self.client.get(reverse("client-list"))
        self.assertEqual(list_clients_response.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(len(list_clients_response.data["results"]), 1)

    def test_manage_tattooers_and_appointment_conflict(self):
        register_response = register_studio_admin(
            self.client, "studio@inkcontrol.dev", "Estudio B"
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Agenda",
                "phone": "54988888888",
                "email": "cliente.agenda@inkcontrol.dev",
            },
            format="json",
        )
        self.assertEqual(client_response.status_code, status.HTTP_201_CREATED)

        tattooer_response = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador 1",
                "artistic_style": "Old School",
                "contact": "54977777777",
            },
            format="json",
        )
        self.assertEqual(tattooer_response.status_code, status.HTTP_201_CREATED)

        appointment_payload = {
            "client": client_response.data["id"],
            "tattooer": tattooer_response.data["id"],
            "scheduled_at": "2026-06-10T14:00:00-03:00",
            "description": "Fechamento braco",
        }
        first_appointment = self.client.post(
            reverse("appointment-list"),
            appointment_payload,
            format="json",
        )
        self.assertEqual(first_appointment.status_code, status.HTTP_201_CREATED)

        conflicting_appointment = self.client.post(
            reverse("appointment-list"),
            appointment_payload,
            format="json",
        )
        self.assertEqual(conflicting_appointment.status_code, status.HTTP_400_BAD_REQUEST)

    def test_client_appointment_create_notifies_studio(self):
        register_response = register_studio_admin(
            self.client, "studio.notif@inkcontrol.dev", "Estudio Notificacao"
        )
        studio_user = User.objects.get(email="studio.notif@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {register_response.data['token']}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuadora Notificacao",
                "artistic_style": "Fineline",
                "contact": "54977771111",
            },
            format="json",
        ).data

        self.client.credentials()
        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Notificacao",
                "email": "cliente.notif@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        client_record = Client.objects.get(email="cliente.notif@inkcontrol.dev")
        ClientHealthForm.objects.create(client=client_record, allergies="Nenhuma")

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        response = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-10-09T10:00:00-03:00",
                "appointment_kind": "consultation",
                "description": "Avaliacao com imagem de referencia",
            },
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.data)
        self.assertTrue(
            InAppNotification.objects.filter(
                user=studio_user,
                link=f"/agendamentos/{response.data['id']}/editar",
                read=False,
            ).exists()
        )

    def test_appointment_period_filters_and_status_transition_rules(self):
        register_response = register_studio_admin(
            self.client, "agenda@inkcontrol.dev", "Estudio Agenda"
        )
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED)
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_response = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Filtro",
                "phone": "54966666666",
                "email": "cliente.filtro@inkcontrol.dev",
            },
            format="json",
        )
        tattooer_response = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador Filtro",
                "artistic_style": "Fine Line",
                "contact": "54955555555",
            },
            format="json",
        )
        self.assertEqual(client_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(tattooer_response.status_code, status.HTTP_201_CREATED)

        base_payload = {
            "client": client_response.data["id"],
            "tattooer": tattooer_response.data["id"],
            "description": "Sessao teste",
            "status": "requested",
            "appointment_kind": "consultation",
        }
        first_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-06-10T14:00:00-03:00"},
            format="json",
        )
        second_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-06-11T14:00:00-03:00"},
            format="json",
        )
        third_response = self.client.post(
            reverse("appointment-list"),
            {**base_payload, "scheduled_at": "2026-07-01T14:00:00-03:00"},
            format="json",
        )
        self.assertEqual(first_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(second_response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(third_response.status_code, status.HTTP_201_CREATED)

        day_response = self.client.get(reverse("appointment-list"), {"period": "day", "date": "2026-06-10"})
        self.assertEqual(day_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(day_response.data["results"]), 1)

        week_response = self.client.get(reverse("appointment-list"), {"period": "week", "date": "2026-06-10"})
        self.assertEqual(week_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(week_response.data["results"]), 2)

        month_response = self.client.get(reverse("appointment-list"), {"period": "month", "date": "2026-06-10"})
        self.assertEqual(month_response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(month_response.data["results"]), 2)

        appointment_id = first_response.data["id"]
        invalid_transition = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": appointment_id}),
            {"status": "done"},
            format="json",
        )
        self.assertEqual(invalid_transition.status_code, status.HTTP_400_BAD_REQUEST)

        valid_transition_1 = self.client.post(
            reverse("appointment-confirm", kwargs={"pk": appointment_id}),
            format="json",
        )
        valid_transition_2 = self.client.post(
            reverse("appointment-start", kwargs={"pk": appointment_id}),
            format="json",
        )
        valid_transition_3 = self.client.post(
            reverse("appointment-complete", kwargs={"pk": appointment_id}),
            format="json",
        )
        self.assertEqual(valid_transition_1.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_transition_2.status_code, status.HTTP_200_OK)
        self.assertEqual(valid_transition_3.status_code, status.HTTP_200_OK)

    def test_search_filters_pagination_and_health_form(self):
        register_response = register_studio_admin(
            self.client, "busca@inkcontrol.dev", "Estudio Busca"
        )
        token = register_response.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")

        client_a = self.client.post(
            reverse("client-list"),
            {"name": "Ana Silva", "phone": "5411111111", "email": "ana@dev.com"},
            format="json",
        ).data
        self.client.post(
            reverse("client-list"),
            {"name": "Bruno Lima", "phone": "5422222222", "email": "bruno@dev.com"},
            format="json",
        )

        tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Rafa Traço",
                "artistic_style": "Blackwork",
                "contact": "5433333333",
            },
            format="json",
        ).data

        clients_search = self.client.get(reverse("client-list"), {"q": "Ana"})
        self.assertEqual(clients_search.status_code, status.HTTP_200_OK)
        self.assertEqual(clients_search.data["count"], 1)

        appointment = self.client.post(
            reverse("appointment-list"),
            {
                "client": client_a["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-08-10T14:00:00-03:00",
                "description": "Leao realista",
                "appointment_kind": "consultation",
            },
            format="json",
        )
        self.assertEqual(appointment.status_code, status.HTTP_201_CREATED)
        self.client.post(
            reverse("appointment-confirm", kwargs={"pk": appointment.data["id"]}),
            format="json",
        )

        appointments_search = self.client.get(
            reverse("appointment-list"),
            {"q": "Leao", "status": "confirmed"},
        )
        self.assertEqual(appointments_search.status_code, status.HTTP_200_OK)
        self.assertEqual(appointments_search.data["count"], 1)

        health_form_create = self.client.post(
            reverse("health-form-list"),
            {
                "client": client_a["id"],
                "allergies": "Niquel",
                "chronic_diseases": "Nenhuma",
                "healing_history": "Boa cicatrizacao",
                "notes": "Cliente tranquilo",
            },
            format="json",
        )
        self.assertEqual(health_form_create.status_code, status.HTTP_201_CREATED)

        health_form_list = self.client.get(reverse("health-form-list"), {"q": "Niquel"})
        self.assertEqual(health_form_list.status_code, status.HTTP_200_OK)
        self.assertEqual(health_form_list.data["count"], 1)

    def test_role_based_permissions(self):
        studio_token = register_studio_admin(
            self.client, "studio.perm@inkcontrol.dev", "Estudio Perm"
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        base_client = self.client.post(
            reverse("client-list"),
            {
                "name": "Cliente Base",
                "phone": "54944444444",
                "email": "cliente.base@inkcontrol.dev",
            },
            format="json",
        ).data
        base_tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuador Base",
                "artistic_style": "Fineline",
                "contact": "54944440000",
            },
            format="json",
        ).data
        self.client.credentials()

        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Perm",
                "email": "cliente.perm@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        client_record = Client.objects.get(email="cliente.perm@inkcontrol.dev")
        ClientHealthForm.objects.create(
            client=client_record,
            allergies="Sem alergias declaradas",
        )

        tattooer_token = self.client.post(
            reverse("register"),
            {
                "name": "Tattooer Perm",
                "email": "tattooer.perm@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "tattooer",
            },
            format="json",
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        denied_client_create_client = self.client.post(
            reverse("client-list"),
            {
                "name": "Nao Pode",
                "phone": "000",
                "email": "naopode@inkcontrol.dev",
            },
            format="json",
        )
        self.assertEqual(denied_client_create_client.status_code, status.HTTP_403_FORBIDDEN)

        allowed_client_create_appointment = self.client.post(
            reverse("appointment-list"),
            {
                "client": base_client["id"],
                "tattooer": base_tattooer["id"],
                "scheduled_at": "2026-10-10T10:00:00-03:00",
                "description": "Cliente pode solicitar",
                "status": "requested",
            },
            format="json",
        )
        self.assertEqual(allowed_client_create_appointment.status_code, status.HTTP_201_CREATED)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {tattooer_token}")
        denied_tattooer_delete_client = self.client.delete(
            reverse("client-detail", kwargs={"pk": base_client["id"]})
        )
        self.assertEqual(denied_tattooer_delete_client.status_code, status.HTTP_403_FORBIDDEN)

        allowed_tattooer_list_clients = self.client.get(reverse("client-list"))
        self.assertEqual(allowed_tattooer_list_clients.status_code, status.HTTP_200_OK)

    def test_client_must_request_consultation_before_session(self):
        studio_token = register_studio_admin(
            self.client, "studio.flow@inkcontrol.dev", "Estudio Fluxo"
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "Tatuadora Fluxo",
                "artistic_style": "Blackwork",
                "contact": "54911110000",
            },
            format="json",
        ).data
        self.client.credentials()

        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Fluxo",
                "email": "cliente.fluxo@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        no_health = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-10-11T10:00:00-03:00",
                "appointment_kind": "consultation",
            },
            format="json",
        )
        self.assertEqual(no_health.status_code, status.HTTP_400_BAD_REQUEST)

        client_record = Client.objects.get(email="cliente.fluxo@inkcontrol.dev")
        ClientHealthForm.objects.create(
            client=client_record,
            allergies="Nenhuma",
            healing_history="Boa",
        )
        session_without_consultation = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-10-12T10:00:00-03:00",
                "appointment_kind": "service",
            },
            format="json",
        )
        self.assertEqual(
            session_without_consultation.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        consultation = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-10-11T10:00:00-03:00",
                "appointment_kind": "consultation",
            },
            format="json",
        )
        self.assertEqual(consultation.status_code, status.HTTP_201_CREATED)
        client_record.refresh_from_db()
        self.assertEqual(client_record.studio_id, tattooer["studio"])

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {studio_token}")
        direct_change = self.client.patch(
            reverse("appointment-detail", kwargs={"pk": consultation.data["id"]}),
            {
                "scheduled_at": "2026-10-11T11:00:00-03:00",
                "description": "Alterado pelo estudio",
            },
            format="json",
        )
        self.assertEqual(direct_change.status_code, status.HTTP_400_BAD_REQUEST)

        confirmed = self.client.post(
            reverse("appointment-confirm", kwargs={"pk": consultation.data["id"]}),
            format="json",
        )
        self.assertEqual(confirmed.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        session = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-10-12T10:00:00-03:00",
                "appointment_kind": "service",
            },
            format="json",
        )
        self.assertEqual(session.status_code, status.HTTP_201_CREATED, session.data)
        self.assertEqual(session.data["source_consultation"], consultation.data["id"])


class SecurityAndUsersAPITests(APITestCase):
    def _register_studio(self, email="studio.sec@inkcontrol.dev"):
        r = register_studio_admin(self.client, email, studio_name=f"Estudio {email}")
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        return r.data["token"]

    @override_settings(LOGIN_MAX_FAILED_ATTEMPTS=3, LOGIN_LOCKOUT_MINUTES=15)
    def test_login_lockout_after_failed_attempts(self):
        User.objects.create_user(
            username="lock@inkcontrol.dev",
            email="lock@inkcontrol.dev",
            password="SenhaForte123",
            first_name="Lock",
        )
        for _ in range(3):
            bad = self.client.post(
                reverse("login"),
                {"email": "lock@inkcontrol.dev", "password": "errada"},
                format="json",
            )
            self.assertEqual(bad.status_code, status.HTTP_400_BAD_REQUEST)
        locked = self.client.post(
            reverse("login"),
            {"email": "lock@inkcontrol.dev", "password": "SenhaForte123"},
            format="json",
        )
        self.assertEqual(locked.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("bloqueada", locked.data["detail"].lower())

    @override_settings(TOKEN_INACTIVITY_MINUTES=30)
    def test_token_expires_after_inactivity(self):
        token_key = self._register_studio("inactive@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token_key}")
        self.assertEqual(self.client.get(reverse("me")).status_code, status.HTTP_200_OK)
        token = Token.objects.get(key=token_key)
        TokenActivity.objects.filter(token=token).update(
            last_activity=timezone.now() - timedelta(minutes=31)
        )
        expired = self.client.get(reverse("me"))
        self.assertEqual(expired.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_studio_cannot_list_system_users(self):
        token = self._register_studio("sysusers@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        r = self.client.get(reverse("system-users"), {"role": "client"})
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)

    def test_tattooer_cannot_inactivate_with_appointments(self):
        token = self._register_studio("tat.inact@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        client = self.client.post(
            reverse("client-list"),
            {
                "name": "C",
                "phone": "1",
                "email": "c.inact@inkcontrol.dev",
            },
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {
                "name": "T",
                "artistic_style": "X",
                "contact": "2",
            },
            format="json",
        ).data
        self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-11-01T10:00:00-03:00",
            },
            format="json",
        )
        patch = self.client.patch(
            reverse("tattooer-detail", kwargs={"pk": tattooer["id"]}),
            {"is_active": False},
            format="json",
        )
        self.assertEqual(patch.status_code, status.HTTP_400_BAD_REQUEST)

    def test_health_form_hidden_until_client_served_at_studio(self):
        token = self._register_studio("health.scope@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        client = self.client.post(
            reverse("client-list"),
            {
                "name": "Sem Sessao",
                "phone": "9",
                "email": "sem.sessao@inkcontrol.dev",
            },
            format="json",
        ).data
        self.client.post(
            reverse("health-form-list"),
            {
                "client": client["id"],
                "allergies": "Po",
            },
            format="json",
        )
        listed = self.client.get(reverse("health-form-list"))
        self.assertEqual(listed.data["count"], 0)

    def test_client_can_send_reference_image_only_on_evaluation_request(self):
        token = self._register_studio("ref@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        self.client.credentials()
        client_token = self.client.post(
            reverse("register"),
            {
                "name": "Cliente Ref",
                "email": "ref.cliente@inkcontrol.dev",
                "password": "SenhaForte123",
                "role": "client",
            },
            format="json",
        ).data["token"]
        client_record = Client.objects.get(email="ref.cliente@inkcontrol.dev")
        ClientHealthForm.objects.create(client=client_record, allergies="Nenhuma")
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buf = BytesIO()
        Image.new("RGB", (8, 8), color="red").save(buf, format="PNG")
        upload = SimpleUploadedFile(
            "ref.png",
            buf.getvalue(),
            content_type="image/png",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {client_token}")
        r = self.client.post(
            reverse("appointment-list"),
            {
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-12-02T10:00:00-03:00",
                "appointment_kind": "consultation",
                "reference_image": upload,
            },
            format="multipart",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertTrue(r.data["reference_image"])


class ExtendedBackendAPITests(APITestCase):
    def _studio_token(self, email="ext.studio@inkcontrol.dev"):
        r = register_studio_admin(self.client, email, studio_name=f"Ext {email}")
        return r.data["token"]

    def test_health_response_time_header(self):
        r = self.client.get(reverse("health"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("X-Response-Time-Ms", r)

    def test_every_studio_allows_consultation_requests(self):
        token = self._studio_token("hu12@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "hu12.c@inkcontrol.dev"},
            format="json",
        ).data
        tattooer = self.client.post(
            reverse("tattooer-list"),
            {"name": "T", "artistic_style": "X", "contact": "2"},
            format="json",
        ).data
        ok = self.client.post(
            reverse("appointment-list"),
            {
                "client": client["id"],
                "tattooer": tattooer["id"],
                "scheduled_at": "2026-12-01T10:00:00-03:00",
                "appointment_kind": "consultation",
            },
            format="json",
        )
        self.assertEqual(ok.status_code, status.HTTP_201_CREATED)

    def test_register_studio_tenant(self):
        r = self.client.post(
            reverse("studio-register"),
            {
                "studio_name": "Novo Estudio",
                "admin_name": "Admin",
                "admin_email": "novo.estudio@inkcontrol.dev",
                "password": "SenhaForte123",
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED)
        self.assertEqual(r.data["studio"]["name"], "Novo Estudio")
        self.assertTrue(r.data["settings"]["offers_consultation"])

    def test_change_request_accept_sends_email(self):
        from unittest.mock import patch

        token = self._studio_token("cr.mail@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        client = self.client.post(
            reverse("client-list"),
            {"name": "C", "phone": "1", "email": "cr.client@inkcontrol.dev"},
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
                "scheduled_at": "2026-12-05T10:00:00-03:00",
            },
            format="json",
        ).data
        client_user = User.objects.create_user(
            username="cr.client@inkcontrol.dev",
            email="cr.client@inkcontrol.dev",
            password="SenhaForte123",
            first_name="Cliente",
        )
        from studio.studio_scope import get_user_studio_id

        studio_id = get_user_studio_id(
            User.objects.get(email="cr.mail@inkcontrol.dev")
        )
        UserProfile.objects.create(
            user=client_user, role=UserProfile.ROLE_CLIENT, studio_id=studio_id
        )
        from studio.features.auth.token_activity import issue_token_for_user

        ct = issue_token_for_user(client_user).key
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {ct}")
        cr = self.client.post(
            reverse("appointment-change-request-list"),
            {
                "appointment": appt["id"],
                "proposed_changes": {
                    "scheduled_at": "2026-12-05T14:00:00-03:00",
                },
            },
            format="json",
        ).data
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        with patch(
            "studio.features.appointments.controller.notify_change_request_accepted"
        ) as notify_mock:
            acc = self.client.post(
                reverse(
                    "appointment-change-request-accept",
                    kwargs={"pk": cr["id"]},
                )
            )
            self.assertEqual(acc.status_code, status.HTTP_200_OK)
            notify_mock.assert_called_once()

    def test_subscription_status(self):
        token = self._studio_token("sub@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        r = self.client.get(reverse("studio-subscription"))
        self.assertEqual(r.status_code, status.HTTP_200_OK)
        self.assertIn("paid_until", r.data)
        self.assertIn("studio_id", r.data)

    def test_studio_cannot_delete_account_user(self):
        token = self._studio_token("delacc@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        email = "del.cliente@inkcontrol.dev"
        self.client.post(
            reverse("client-list"),
            {"name": "Del", "phone": "9", "email": email},
            format="json",
        )
        from studio.studio_scope import get_user_studio_id

        studio_id = get_user_studio_id(
            User.objects.get(email="delacc@inkcontrol.dev")
        )
        u = User.objects.create_user(
            username=email,
            email=email,
            password="SenhaForte123",
            first_name="Del",
        )
        UserProfile.objects.create(
            user=u, role=UserProfile.ROLE_CLIENT, studio_id=studio_id
        )
        self.assertTrue(Client.objects.filter(email=email).exists())
        del_r = self.client.delete(reverse("account-detail", kwargs={"pk": u.pk}))
        self.assertEqual(del_r.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(Client.objects.filter(email=email).exists())

    def test_tenant_isolation_clients(self):
        t1 = self._studio_token("tenant1@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {t1}")
        self.client.post(
            reverse("client-list"),
            {"name": "C1", "phone": "1", "email": "c1@tenant.dev"},
            format="json",
        )
        t2 = self._studio_token("tenant2@inkcontrol.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {t2}")
        listed = self.client.get(reverse("client-list"))
        emails = [c["email"] for c in listed.data["results"]]
        self.assertNotIn("c1@tenant.dev", emails)
