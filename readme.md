# InkControl

Sistema web para gestão de estúdio de tatuagem (avaliações, agendamentos, clientes, tatuadores e saúde do cliente), conforme o **Documento de Visão do Produto** do projeto acadêmico.

**Stack:** React · Django 5 + Django REST Framework · PostgreSQL 17 (ou SQLite para desenvolvimento rápido).

## Pré-requisitos

- Python 3.11+
- Node.js 20+ (recomendado 24+)
- Docker Desktop (opcional, para PostgreSQL)

## Configuração rápida

### 1. Ambiente Python

Na raiz do repositório:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Variáveis de ambiente

```powershell
copy .env.example .env
```

Ajuste `.env` se necessário. Sem `POSTGRES_*`, o back-end usa **SQLite** em `backend/db.sqlite3`.

### 3. PostgreSQL com Docker (opcional)

```powershell
docker compose up -d
```

Depois defina no `.env` os valores de `POSTGRES_*` como em `.env.example` (`POSTGRES_HOST=localhost`).

### 4. Migrações e servidor Django

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py migrate
..\.venv\Scripts\python.exe manage.py runserver
```

### 5. Front-end (Vite)

Em outro terminal:

```powershell
cd frontend
npm install
npm run dev
```

Abra [http://localhost:5173](http://localhost:5173). O Vite encaminha `/api` para `http://127.0.0.1:8000`.

## API principal

### Autenticação

- `POST /api/auth/register/` — cliente no fluxo público
- `POST /api/studios/register/` — **novo estúdio** (tenant) + administrador
- `POST /api/auth/login/` · `GET /api/auth/me/` · `POST /api/auth/logout/`
- Recuperação de senha: `POST /api/auth/password-reset/request/` e `confirm/`

### Estúdio (multi-tenant)

- `GET/PATCH /api/studios/{id}/` — dados do estúdio (admin do próprio tenant)
- `GET/PATCH /api/studio-settings/?studio={id}` — expediente do estúdio
- `GET/POST /api/studio/subscription/` — mensalidade **por estúdio**

### Cadastros e agenda

- CRUD `/api/clients/`, `/api/tattooers/`, `/api/appointments/`
- `POST /api/appointments/{id}/cancel/`
- `POST /api/appointments/{id}/confirm/`, `start/`, `complete/` — ações do fluxo, sem mudança manual de status
- `GET/POST/PATCH /api/appointments/{id}/budget/` — orçamento da sessão
- `POST /api/appointments/{id}/budget/accept/` e `budget/reject/` — resposta do cliente
- `GET/POST /api/appointment-change-requests/` + `accept/` / `reject/`

### Segurança

- Token expira após inatividade (`TOKEN_INACTIVITY_MINUTES`, padrão 30)
- Bloqueio de login após tentativas inválidas (`LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`)

### Fluxo de avaliação e sessão

- Todo estúdio oferece avaliação; não há opção para desativar.
- O cliente primeiro solicita uma **avaliação** e pode anexar uma imagem de referência na solicitação.
- Depois de uma avaliação aprovada, o cliente pode solicitar uma **sessão** com o mesmo profissional.
- O estúdio/tatuador envia o orçamento da sessão; o cliente aceita ou recusa.
- Se o cliente aceitar o orçamento, a sessão é confirmada automaticamente.

### Ficha de saúde 

- Papel **studio**: vê fichas apenas de clientes **já atendidos** no estúdio
- Papel **tatuador**: vê fichas de clientes com sessão com ele no estúdio
- Papel **client**: vê/edita a própria ficha

### Notificações, e-mails e tarefas agendadas 

Configure SMTP no `.env` (ver `.env.example`).

No MVP acadêmico, as tarefas recorrentes rodam dentro do próprio processo iniciado por `runserver`. Em desenvolvimento, o agendador interno já fica ligado por padrão.

```env
# Opcional: ajuste o intervalo ou desligue se precisar.
# ENABLE_EMAIL_SCHEDULER=false
# SCHEDULER_INTERVAL_MINUTES=5
```

O `runserver` executa lembretes (~30 min antes) e purge de imagens de referência anexadas ao agendamento.

Notificações in-app são geradas quando qualquer lado age em um agendamento: criação, edição permitida, cancelamento, mudança de status, orçamento, aceite/recusa de orçamento e contrapropostas.

E-mails também são enviados em: criação/cancelamento/status de agendamento, solicitação de alteração, **aceite** e **recusa** de alteração.

### Retenção de imagens 

- `purge_expired_appointment_reference_images` — imagens do agendamento

### Monitoramento 

Respostas incluem o header `X-Response-Time-Ms` (tempo de processamento no servidor).

### Permissões por papel

- **studio**: CRUD operacional no tenant, pedidos, orçamento, agenda e assinatura
- **tattooer**: agenda e clientes do escopo de atendimento; alterações via change-request
- **client**: solicitar avaliação/sessão e manter a própria ficha de saúde

Header autenticado: `Authorization: Token <seu_token>`

## Estrutura

| Pasta | Conteúdo |
|--------|-----------|
| `backend/` | Django (`config/`), app `studio` |
| `frontend/` | React + Vite |
| `requirements.txt` | Dependências Python |

## Backend — revisão e boas práticas

Ver **`backend/README.md`**: arquitetura, fluxo HTTP, multi-tenant, RBAC, agenda, assinatura e comandos agendados.

### Orçamento (`waiting_budget`)

- `GET/POST/PATCH /api/appointments/{id}/budget/` — envio de valor e notas (estúdio/tatuador)
- `POST /api/appointments/{id}/budget/accept/` — cliente aceita e confirma a sessão
- `POST /api/appointments/{id}/budget/reject/` — cliente recusa e cancela a solicitação

### Pagamento simulado

- `POST /api/studio/subscription/pay/` com `simulate_failure: true` registra falha e envia e-mail

## SQLite de desenvolvimento (schema antigo)

Se `migrate` falhar por `studio_studio` legado (`default_open_time`, etc.):

```powershell
cd backend
..\.venv\Scripts\python.exe manage.py reconcile_legacy_database
```

## Pendências conhecidas (backend)

- Pagamento real com gateway - simulação + e-mails já implementados
- Cloudflare R2 — configurar `AWS_*` no `.env` (ver comentários em `config/settings.py`)
