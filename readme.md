# InkControl

Sistema web para gestão de estúdio de tatuagem (agendamentos, clientes, tatuadores, portfólio, saúde do cliente), conforme o **Documento de Visão do Produto** do projeto acadêmico.

**Stack:** React 18 · Django 5 + Django REST Framework · PostgreSQL 17 (ou SQLite para desenvolvimento rápido).

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

- `POST /api/auth/register/` — cliente/tatuador (vinculado ao estúdio padrão)
- `POST /api/studios/register/` — **novo estúdio** (tenant) + administrador
- `POST /api/auth/login/` · `GET /api/auth/me/` · `POST /api/auth/logout/`
- Recuperação de senha: `POST /api/auth/password-reset/request/` e `confirm/`

### Estúdio (multi-tenant)

- `GET/PATCH /api/studios/{id}/` — dados do estúdio (admin do próprio tenant)
- `GET/PATCH /api/studio-settings/?studio={id}` — expediente e **`offers_consultation`** (HU12)
- `GET/POST /api/studio/subscription/` — mensalidade **por estúdio**

### Cadastros e agenda

- CRUD `/api/clients/`, `/api/tattooers/`, `/api/appointments/`
- `POST /api/appointments/{id}/cancel/`
- `GET/POST /api/appointment-change-requests/` + `accept/` / `reject/`
- `GET/POST /api/portfolio-images/?client=` — referências no perfil do cliente (RF04)
- `GET /api/system-users/` — lista unificada (papel `studio`)
- `GET/PATCH/DELETE /api/accounts/{id}/` — contas de login

### Segurança (RNF05 / RNF06)

- Token expira após inatividade (`TOKEN_INACTIVITY_MINUTES`, padrão 30)
- Bloqueio de login após tentativas inválidas (`LOGIN_MAX_FAILED_ATTEMPTS`, `LOGIN_LOCKOUT_MINUTES`)

### Avaliação

- `offers_consultation` em `studio-settings` (PATCH pelo estúdio)
- Agendamento com `appointment_kind=consultation` só é aceito se a flag estiver ativa

### Ficha de saúde 

- Papel **studio**: vê fichas apenas de clientes **já atendidos** no estúdio
- Papel **tatuador**: vê fichas de clientes com sessão com ele no estúdio
- Papel **client**: vê/edita a própria ficha

### E-mails e tarefas agendadas 

Configure SMTP no `.env` (ver `.env.example`).

**Opção A — agendador no processo Django (dev/servidor único):**

```env
ENABLE_EMAIL_SCHEDULER=true
SCHEDULER_INTERVAL_MINUTES=5
```

**Opção B — cron / Agendador de Tarefas (produção):**

```powershell
python manage.py run_scheduled_tasks
```

Esse comando executa lembretes (~30 min antes), purge de imagens de agendamento e purge de portfólio (7 dias após sessão concluída).

E-mails também são enviados em: criação/cancelamento/status de agendamento, solicitação de alteração, **aceite** e **recusa** de alteração.

### Retenção de imagens 

- `purge_expired_appointment_reference_images` — imagens do agendamento
- `purge_expired_client_portfolio_images` — portfólio do cliente

### Monitoramento 

Respostas incluem o header `X-Response-Time-Ms` (tempo de processamento no servidor).

### Permissões por papel

- **studio**: CRUD completo no tenant; lista unificada de usuários; assinatura
- **tattooer**: agenda e clientes do escopo de atendimento; alterações via change-request
- **client**: agendar, portfólio e ficha próprios

Header autenticado: `Authorization: Token <seu_token>`

## Estrutura

| Pasta | Conteúdo |
|--------|-----------|
| `backend/` | Django (`config/`), app `studio` |
| `frontend/` | React 18 + Vite |
| `requirements.txt` | Dependências Python |

## Backend — revisão e boas práticas

Ver **`backend/README.md`**: arquitetura, fluxo HTTP, multi-tenant, RBAC, agenda, assinatura e comandos agendados.

### Orçamento (`waiting_budget`)

- `GET/POST/PATCH /api/appointments/{id}/budget/` — envio de valor e notas (estúdio/tatuador)

### Pagamento simulado (HU20)

- `POST /api/studio/subscription/pay/` com `simulate_failure: true` registra falha e envia e-mail

## SQLite de desenvolvimento (schema antigo)

Se `migrate` falhar por `studio_studio` legado (`default_open_time`, etc.):

```powershell
cd backend
python manage.py reconcile_legacy_database
```

## Pendências conhecidas (backend)

- Pagamento real com gateway - simulação + e-mails já implementados
- Cloudflare R2 — configurar `AWS_*` no `.env` (ver comentários em `config/settings.py`)
