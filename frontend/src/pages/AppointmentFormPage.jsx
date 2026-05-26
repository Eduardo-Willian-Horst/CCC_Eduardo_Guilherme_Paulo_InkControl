import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import {
  APPOINTMENT_KIND_LABELS,
  APPOINTMENT_STATUS_LABELS,
  ROLES,
} from '../lib/constants'
import {
  formatBudgetAmount,
  formatDateTime,
  fromDatetimeLocalValue,
  toDatetimeLocalValue,
} from '../lib/format'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { tattooerPortraitSrc } from '../lib/tattooerPortrait'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Select } from '../components/ui/Select'
import { Textarea } from '../components/ui/Textarea'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'
import './tattooers-vitrine.css'

function clientPkFromAppointment(a) {
  if (a?.client && typeof a.client === 'object') return String(a.client.id)
  return a?.client != null ? String(a.client) : ''
}

function tattooerPkFromAppointment(a) {
  if (a?.tattooer && typeof a.tattooer === 'object') return String(a.tattooer.id)
  return a?.tattooer != null ? String(a.tattooer) : ''
}

function tattooerBriefFromAppointment(a) {
  if (a?.tattooer && typeof a.tattooer === 'object') return a.tattooer
  return null
}

const VALID_CONSULTATION_STATUSES = new Set(['confirmed', 'done'])

