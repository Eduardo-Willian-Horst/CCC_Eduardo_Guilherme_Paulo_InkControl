# Backend InkControl (Django)



API REST para gestao de estudio de tatuagem: multi-tenant, agenda, saude (LGPD), assinatura, notificacoes in-app e e-mails transacionais.



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

| **Agenda** | `booking_utils.py` e `services/appointment_service.py` | Expediente, sobreposicao, avaliacao previa, change-requests e escopo de agenda |

| **Dominio** | `models.py` | Entidades e maquina de status de `Appointment` |

| **Middleware** | `studio/middleware/` | Assinatura (HU16), tempo de resposta (RNF01) |



### Multi-tenant (`Studio`)



- Cada estudio e um **tenant** (`Studio`).

- `UserProfile.studio` liga usuario de painel ao tenant.

- `Client.studio`, `Tattooer.studio`, `Appointment.studio` isolam dados.

- Registro de **novo** estudio: `POST /api/studios/register/` (cria Studio + Settings + Billing + admin).

- Registro publico de cliente: `POST /api/auth/register/` (vincula ao estudio padrao ou existente).

- Filtros centralizados em `studio_scope.py` e `user_appointment_scope_queryset()` em `booking_utils.py`.



### Papeis (RBAC)



Cada ViewSet define `role_permissions = { "list": {ROLE_STUDIO, ...}, ... }`.

`RoleByActionPermission` nega se o papel do usuario nao estiver no conjunto da acao.



| Papel | Uso tipico |

|-------|------------|

| `studio` | Admin do tenant: CRUD operacional e assinatura |

| `tattooer` | Agenda e clientes do seu escopo; change-requests |

| `client` | Solicitar avaliação/sessão e manter a própria ficha de saúde |



### Agendamento (`Appointment`)



Status com transicoes em `Appointment.ALLOWED_STATUS_TRANSITIONS`:



`requested` -> `waiting_budget` -> `confirmed` -> `in_progress` -> `done` (ou `cancelled` em varios pontos).

- **Avaliacao primeiro**: cliente solicita `consultation`; so depois de uma avaliacao `confirmed` ou `done` pode solicitar `service` com o mesmo profissional.

- **Imagem de referencia**: `reference_image` pode ser enviada na solicitacao do agendamento via multipart.

- **Status sem edicao manual**: mudancas usam acoes dedicadas (`confirm`, `start`, `complete`, `cancel`, `budget/accept`, `budget/reject`).

- **Pedidos do cliente**: estudio nao altera diretamente uma solicitacao pendente; usa acoes do fluxo ou `appointment-change-requests`.



- **Orcamento**: `POST/PATCH /api/appointments/{id}/budget/` (`budget_service`).

- **Resposta do cliente ao orcamento**: `POST .../budget/accept/` confirma a sessao; `POST .../budget/reject/` cancela a solicitacao.

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

| `manage.py runserver` | Sobe a API e o scheduler interno no mesmo processo Django |

| `ENABLE_EMAIL_SCHEDULER=false` | Desliga o scheduler interno quando precisar rodar sem tarefas recorrentes |



Com `runserver`, o scheduler interno executa lembretes 30 min antes e purge de imagens de referência do agendamento. O comando `run_scheduled_tasks` continua existindo apenas para manutenção manual.


### Notificacoes


`InAppNotification` guarda avisos por usuario autenticado. Eventos de agendamento notificam os participantes do outro lado: criacao, edicao permitida, cancelamento, mudanca de status, envio de orcamento, aceite/recusa de orcamento e aceite/recusa de contraproposta.



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

..\.venv\Scripts\python.exe manage.py test studio

```



Inclui `tests_ops.py`: gate 402, purge, pagamento, orcamento, notificacoes, upload de imagem e RNF01.



## SQLite legado



```powershell

..\.venv\Scripts\python.exe manage.py reconcile_legacy_database

```



Converte `studio_studio` antigo e aplica migracoes 0008–0010.



## Pendencias DVP



- Gateway de pagamento real (substituir simulacao em `subscription_controller`).




Ver tambem `readme.md` na raiz do repositorio.

