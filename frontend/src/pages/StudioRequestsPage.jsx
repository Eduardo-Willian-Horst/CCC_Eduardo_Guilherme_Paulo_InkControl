import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Spinner } from '../components/ui/Spinner'
import { TableWrap, TableWithHead } from '../components/ui/Table'
import {
  APPOINTMENT_KIND_LABELS,
  APPOINTMENT_STATUS_LABELS,
} from '../lib/constants'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { formatBudgetAmount, formatDateTime, fromDatetimeLocalValue } from '../lib/format'
import './pages.css'

function clientLabel(row) {
  if (row?.client && typeof row.client === 'object') return row.client.name || 'Cliente'
  return 'Cliente'
}

function tattooerLabel(row) {
  if (row?.tattooer && typeof row.tattooer === 'object') return row.tattooer.name || 'Profissional'
  return 'Profissional'
}

function requestTitle(row) {
  const kind = APPOINTMENT_KIND_LABELS[row.appointment_kind] ?? row.appointment_kind
  return `${kind} para ${clientLabel(row)}`
}

function isAwaitingBudgetResponse(row) {
  return row.status === 'waiting_budget'
}

function isConsultationRequest(row) {
  return row.appointment_kind === 'consultation' && row.status === 'requested'
}

export function StudioRequestsPage() {
  const [appointments, setAppointments] = useState([])
  const [changeRequests, setChangeRequests] = useState([])
  const [proposedTimes, setProposedTimes] = useState({})
  const [loading, setLoading] = useState(true)
  const [busyKey, setBusyKey] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [reloadKey, setReloadKey] = useState(0)

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      try {
        const requestedAppointments = await fetchAllPaginated('/api/appointments/?status=requested')
        const waitingBudgetAppointments = await fetchAllPaginated(
          '/api/appointments/?status=waiting_budget',
        )
        const pendingAppointments = [...requestedAppointments, ...waitingBudgetAppointments]
        const pendingChanges = await fetchAllPaginated('/api/appointment-change-requests/')
        const pendingChangeRows = pendingChanges.filter((row) => row.status === 'pending')
        const enrichedChanges = []
        for (const row of pendingChangeRows) {
          try {
            const appointment = await apiFetch(`/api/appointments/${row.appointment}/`)
            enrichedChanges.push({ ...row, appointment_detail: appointment })
          } catch {
            enrichedChanges.push(row)
          }
        }
        if (!cancelled) {
          setAppointments(pendingAppointments)
          setChangeRequests(enrichedChanges)
        }
      } catch (e) {
        if (!cancelled) setError(e.message ?? String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [reloadKey])

  function refresh(message) {
    setSuccess(message)
    setReloadKey((key) => key + 1)
  }

  async function handleConfirmAppointment(row) {
    setBusyKey(`confirm-appointment-${row.id}`)
    setError('')
    setSuccess('')
    try {
      await apiFetch(`/api/appointments/${row.id}/confirm/`, { method: 'POST' })
      refresh('Avaliação confirmada.')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBusyKey('')
    }
  }

  async function handleRejectAppointment(row) {
    if (!window.confirm('Recusar este pedido? O agendamento será cancelado.')) return
    setBusyKey(`reject-appointment-${row.id}`)
    setError('')
    setSuccess('')
    try {
      await apiFetch(`/api/appointments/${row.id}/cancel/`, { method: 'POST' })
      refresh('Pedido recusado.')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBusyKey('')
    }
  }

  async function handleProposeAppointmentTime(row) {
    const proposedLocal = proposedTimes[row.id]
    if (!proposedLocal) {
      setError('Informe um novo horário antes de solicitar alteração.')
      return
    }
    setBusyKey(`propose-appointment-${row.id}`)
    setError('')
    setSuccess('')
    try {
      await apiFetch('/api/appointment-change-requests/', {
        method: 'POST',
        body: JSON.stringify({
          appointment: row.id,
          proposed_changes: { scheduled_at: fromDatetimeLocalValue(proposedLocal) },
        }),
      })
      setProposedTimes((current) => ({ ...current, [row.id]: '' }))
      refresh('Solicitação de mudança enviada.')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBusyKey('')
    }
  }

  async function handleAcceptChange(row) {
    setBusyKey(`accept-change-${row.id}`)
    setError('')
    setSuccess('')
    try {
      await apiFetch(`/api/appointment-change-requests/${row.id}/accept/`, { method: 'POST' })
      refresh('Alteração aceita.')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBusyKey('')
    }
  }

  async function handleRejectChange(row) {
    setBusyKey(`reject-change-${row.id}`)
    setError('')
    setSuccess('')
    try {
      await apiFetch(`/api/appointment-change-requests/${row.id}/reject/`, { method: 'POST' })
      refresh('Alteração recusada.')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBusyKey('')
    }
  }

  function renderAppointmentTable(rows) {
    return (
      <TableWrap>
        <TableWithHead
          head={
            <>
              <th>Pedido</th>
              <th>Horário</th>
              <th>Status</th>
              <th>Ações</th>
            </>
          }
        >
          {rows.map((row) => (
            <tr key={row.id}>
              <td>
                <div>{requestTitle(row)}</div>
                <div className="ic-muted">
                  {tattooerLabel(row)}
                  {row.description ? ` — ${row.description}` : ''}
                </div>
                {isAwaitingBudgetResponse(row) && row.budget_amount ? (
                  <div className="ic-muted">
                    Orçamento enviado: {formatBudgetAmount(row.budget_amount)}
                  </div>
                ) : null}
              </td>
              <td>{formatDateTime(row.scheduled_at)}</td>
              <td>
                <Badge variant="outline">
                  {APPOINTMENT_STATUS_LABELS[row.status] ?? row.status}
                </Badge>
              </td>
              <td>
                <div className="ic-row-actions">
                  <Link to={`/agendamentos/${row.id}/editar`}>Abrir detalhes</Link>
                  {isAwaitingBudgetResponse(row) ? (
                    <span className="ic-muted">Aguardando o cliente aceitar ou recusar.</span>
                  ) : (
                    <>
                      <div className="ic-inline-actions">
                        {isConsultationRequest(row) ? (
                          <Button
                            type="button"
                            size="sm"
                            disabled={Boolean(busyKey)}
                            onClick={() => handleConfirmAppointment(row)}
                          >
                            Confirmar avaliação
                          </Button>
                        ) : (
                          <Link to={`/agendamentos/${row.id}/editar`}>Enviar orçamento</Link>
                        )}
                        <Button
                          type="button"
                          variant="danger"
                          size="sm"
                          disabled={Boolean(busyKey)}
                          onClick={() => handleRejectAppointment(row)}
                        >
                          Recusar
                        </Button>
                      </div>
                      <Field label="Sugerir outro horário" id={`propose-${row.id}`}>
                        <Input
                          id={`propose-${row.id}`}
                          type="datetime-local"
                          value={proposedTimes[row.id] ?? ''}
                          onChange={(e) =>
                            setProposedTimes((current) => ({
                              ...current,
                              [row.id]: e.target.value,
                            }))
                          }
                        />
                      </Field>
                      <Button
                        type="button"
                        variant="secondary"
                        size="sm"
                        disabled={Boolean(busyKey)}
                        onClick={() => handleProposeAppointmentTime(row)}
                      >
                        Solicitar mudança
                      </Button>
                    </>
                  )}
                </div>
              </td>
            </tr>
          ))}
        </TableWithHead>
      </TableWrap>
    )
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando pedidos" />
      </div>
    )
  }

  const newRequests = appointments.filter((row) => !isAwaitingBudgetResponse(row))
  const sentBudgets = appointments.filter(isAwaitingBudgetResponse)

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Pedidos</h1>
          <p className="ic-page__lede">
            Central do estúdio para confirmar avaliações, enviar orçamentos, recusar pedidos
            ou negociar horários.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={() => setReloadKey((key) => key + 1)}>
          Atualizar
        </Button>
      </div>

      {error ? (
        <div className="ic-mb-2">
          <Alert variant="error">{error}</Alert>
        </div>
      ) : null}
      {success ? (
        <div className="ic-mb-2">
          <Alert>{success}</Alert>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <h2>Pedidos em acompanhamento</h2>
        </CardHeader>
        <CardBody>
          {appointments.length === 0 ? (
            <p className="ic-muted">Nenhum pedido em acompanhamento.</p>
          ) : (
            <>
              <h3>Solicitações novas</h3>
              {newRequests.length === 0 ? (
                <p className="ic-muted">Nenhuma solicitação nova.</p>
              ) : (
                renderAppointmentTable(newRequests)
              )}
              <h3 className="ic-mt-4">Orçamentos enviados aguardando cliente</h3>
              {sentBudgets.length === 0 ? (
                <p className="ic-muted">Nenhum orçamento aguardando resposta do cliente.</p>
              ) : (
                renderAppointmentTable(sentBudgets)
              )}
            </>
          )}
        </CardBody>
      </Card>

      <Card className="ic-mt-4">
        <CardHeader>
          <h2>Alterações pendentes</h2>
        </CardHeader>
        <CardBody>
          {changeRequests.length === 0 ? (
            <p className="ic-muted">Nenhuma alteração pendente.</p>
          ) : (
            <TableWrap>
              <TableWithHead
                head={
                  <>
                    <th>Solicitação</th>
                    <th>Proposta</th>
                    <th>Ações</th>
                  </>
                }
              >
                {changeRequests.map((row) => {
                  const appointment = row.appointment_detail
                  return (
                    <tr key={row.id}>
                      <td>
                        <div>
                          {appointment ? requestTitle(appointment) : 'Alteração de agendamento'}
                        </div>
                        <div className="ic-muted">
                          Solicitado por {row.requested_by_display || 'usuário do sistema'}
                        </div>
                      </td>
                      <td>
                        <div>{row.proposed_summary || 'Alteração'}</div>
                        {row.proposed_scheduled_at ? (
                          <div className="ic-muted">
                            Novo horário: {formatDateTime(row.proposed_scheduled_at)}
                          </div>
                        ) : null}
                      </td>
                      <td>
                        <div className="ic-row-actions">
                          {appointment ? (
                            <Link to={`/agendamentos/${appointment.id}/editar`}>
                              Abrir detalhes
                            </Link>
                          ) : null}
                          <div className="ic-inline-actions">
                            <Button
                              type="button"
                              size="sm"
                              disabled={Boolean(busyKey) || !row.can_respond}
                              onClick={() => handleAcceptChange(row)}
                            >
                              Aceitar alteração
                            </Button>
                            <Button
                              type="button"
                              variant="secondary"
                              size="sm"
                              disabled={Boolean(busyKey) || !row.can_respond}
                              onClick={() => handleRejectChange(row)}
                            >
                              Recusar
                            </Button>
                          </div>
                          {!row.can_respond ? (
                            <span className="ic-muted">Aguardando resposta da outra parte.</span>
                          ) : null}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </TableWithHead>
            </TableWrap>
          )}
        </CardBody>
      </Card>
    </>
  )
}