export function AppointmentFormPage() {
  const { id: appointmentId, tattooerId: tattooerIdFromUrl } = useParams()
  const isNew = !appointmentId
  const navigate = useNavigate()

  const [me, setMe] = useState(null)
  const [presetTattooer, setPresetTattooer] = useState(null)
  const [tattooers, setTattooers] = useState([])
  const [updatedAt, setUpdatedAt] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [cancelling, setCancelling] = useState(false)
  const [actionBusy, setActionBusy] = useState('')
  const [error, setError] = useState('')
  const [flowMessage, setFlowMessage] = useState('')

  const [clients, setClients] = useState([])

  const [clientId, setClientId] = useState('')
  const [tattooerId, setTattooerId] = useState('')
  const [scheduledLocal, setScheduledLocal] = useState('')
  const [description, setDescription] = useState('')
  const [status, setStatus] = useState('requested')
  const [appointmentKind, setAppointmentKind] = useState('service')
  const [referenceImageFile, setReferenceImageFile] = useState(null)
  const [referenceImageUrl, setReferenceImageUrl] = useState('')
  const [healthSummary, setHealthSummary] = useState(null)
  const [budgetAmount, setBudgetAmount] = useState('')
  const [budgetNotes, setBudgetNotes] = useState('')
  const [budgetSentAt, setBudgetSentAt] = useState('')
  const [budgetSaving, setBudgetSaving] = useState(false)
  const [budgetResponding, setBudgetResponding] = useState('')
  const [budgetMessage, setBudgetMessage] = useState('')
  const [sourceConsultationSummary, setSourceConsultationSummary] = useState(null)

  const [changeRequests, setChangeRequests] = useState([])
  const [crKey, setCrKey] = useState(0)
  const [proposedLocal, setProposedLocal] = useState('')
  const [crBusyId, setCrBusyId] = useState(null)
  const [baseline, setBaseline] = useState(null)

  const fromTattooerPage = Boolean(tattooerIdFromUrl)

  useEffect(() => {
    let cancelled = false
    async function boot() {
      setLoading(true)
      setError('')
      try {
        const user = await apiFetch('/api/auth/me/')
        if (cancelled) return
        setMe(user)

        if (fromTattooerPage && tattooerIdFromUrl) {
          const t = await apiFetch(`/api/tattooers/${tattooerIdFromUrl}/`)
          if (cancelled) return
          setPresetTattooer(t)
          setTattooerId(String(t.id))
          if (user.role === ROLES.client && isNew) {
            const consultations = await fetchAllPaginated(
              `/api/appointments/?tattooer=${t.id}&appointment_kind=consultation`,
            )
            if (cancelled) return
            const valid = consultations.some((a) => VALID_CONSULTATION_STATUSES.has(a.status))
            setAppointmentKind(valid ? 'service' : 'consultation')
          }
        } else if (!isNew) {
          setPresetTattooer(null)
        } else {
          setPresetTattooer(null)
        }

        if (user.role === ROLES.studio) {
          try {
            const c = await fetchAllPaginated('/api/clients/?page=1')
            if (!cancelled) setClients(c.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setClients([])
          }
          try {
            const tlist = await fetchAllPaginated('/api/tattooers/?page=1')
            if (!cancelled) setTattooers(tlist.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setTattooers([])
          }
        } else if (user.role === ROLES.tattooer) {
          try {
            const c = await fetchAllPaginated('/api/clients/?page=1')
            if (!cancelled) setClients(c.filter((x) => x.is_active))
          } catch {
            if (!cancelled) setClients([])
          }
          setTattooers([])
        } else {
          setClients([])
          setTattooers([])
        }

        if (!isNew && appointmentId) {
          const a = await apiFetch(`/api/appointments/${appointmentId}/`)
          if (cancelled) return
          setClientId(clientPkFromAppointment(a))
          setTattooerId(tattooerPkFromAppointment(a))
          setScheduledLocal(toDatetimeLocalValue(a.scheduled_at))
          setDescription(a.description ?? '')
          setStatus(a.status ?? 'requested')
          setAppointmentKind(a.appointment_kind ?? 'service')
          setUpdatedAt(a.updated_at ?? '')
          setReferenceImageUrl(a.reference_image ?? '')
          setHealthSummary(a.health_summary ?? null)
          setBudgetAmount(a.budget_amount != null ? String(a.budget_amount) : '')
          setBudgetNotes(a.budget_notes ?? '')
          setBudgetSentAt(a.budget_sent_at ?? '')
          setSourceConsultationSummary(a.source_consultation_summary ?? null)
          setBaseline({
            scheduled_at: a.scheduled_at,
            description: a.description ?? '',
            appointment_kind: a.appointment_kind ?? 'service',
            tattooer: Number(tattooerPkFromAppointment(a)),
            client: Number(clientPkFromAppointment(a)),
            status: a.status ?? 'requested',
            duration_minutes: a.duration_minutes ?? 60,
          })
          const brief = tattooerBriefFromAppointment(a)
          if (brief) {
            setPresetTattooer(brief)
          } else if (tattooerPkFromAppointment(a)) {
            const t = await apiFetch(`/api/tattooers/${tattooerPkFromAppointment(a)}/`)
            if (!cancelled) setPresetTattooer(t)
          }
        }
      } catch (e) {
        if (!cancelled) setError(e.message ?? String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    boot()
    return () => {
      cancelled = true
    }
  }, [appointmentId, fromTattooerPage, isNew, tattooerIdFromUrl])

  useEffect(() => {
    if (isNew || !appointmentId) return undefined
    let cancelled = false
    async function run() {
      try {
        const res = await apiFetch(`/api/appointment-change-requests/?appointment=${appointmentId}`)
        if (!cancelled) setChangeRequests(res.results ?? [])
      } catch {
        if (!cancelled) setChangeRequests([])
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [appointmentId, isNew, crKey])

  const isTattooer = me?.role === ROLES.tattooer
  const isStudio = me?.role === ROLES.studio
  const isClient = me?.role === ROLES.client
  const canDelete = isStudio && !isNew
  const canRespondBudget = isClient && status === 'waiting_budget' && Boolean(budgetAmount)

  const showTattooerSelect = !(fromTattooerPage && isNew) && !isClient
  const showClientPicker = (isStudio || (isTattooer && !isNew)) && !isClient

  const isPendingStudioRequest = isStudio && !isNew && baseline?.status === 'requested'
  const canConfirmConsultation =
    (isStudio || isTattooer) && !isNew && status === 'requested' && appointmentKind === 'consultation'
  const canStartAppointment = (isStudio || isTattooer) && !isNew && status === 'confirmed'
  const canCompleteAppointment = (isStudio || isTattooer) && !isNew && status === 'in_progress'
  const canAttachReferenceImage = isTattooer
    ? !isNew
    : !isClient || isNew || appointmentKind === 'consultation'
  const referenceImageLabel = isClient
    ? 'Imagem de referência da solicitação (opcional)'
    : 'Imagem de referência (opcional)'
  const referenceImageHint = isClient
    ? 'Envie uma referência visual para o profissional entender sua ideia.'
    : ''

  function goBack() {
    if (fromTattooerPage && tattooerIdFromUrl) {
      navigate(`/tatuadores/${tattooerIdFromUrl}`)
      return
    }
    navigate('/agendamentos')
  }

  async function reloadAppointmentDetail() {
    if (!appointmentId) return
    const a = await apiFetch(`/api/appointments/${appointmentId}/`)
    setClientId(clientPkFromAppointment(a))
    setTattooerId(tattooerPkFromAppointment(a))
    setScheduledLocal(toDatetimeLocalValue(a.scheduled_at))
    setDescription(a.description ?? '')
    setStatus(a.status ?? 'requested')
    setUpdatedAt(a.updated_at ?? '')
    setReferenceImageUrl(a.reference_image ?? '')
    setHealthSummary(a.health_summary ?? null)
    setAppointmentKind(a.appointment_kind ?? 'service')
    setBudgetAmount(a.budget_amount != null ? String(a.budget_amount) : '')
    setBudgetNotes(a.budget_notes ?? '')
    setBudgetSentAt(a.budget_sent_at ?? '')
    setSourceConsultationSummary(a.source_consultation_summary ?? null)
    const brief = tattooerBriefFromAppointment(a)
    if (brief) setPresetTattooer(brief)
    setBaseline({
      scheduled_at: a.scheduled_at,
      description: a.description ?? '',
      appointment_kind: a.appointment_kind ?? 'service',
      tattooer: Number(tattooerPkFromAppointment(a)),
      client: Number(clientPkFromAppointment(a)),
      status: a.status ?? 'requested',
      duration_minutes: a.duration_minutes ?? 60,
    })
  }

  async function ensureClientHealthForm() {
    const data = await apiFetch('/api/health-forms/?page=1')
    const rows = data.results ?? []
    if (rows.length === 0) {
      throw new Error('Preencha sua ficha de saúde antes de solicitar um agendamento.')
    }
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    try {
      if (isNew && isClient) {
        await ensureClientHealthForm()
      }
      if (!isNew && !isStudio && me) {
        if (!baseline) {
          setError('Aguarde o carregamento dos dados antes de salvar.')
          setSaving(false)
          return
        }
        const scheduledIso = fromDatetimeLocalValue(scheduledLocal)
        const proposedChanges = {}
        if (scheduledIso !== baseline.scheduled_at) {
          proposedChanges.scheduled_at = scheduledIso
        }
        if (description !== baseline.description) {
          proposedChanges.description = description
        }
        if (appointmentKind !== baseline.appointment_kind) {
          proposedChanges.appointment_kind = appointmentKind
        }
        if (Number(tattooerId) !== baseline.tattooer) {
          proposedChanges.tattooer = Number(tattooerId)
        }
        const hasImage = Boolean(referenceImageFile)
        const hasAgenda = Object.keys(proposedChanges).length > 0 || hasImage
        if (!hasAgenda) {
          setError('Nenhuma alteração para salvar.')
          setSaving(false)
          return
        }
        if (hasAgenda) {
          const fd = new FormData()
          fd.append('appointment', String(appointmentId))
          fd.append('proposed_changes', JSON.stringify(proposedChanges))
          if (hasImage) {
            fd.append('proposed_reference_image', referenceImageFile)
          }
          await apiFetch('/api/appointment-change-requests/', { method: 'POST', body: fd })
        }
        navigate('/agendamentos')
        return
      }

      if (isStudio && !isNew) {
        if (isPendingStudioRequest) {
          setError('Para mudar esta solicitação, use contraproposta, orçamento ou uma ação do fluxo.')
          setSaving(false)
          return
        }
        const scheduled_at = fromDatetimeLocalValue(scheduledLocal)
        const useMultipart = Boolean(referenceImageFile)
        if (useMultipart) {
          const fd = new FormData()
          fd.append('tattooer', String(Number(tattooerId)))
          fd.append('scheduled_at', scheduled_at)
          fd.append('description', description)
          fd.append('appointment_kind', appointmentKind)
          fd.append('client', String(Number(clientId)))
          fd.append('reference_image', referenceImageFile)
          await apiFetch(`/api/appointments/${appointmentId}/`, {
            method: 'PUT',
            body: fd,
          })
        } else {
          await apiFetch(`/api/appointments/${appointmentId}/`, {
            method: 'PUT',
            body: JSON.stringify({
              tattooer: Number(tattooerId),
              scheduled_at,
              description,
              appointment_kind: appointmentKind,
              client: Number(clientId),
            }),
          })
        }
        navigate('/agendamentos')
        return
      }

      const scheduled_at = fromDatetimeLocalValue(scheduledLocal)
      const useMultipart = Boolean(referenceImageFile)
      if (useMultipart) {
        const fd = new FormData()
        fd.append('tattooer', String(Number(tattooerId)))
        fd.append('scheduled_at', scheduled_at)
        fd.append('description', description)
        fd.append('appointment_kind', appointmentKind)
        if (!(isClient && isNew)) {
          fd.append('client', String(Number(clientId)))
        }
        fd.append('reference_image', referenceImageFile)
        if (isNew) {
          await apiFetch('/api/appointments/', { method: 'POST', body: fd })
        }
      } else {
        const body = {
          tattooer: Number(tattooerId),
          scheduled_at,
          description,
          appointment_kind: appointmentKind,
        }
        if (!(isClient && isNew)) {
          body.client = Number(clientId)
        }
        if (isNew) {
          await apiFetch('/api/appointments/', { method: 'POST', body: JSON.stringify(body) })
        }
      }
      navigate('/agendamentos')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!canDelete) return
    if (!window.confirm('Excluir este agendamento?')) return
    setRemoving(true)
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/`, { method: 'DELETE' })
      navigate('/agendamentos')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setRemoving(false)
    }
  }

  async function handleCancelAppointment() {
    if (isNew) return
    if (!window.confirm('Cancelar este agendamento?')) return
    setCancelling(true)
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/cancel/`, { method: 'POST' })
      await reloadAppointmentDetail()
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCancelling(false)
    }
  }

  async function handleStatusAction(action, successMessage) {
    if (!appointmentId) return
    setActionBusy(action)
    setError('')
    setFlowMessage('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/${action}/`, { method: 'POST' })
      await reloadAppointmentDetail()
      setFlowMessage(successMessage)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setActionBusy('')
    }
  }

  async function handleProposeChange(e) {
    e.preventDefault()
    if (!appointmentId || !proposedLocal.trim()) return
    setSaving(true)
    setError('')
    try {
      const scheduled_at = fromDatetimeLocalValue(proposedLocal)
      await apiFetch('/api/appointment-change-requests/', {
        method: 'POST',
        body: JSON.stringify({
          appointment: Number(appointmentId),
          proposed_changes: { scheduled_at },
        }),
      })
      setProposedLocal('')
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleAcceptChange(id) {
    setCrBusyId(id)
    setError('')
    try {
      await apiFetch(`/api/appointment-change-requests/${id}/accept/`, { method: 'POST' })
      await reloadAppointmentDetail()
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCrBusyId(null)
    }
  }

  async function handleRejectChange(id) {
    setCrBusyId(id)
    setError('')
    try {
      await apiFetch(`/api/appointment-change-requests/${id}/reject/`, { method: 'POST' })
      setCrKey((k) => k + 1)
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setCrBusyId(null)
    }
  }

  async function handleSubmitBudget(e) {
    e.preventDefault()
    if (isNew || !appointmentId) return
    setBudgetSaving(true)
    setBudgetMessage('')
    setError('')
    try {
      const updated = await apiFetch(`/api/appointments/${appointmentId}/budget/`, {
        method: budgetSentAt ? 'PATCH' : 'POST',
        body: JSON.stringify({
          budget_amount: budgetAmount,
          budget_notes: budgetNotes,
          move_to_waiting_budget: true,
        }),
      })
      setBudgetAmount(updated.budget_amount != null ? String(updated.budget_amount) : '')
      setBudgetNotes(updated.budget_notes ?? '')
      setBudgetSentAt(updated.budget_sent_at ?? '')
      setStatus(updated.status ?? status)
      setBudgetMessage('Orçamento enviado ao cliente.')
      await reloadAppointmentDetail()
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBudgetSaving(false)
    }
  }

  async function handleAcceptBudget() {
    if (!appointmentId) return
    setBudgetResponding('accept')
    setBudgetMessage('')
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/budget/accept/`, { method: 'POST' })
      setBudgetMessage('Orçamento aceito. A sessão foi confirmada.')
      await reloadAppointmentDetail()
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBudgetResponding('')
    }
  }

  async function handleRejectBudget() {
    if (!appointmentId) return
    if (!window.confirm('Recusar este orçamento? A solicitação será cancelada.')) return
    setBudgetResponding('reject')
    setBudgetMessage('')
    setError('')
    try {
      await apiFetch(`/api/appointments/${appointmentId}/budget/reject/`, { method: 'POST' })
      setBudgetMessage('Orçamento recusado. A solicitação foi cancelada.')
      await reloadAppointmentDetail()
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setBudgetResponding('')
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando agendamento" />
      </div>
    )
  }

  const portrait = presetTattooer
    ? tattooerPortraitSrc(presetTattooer.id, presetTattooer.name)
    : ''

  const canExplicitCancel =
    !isNew && status !== 'cancelled' && status !== 'done' && (isStudio || isClient || isTattooer)
  const newClientRequestLabel = appointmentKind === 'service' ? 'sessão' : 'avaliação'
  const shouldShowBudgetCard =
    !isNew && appointmentKind === 'service' && (isStudio || isTattooer || budgetAmount)
  const shouldPrioritizeBudget = canRespondBudget

  function renderBudgetCard() {
    return (
      <Card className="ic-mt-4">
        <CardHeader>
          <h2>Orçamento</h2>
        </CardHeader>
        <CardBody>
          {budgetMessage ? (
            <div className="ic-mb-2">
              <Alert>{budgetMessage}</Alert>
            </div>
          ) : null}
          {isStudio || isTattooer ? (
            <form onSubmit={handleSubmitBudget}>
              <Field label="Valor" id="a-budget-amount">
                <Input
                  id="a-budget-amount"
                  type="number"
                  min="0"
                  step="0.01"
                  required
                  value={budgetAmount}
                  onChange={(e) => setBudgetAmount(e.target.value)}
                />
              </Field>
              <Field label="Observações do orçamento" id="a-budget-notes">
                <Textarea
                  id="a-budget-notes"
                  rows={3}
                  value={budgetNotes}
                  onChange={(e) => setBudgetNotes(e.target.value)}
                />
              </Field>
              {budgetSentAt ? (
                <p className="ic-muted ic-mt-4">Enviado em {formatDateTime(budgetSentAt)}</p>
              ) : null}
              <div className="ic-form-actions">
                <Button type="submit" variant="primary" disabled={budgetSaving}>
                  {budgetSaving
                    ? 'Enviando…'
                    : budgetSentAt
                      ? 'Atualizar orçamento'
                      : 'Enviar orçamento'}
                </Button>
              </div>
            </form>
          ) : (
            <>
              <p className="ic-kpi-value">{formatBudgetAmount(budgetAmount)}</p>
              {budgetNotes ? <p className="ic-muted ic-mt-4">{budgetNotes}</p> : null}
              {budgetSentAt ? (
                <p className="ic-muted ic-mt-4">Enviado em {formatDateTime(budgetSentAt)}</p>
              ) : null}
              {canRespondBudget ? (
                <div className="ic-form-actions">
                  <Button
                    type="button"
                    variant="primary"
                    disabled={Boolean(budgetResponding)}
                    onClick={handleAcceptBudget}
                  >
                    {budgetResponding === 'accept' ? 'Aceitando…' : 'Aceitar orçamento'}
                  </Button>
                  <Button
                    type="button"
                    variant="secondary"
                    disabled={Boolean(budgetResponding)}
                    onClick={handleRejectBudget}
                  >
                    {budgetResponding === 'reject' ? 'Recusando…' : 'Recusar orçamento'}
                  </Button>
                </div>
              ) : null}
            </>
          )}
        </CardBody>
      </Card>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">
            {isNew && fromTattooerPage && presetTattooer
              ? `Solicitar ${newClientRequestLabel} com ${presetTattooer.name}`
              : isNew
                ? 'Novo agendamento'
                : 'Agendamento'}
          </h1>
          <p className="ic-page__lede">
            {isTattooer && !isNew
              ? 'Use as ações do fluxo para confirmar, iniciar ou concluir. Alterações em data, descrição, modalidade ou imagem geram uma solicitação para aceite.'
              : isClient && isNew
                ? appointmentKind === 'service'
                  ? 'Você já tem uma avaliação aprovada com este profissional. Solicite a sessão; o estúdio enviará um orçamento para sua resposta.'
                  : 'A primeira etapa é uma avaliação. O profissional consulta sua ficha de saúde antes de liberar uma sessão.'
                : !isNew && !isStudio && isClient
                  ? 'Alterações em data, descrição, modalidade ou imagem são enviadas como solicitação; a outra parte precisa aceitar antes de valer.'
                  : 'Datas em conflito com o mesmo tatuador são bloqueadas automaticamente.'}
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={goBack}>
          Voltar
        </Button>
      </div>

      {isNew && fromTattooerPage && presetTattooer ? (
        <div className="ic-profile-hero ic-mb-2">
          <div className="ic-profile-hero__media ic-profile-hero__media--compact">
            <img src={portrait} alt="" decoding="async" />
          </div>
          <div>
            <p className="ic-muted ic-mb-2">{presetTattooer.artistic_style}</p>
            <p className="ic-muted">Contato: {presetTattooer.contact}</p>
          </div>
        </div>
      ) : null}

      {isNew && isClient ? (
        <div className="ic-mb-2">
          <Alert>
            {appointmentKind === 'service'
                    ? 'Você está solicitando uma sessão. Anexe uma referência se quiser e aguarde o orçamento do estúdio.'
              : 'Você está solicitando uma avaliação. Mantenha sua '}
            {appointmentKind === 'consultation' ? <Link to="/fichas-saude">ficha de saúde</Link> : null}
            {appointmentKind === 'consultation' ? ' preenchida e anexe uma imagem de referência se quiser.' : null}
          </Alert>
        </div>
      ) : null}

      {shouldPrioritizeBudget ? (
        <>
          <div className="ic-mb-2">
            <Alert>
              Você recebeu um orçamento para esta sessão. Revise o valor e aceite ou recuse
              para o estúdio saber como seguir.
            </Alert>
          </div>
          {renderBudgetCard()}
        </>
      ) : null}

      <Card>
        <CardHeader>
          <h2>{isNew ? 'Solicitação' : 'Detalhes'}</h2>
        </CardHeader>
        <CardBody>
          {error ? (
            <div className="ic-mb-2">
              <Alert variant="error">{error}</Alert>
            </div>
          ) : null}
          {flowMessage ? (
            <div className="ic-mb-2">
              <Alert>{flowMessage}</Alert>
            </div>
          ) : null}

          {!isNew && updatedAt ? (
            <p className="ic-muted ic-mb-2">Última atualização: {formatDateTime(updatedAt)}</p>
          ) : null}

          {!isNew && healthSummary?.has_alerts ? (
            <div className="ic-mb-2">
              <Alert variant="error">
                <strong>Ficha de saúde (resumo):</strong>{' '}
                {healthSummary.allergies_preview ? (
                  <span> Alergias: {healthSummary.allergies_preview}</span>
                ) : null}{' '}
                {healthSummary.chronic_diseases_preview ? (
                  <span> Condições: {healthSummary.chronic_diseases_preview}</span>
                ) : null}
              </Alert>
            </div>
          ) : null}

          {!isNew && referenceImageUrl ? (
            <div className="ic-mb-2">
              <p className="ic-muted ic-mb-2">Imagem de referência</p>
              <img
                src={referenceImageUrl}
                alt="Referência do agendamento"
                className="ic-appt-ref-thumb"
              />
            </div>
          ) : null}
          {!isNew && appointmentKind === 'service' && sourceConsultationSummary ? (
            <div className="ic-mb-2">
              <Alert>
                Sessão liberada por avaliação de{' '}
                {formatDateTime(sourceConsultationSummary.scheduled_at)}.
              </Alert>
            </div>
          ) : null}

          <form onSubmit={handleSubmit}>
            {isPendingStudioRequest ? (
              <div className="ic-mb-2">
                <Alert>
                  Este pedido veio do cliente. O estúdio pode aceitar, recusar ou enviar uma
                  contraproposta de horário; os dados originais não são editados diretamente.
                </Alert>
              </div>
            ) : null}
            {isTattooer && !isNew ? null : (
              <>
                {isClient && isNew ? (
                  <p className="ic-muted ic-mb-2">
                    Você está solicitando {newClientRequestLabel} em seu próprio nome.
                  </p>
                ) : null}

                {showClientPicker ? (
                  <>
                    {clients.length > 0 ? (
                      <Field label="Cliente" id="a-client">
                        <Select
                          id="a-client"
                          required
                          disabled={isPendingStudioRequest}
                          value={clientId}
                          onChange={(e) => setClientId(e.target.value)}
                        >
                          <option value="">Selecione</option>
                          {clients.map((c) => (
                            <option key={c.id} value={c.id}>
                              {c.name} — {c.email}
                            </option>
                          ))}
                        </Select>
                      </Field>
                    ) : isStudio ? (
                      <div className="ic-mb-2">
                        <Alert>
                          Clientes aparecem automaticamente quando solicitam uma avaliação.
                        </Alert>
                      </div>
                    ) : null}
                  </>
                ) : null}

                {presetTattooer && (fromTattooerPage || !showTattooerSelect) ? (
                  <Field label="Profissional" id="a-tattooer-ro">
                    <Input id="a-tattooer-ro" value={presetTattooer.name} disabled />
                  </Field>
                ) : showTattooerSelect ? (
                  tattooers.length > 0 ? (
                    <Field label="Profissional" id="a-tattooer">
                      <Select
                        id="a-tattooer"
                        required
                        disabled={isPendingStudioRequest}
                        value={tattooerId}
                        onChange={(e) => setTattooerId(e.target.value)}
                      >
                        <option value="">Selecione</option>
                        {tattooers.map((t) => (
                          <option key={t.id} value={t.id}>
                            {t.name} — {t.artistic_style}
                          </option>
                        ))}
                      </Select>
                    </Field>
                  ) : isStudio ? (
                    <div className="ic-mb-2">
                      <Alert variant="error">
                        Não há profissionais cadastrados. Cadastre um tatuador antes de agendar.
                      </Alert>
                    </div>
                  ) : null
                ) : null}

                <Field label="Data e hora" id="a-when">
                  <Input
                    id="a-when"
                    type="datetime-local"
                    required
                    disabled={isPendingStudioRequest}
                    value={scheduledLocal}
                    onChange={(e) => setScheduledLocal(e.target.value)}
                  />
                </Field>
              </>
            )}

            {isTattooer && !isNew ? (
              <Field label="Modalidade" id="a-kind-t">
                <Select
                  id="a-kind-t"
                  value={appointmentKind}
                  onChange={(e) => setAppointmentKind(e.target.value)}
                >
                  <option value="service">{APPOINTMENT_KIND_LABELS.service}</option>
                  <option value="consultation">{APPOINTMENT_KIND_LABELS.consultation}</option>
                </Select>
              </Field>
            ) : null}

            {canAttachReferenceImage ? (
              <Field label={referenceImageLabel} hint={referenceImageHint} id="a-img">
                <Input
                  id="a-img"
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  disabled={isPendingStudioRequest}
                  onChange={(e) => setReferenceImageFile(e.target.files?.[0] ?? null)}
                />
              </Field>
            ) : null}

            <Field label="O que você quer fazer / referência" id="a-desc">
              <Textarea
                id="a-desc"
                rows={4}
                value={description}
                readOnly={isPendingStudioRequest}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Descreva a tatuagem, tamanho, local do corpo…"
              />
            </Field>

            {isClient ? (
              <Field label="Modalidade" id="a-kind-ro">
                <Input
                  id="a-kind-ro"
                  value={APPOINTMENT_KIND_LABELS[appointmentKind] ?? appointmentKind}
                  disabled
                />
              </Field>
            ) : isNew || !(isTattooer && !isNew) ? (
              <Field label="Modalidade" id="a-kind">
                <Select
                  id="a-kind"
                  value={appointmentKind}
                  disabled={isPendingStudioRequest}
                  onChange={(e) => setAppointmentKind(e.target.value)}
                >
                  <option value="service">{APPOINTMENT_KIND_LABELS.service}</option>
                  <option value="consultation">{APPOINTMENT_KIND_LABELS.consultation}</option>
                </Select>
              </Field>
            ) : null}

            {!isNew ? (
              <Field label="Situação" id="a-status">
                <Input id="a-status" value={APPOINTMENT_STATUS_LABELS[status] ?? status} disabled />
              </Field>
            ) : null}

            <div className="ic-form-actions">
              <Button
                type="submit"
                variant="primary"
                disabled={saving || removing || cancelling || Boolean(actionBusy)}
              >
                {saving
                  ? 'Salvando…'
                  : isNew && isClient
                    ? `Solicitar ${newClientRequestLabel}`
                    : 'Salvar'}
              </Button>
              {canConfirmConsultation ? (
                <Button
                  type="button"
                  variant="primary"
                  disabled={saving || removing || cancelling || Boolean(actionBusy)}
                  onClick={() => handleStatusAction('confirm', 'Avaliação confirmada.')}
                >
                  {actionBusy === 'confirm' ? 'Confirmando…' : 'Confirmar avaliação'}
                </Button>
              ) : null}
              {canStartAppointment ? (
                <Button
                  type="button"
                  variant="secondary"
                  disabled={saving || removing || cancelling || Boolean(actionBusy)}
                  onClick={() => handleStatusAction('start', 'Atendimento iniciado.')}
                >
                  {actionBusy === 'start' ? 'Iniciando…' : 'Iniciar atendimento'}
                </Button>
              ) : null}
              {canCompleteAppointment ? (
                <Button
                  type="button"
                  variant="secondary"
                  disabled={saving || removing || cancelling || Boolean(actionBusy)}
                  onClick={() => handleStatusAction('complete', 'Atendimento concluído.')}
                >
                  {actionBusy === 'complete' ? 'Concluindo…' : 'Concluir atendimento'}
                </Button>
              ) : null}
              <Button type="button" variant="ghost" disabled={saving || removing} onClick={goBack}>
                Voltar à lista
              </Button>
              {canExplicitCancel ? (
                <Button
                  type="button"
                  variant="danger"
                  disabled={saving || removing || cancelling || Boolean(actionBusy)}
                  onClick={handleCancelAppointment}
                >
                  {cancelling ? 'Cancelando…' : 'Cancelar agendamento'}
                </Button>
              ) : null}
              {canDelete ? (
                <Button
                  type="button"
                  variant="danger"
                  disabled={saving || removing}
                  onClick={handleDelete}
                >
                  {removing ? 'Excluindo…' : 'Excluir'}
                </Button>
              ) : null}
            </div>
          </form>
        </CardBody>
      </Card>

      {shouldShowBudgetCard && !shouldPrioritizeBudget ? renderBudgetCard() : null}

      {!isNew ? (
        <Card className="ic-mt-4">
          <CardHeader>
            <h2>Solicitações de alteração</h2>
          </CardHeader>
          <CardBody>
            <ul className="ic-cr-list">
              {changeRequests.map((cr) => (
                <li key={cr.id} className="ic-cr-list__item">
                  <div>
                    <strong>{cr.proposed_summary ?? 'Alteração'}</strong>
                    <span className="ic-muted"> — {cr.requested_by_display}</span>
                    {cr.proposed_scheduled_at ? (
                      <div className="ic-muted">
                        Horário proposto: {formatDateTime(cr.proposed_scheduled_at)}
                      </div>
                    ) : null}
                    <div className="ic-muted">
                      Status: {cr.status === 'pending' ? 'Pendente' : cr.status === 'accepted' ? 'Aceito' : 'Recusado'}
                    </div>
                  </div>
                  <div className="ic-inline-actions">
                    {cr.status === 'pending' && cr.can_respond ? (
                      <>
                        <Button
                          type="button"
                          size="sm"
                          variant="primary"
                          disabled={crBusyId === cr.id}
                          onClick={() => handleAcceptChange(cr.id)}
                        >
                          Aceitar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="secondary"
                          disabled={crBusyId === cr.id}
                          onClick={() => handleRejectChange(cr.id)}
                        >
                          Recusar
                        </Button>
                      </>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>

            <form className="ic-mt-4" onSubmit={handleProposeChange}>
              <Field label="Novo horário sugerido" id="a-cr-when">
                <Input
                  id="a-cr-when"
                  type="datetime-local"
                  value={proposedLocal}
                  onChange={(e) => setProposedLocal(e.target.value)}
                />
              </Field>
              <Button type="submit" variant="secondary" disabled={saving}>
                Enviar pedido de alteração
              </Button>
            </form>
          </CardBody>
        </Card>
      ) : null}
    </>
  )
}
