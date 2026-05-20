"""
Regras de negocio desacopladas dos serializers DRF.

- appointment_service: validacao de agenda, status, HU12, conflito de horario.
- change_request_service: campos permitidos em solicitacao de alteracao.
- budget_service: orcamento e transicao para waiting_budget.
- registration_service: cadastro cliente/tatuador (nao cria estudio).
- billing_notifications: e-mail de tentativa de pagamento (HU20).
- image_validation: tamanho/tipo de upload de imagens.
"""
