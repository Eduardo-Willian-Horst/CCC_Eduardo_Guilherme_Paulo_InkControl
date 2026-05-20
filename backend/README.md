# Backend InkControl (Django)



API REST para gestao de estudio de tatuagem: multi-tenant, agenda, saude (LGPD), assinatura e e-mails transacionais.



## Como o backend funciona



### Fluxo de uma requisicao



```

Cliente HTTP

  -> CORS

  -> SubscriptionGateMiddleware (402 se assinatura expirada; rotas de login/pay liberadas)

  -> ResponseTimeMiddleware (header X-Response-Time-Ms)

  -> DRF: InactivityTokenAuthentication (RNF05)

  -> ViewSet / APIView em studio/features/*/controller.py

  -> Serializer (validacao I/O) -> studio/services/ (regras de negocio)

  -> models.py + studio_scope.py (filtros por tenant)

```



### Camadas



| Camada | Onde | Responsabilidade |

|--------|------|------------------|

| **Rotas** | `studio/urls.py` | Mapeamento `/api/...`; unica fonte de verdade |

| **Controllers** | `studio/features/*/controller.py` | HTTP, permissoes por acao, orquestracao |

| **Serializers** | `studio/serializers.py` | Entrada/saida JSON; delega validacao pesada aos services |

| **Services** | `studio/services/` | Regras de negocio testaveis sem DRF |

| **Escopo tenant** | `studio_scope.py` | Quem ve quais clientes, fichas, estudio |

| **Agenda** | `booking_utils.py` | Expediente, sobreposicao, change-requests, notificacoes in-app |

| **Dominio** | `models.py` | Entidades e maquina de status de `Appointment` |

| **Middleware** | `studio/middleware/` | Assinatura (HU16), tempo de resposta (RNF01) |



### Multi-tenant (`Studio`)



- Cada estudio e um **tenant** (`Studio`).

- `UserProfile.studio` liga usuario de painel ao tenant.

- `Client.studio`, `Tattooer.studio`, `Appointment.studio` isolam dados.

- Registro de **novo** estudio: `POST /api/studios/register/` (cria Studio + Settings + Billing + admin).

- Registro de cliente/tatuador: `POST /api/auth/register/` (vincula ao estudio padrao ou existente).

- Filtros centralizados em `studio_scope.py` e `user_appointment_scope_queryset()` em `booking_utils.py`.



### Papeis (RBAC)



Cada ViewSet define `role_permissions = { "list": {ROLE_STUDIO, ...}, ... }`.

`RoleByActionPermission` nega se o papel do usuario nao estiver no conjunto da acao.



| Papel | Uso tipico |

|-------|------------|

| `studio` | Admin do tenant: CRUD, assinatura, usuarios do sistema |

| `tattooer` | Agenda e clientes do seu escopo; change-requests |

| `client` | Agendar, portfólio e ficha proprios |



### Agendamento (`Appointment`)



Status com transicoes em `Appointment.ALLOWED_STATUS_TRANSITIONS`:



`requested` -> `waiting_budget` -> `confirmed` -> `in_progress` -> `done` (ou `cancelled` em varios pontos).



- **Orcamento**: `POST/PATCH /api/appointments/{id}/budget/` (`budget_service`).

- **Cancelar**: `POST .../cancel/` (nao usa DELETE).

- **Alteracao**: `appointment-change-requests` com accept/reject; notificacao + e-mail apos commit.

- **HU06**: `health_snapshot` gravado no create; ficha viva so visivel com escopo em `studio_scope`.



### Assinatura 



- `StudioBilling.paid_until`: acesso liberado enquanto `paid_until >= agora`.

- `SubscriptionGateMiddleware`: retorna **402** nas rotas `/api/*` se expirou (exceto login, registro, pay).

- Pagamento hoje e **simulado** em `/api/studio/subscription/pay/`; `simulate_failure` dispara e-mail (HU20).



### E-mails e tarefas agendadas



| Mecanismo | Quando usar |

|-----------|-------------|

| `ENABLE_EMAIL_SCHEDULER=true` | APScheduler no processo Django (`scheduler.py` -> `run_scheduled_tasks`) |

| Cron / Agendador Windows | `python manage.py run_scheduled_tasks` em producao |



Comandos: lembretes 30 min antes, purge de imagens de agendamento e portfólio.



### Autenticacao



- Token DRF + `TokenActivity`: inatividade apaga token.

- Login com bloqueio apos falhas em `login_guard.py`.

- Novo login invalida tokens anteriores do usuario (`issue_token_for_user`).



## Estrutura de pastas



```

config/           # settings, urls raiz, WSGI

studio/

  models.py

  serializers.py

  booking_utils.py

  studio_scope.py

  permissions.py

  services/       # regras de negocio

  features/       # controllers por caso de uso

  middleware/

  management/commands/

```



## Testes



```powershell

python manage.py test studio

```



Inclui `tests_ops.py`: gate 402, purge, pagamento, orcamento, RNF01.



## SQLite legado



```powershell

python manage.py reconcile_legacy_database

```



Converte `studio_studio` antigo e aplica migracoes 0008–0010.



## Pendencias DVP



- Gateway de pagamento real (substituir simulacao em `subscription_controller`).

- Front-end (fora deste repositorio backend).



Ver tambem `readme.md` na raiz do repositorio.

