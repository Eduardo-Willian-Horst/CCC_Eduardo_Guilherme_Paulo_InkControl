export const ROLES = {
  studio: 'studio',
  tattooer: 'tattooer',
  client: 'client',
}

export const ROLE_LABELS = {
  studio: 'Estúdio',
  tattooer: 'Tatuador',
  client: 'Cliente',
}

export const APPOINTMENT_STATUS = {
  requested: 'requested',
  waiting_budget: 'waiting_budget',
  confirmed: 'confirmed',
  in_progress: 'in_progress',
  done: 'done',
  cancelled: 'cancelled',
}

export const APPOINTMENT_KIND = {
  service: 'service',
  consultation: 'consultation',
}

export const APPOINTMENT_KIND_LABELS = {
  service: 'Sessão',
  consultation: 'Avaliação',
}

export const APPOINTMENT_STATUS_LABELS = {
  requested: 'Solicitado',
  waiting_budget: 'Orçamento enviado',
  confirmed: 'Sessão confirmada',
  in_progress: 'Em andamento',
  done: 'Concluído',
  cancelled: 'Cancelado',
}

export const STATUS_TRANSITIONS = {
  requested: ['waiting_budget', 'confirmed', 'cancelled'],
  waiting_budget: ['confirmed', 'cancelled'],
  confirmed: ['in_progress', 'cancelled'],
  in_progress: ['done', 'cancelled'],
  done: [],
  cancelled: [],
}

export const TOKEN_STORAGE_KEY = 'inkcontrol_token'
