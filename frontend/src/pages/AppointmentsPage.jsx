import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import {
  APPOINTMENT_KIND_LABELS,
  APPOINTMENT_STATUS_LABELS,
  ROLES,
} from '../lib/constants'
import {
  addDaysToISODate,
  formatBudgetAmount,
  formatDateTime,
  formatTimeShort,
  todayISODateLocal,
} from '../lib/format'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Field, Input } from '../components/ui/Field'
import { PaginationBar } from '../components/ui/PaginationBar'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import { TableWrap, TableWithHead } from '../components/ui/Table'
import './pages.css'

const PAGE_SIZE = 10

const DEFAULT_OPEN_MIN = 7 * 60
const DEFAULT_CLOSE_MIN = 22 * 60

function clientLabel(row) {
  if (row.client && typeof row.client === 'object') {
    return row.client.name || row.client.email || 'Cliente'
  }
  return 'Cliente'
}

function tattooerLabel(row) {
  if (row.tattooer && typeof row.tattooer === 'object') {
    return row.tattooer.name || 'Profissional'
  }
  return 'Profissional'
}

function tattooerProfileId(row) {
  if (row.tattooer && typeof row.tattooer === 'object') return row.tattooer.id
  return row.tattooer
}

function canCancelRow(row) {
  return row.status !== 'done' && row.status !== 'cancelled'
}

function hasPendingBudget(row) {
  return row.status === 'waiting_budget' && row.budget_amount != null
}

function studioTimeToMinutes(value) {
  if (value == null || value === '') return null
  const parts = String(value).split(':')
  const h = parseInt(parts[0], 10)
  const m = parseInt(parts[1] ?? '0', 10)
  if (Number.isNaN(h)) return null
  const mm = Number.isNaN(m) ? 0 : m
  return (h * 60 + mm + 24 * 60) % (24 * 60)
}

function formatISODateHeading(isoDate) {
  if (!isoDate) return ''
  const parts = isoDate.split('-').map(Number)
  const d = new Date(parts[0], parts[1] - 1, parts[2])
  if (Number.isNaN(d.getTime())) return isoDate
  return new Intl.DateTimeFormat('pt-BR', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  }).format(d)
}

function assignGridPlacements(appointments, openMin, closeMin) {
  const totalMin = Math.max(60, closeMin - openMin)
  const enriched = []
  for (const a of appointments) {
    const start = new Date(a.scheduled_at)
    if (Number.isNaN(start.getTime())) continue
    const sm = start.getHours() * 60 + start.getMinutes()
    const dur = a.duration_minutes ?? 60
    const em = sm + dur
    const visStart = Math.max(sm, openMin)
    const visEnd = Math.min(em, closeMin)
    if (visEnd <= openMin || visStart >= closeMin) continue
    enriched.push({ a, sm, em, visStart, visEnd })
  }
  enriched.sort((x, y) => x.sm - y.sm || x.em - y.em)
  const colEnds = []
  const placed = []
  for (const it of enriched) {
    let col = 0
    for (; col < colEnds.length; col += 1) {
      if (it.sm >= colEnds[col]) break
    }
    if (col === colEnds.length) colEnds.push(it.em)
    else colEnds[col] = it.em
    placed.push({ ...it, col })
  }
  const colCount = Math.max(1, colEnds.length)
  return { placed, colCount, totalMin }
}

function minutesClock(m) {
  const h = Math.floor(m / 60) % 24
  const min = m % 60
  return `${String(h).padStart(2, '0')}:${String(min).padStart(2, '0')}`
}

function StudioDayAgenda({ appointments, openMin, closeMin, cancellingId, onCancel }) {
  const totalMin = Math.max(60, closeMin - openMin)
  const steps = []
  for (let m = openMin; m < closeMin; m += 60) {
    steps.push(m)
  }
  if (steps.length === 0) steps.push(openMin)
  const laneHeightRem = steps.length * 3
  const { placed, colCount } = assignGridPlacements(appointments, openMin, closeMin)
  const colPct = 100 / colCount

  return (
    <div className="ic-agenda">
      <div className="ic-agenda__hours" style={{ minHeight: `${laneHeightRem}rem` }}>
        {steps.map((m) => (
          <div key={m} className="ic-agenda__hour-cell">
            {minutesClock(m)}
          </div>
        ))}
      </div>
      <div className="ic-agenda__lane-wrap">
        <div className="ic-agenda__lane" style={{ minHeight: `${laneHeightRem}rem` }}>
          {steps.map((m) => (
            <div key={m} className="ic-agenda__row" />
          ))}
          <div className="ic-agenda__events">
            {placed.map(({ a, visStart, visEnd, col }) => {
              const top = ((visStart - openMin) / totalMin) * 100
              const hPct = ((visEnd - visStart) / totalMin) * 100
              const startIso = a.scheduled_at
              const durMin = a.duration_minutes ?? 60
              const startDate = new Date(startIso)
              const endDate = new Date(startDate.getTime() + durMin * 60 * 1000)
              const endLabel = formatTimeShort(endDate.toISOString())
              return (
                <div
                  key={a.id}
                  className="ic-agenda__event"
                  style={{
                    top: `${top}%`,
                    height: `${Math.max(hPct, 2.5)}%`,
                    left: `calc(${col} * ${colPct}%)`,
                    width: `calc(${colPct}% - 0.125rem)`,
                  }}
                >
                  <span className="ic-agenda__event-time">
                    {formatTimeShort(startIso)} – {endLabel}
                  </span>
                  <span className="ic-agenda__event-title">{clientLabel(a)}</span>
                  <span className="ic-agenda__event-meta">{tattooerLabel(a)}</span>
                  <div className="ic-agenda__event-actions">
                    <Badge variant="outline">{APPOINTMENT_STATUS_LABELS[a.status] ?? a.status}</Badge>
                    <Link to={`/tatuadores/${tattooerProfileId(a)}`}>Perfil</Link>
                    <Link to={`/agendamentos/${a.id}/editar`}>Detalhes</Link>
                    {canCancelRow(a) ? (
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        disabled={cancellingId === a.id}
                        onClick={() => onCancel(a.id)}
                      >
                        {cancellingId === a.id ? 'Cancelando…' : 'Cancelar'}
                      </Button>
                    ) : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </div>
    </div>
  )
}

export function AppointmentsPage() {
  const { user } = useAuth()
  const isClient = user?.role === ROLES.client
  const isTattooer = user?.role === ROLES.tattooer
  const isStudio = user?.role === ROLES.studio

  const [q, setQ] = useState('')
  const [status, setStatus] = useState('')
  const [appointmentKind, setAppointmentKind] = useState('')
  const [periodTab, setPeriodTab] = useState('')
  const [date, setDate] = useState('')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ count: 0, results: [] })
  const [cancellingId, setCancellingId] = useState(null)

  const [useAgendaView, setUseAgendaView] = useState(true)
  const [agendaDate, setAgendaDate] = useState(() => todayISODateLocal())
  const [studioBounds, setStudioBounds] = useState({
    openMin: DEFAULT_OPEN_MIN,
    closeMin: DEFAULT_CLOSE_MIN,
  })

  useEffect(() => {
    if (!isStudio) return undefined
    let cancelled = false
    apiFetch('/api/studio-settings/')
      .then((s) => {
        if (cancelled) return
        const o = studioTimeToMinutes(s.opens_at)
        const c = studioTimeToMinutes(s.closes_at)
        let openMin = o ?? DEFAULT_OPEN_MIN
        let closeMin = c ?? DEFAULT_CLOSE_MIN
        if (closeMin <= openMin) {
          openMin = DEFAULT_OPEN_MIN
          closeMin = DEFAULT_CLOSE_MIN
        }
        setStudioBounds({ openMin, closeMin })
      })
      .catch(() => {
        if (!cancelled) {
          setStudioBounds({ openMin: DEFAULT_OPEN_MIN, closeMin: DEFAULT_CLOSE_MIN })
        }
      })
    return () => {
      cancelled = true
    }
  }, [isStudio])

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      try {
        if (isStudio && useAgendaView) {
          const params = new URLSearchParams()
          params.set('period', 'day')
          params.set('date', agendaDate.trim() || todayISODateLocal())
          if (q.trim()) params.set('q', q.trim())
          if (status) params.set('status', status)
          if (appointmentKind) params.set('appointment_kind', appointmentKind)
          const path = `/api/appointments/?${params.toString()}`
          const results = await fetchAllPaginated(path)
          if (!cancelled) setData({ count: results.length, results })
        } else {
          const params = new URLSearchParams()
          params.set('page', String(page))
          if (q.trim()) params.set('q', q.trim())
          if (status) params.set('status', status)
          if (appointmentKind) params.set('appointment_kind', appointmentKind)
          if (periodTab) {
            params.set('period', periodTab)
            params.set('date', (date || todayISODateLocal()).trim())
          } else if (date.trim()) {
            params.set('date_from', date.trim())
            params.set('date_to', date.trim())
          }
          const res = await apiFetch(`/api/appointments/?${params.toString()}`)
          if (!cancelled) setData({ count: res.count ?? 0, results: res.results ?? [] })
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
  }, [
    page,
    q,
    status,
    appointmentKind,
    periodTab,
    date,
    reloadKey,
    isClient,
    isStudio,
    useAgendaView,
    agendaDate,
  ])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setReloadKey((k) => k + 1)
  }

  function setPeriod(next) {
    setPeriodTab(next)
    if (next && !date.trim()) {
      setDate(todayISODateLocal())
    }
    setPage(1)
    setReloadKey((k) => k + 1)
  }

  function shiftAgendaDay(delta) {
    setAgendaDate((d) => addDaysToISODate(d, delta))
    setReloadKey((k) => k + 1)
  }

  function goAgendaToday() {
    setAgendaDate(todayISODateLocal())
    setReloadKey((k) => k + 1)
  }

  async function handleCancelAppointment(id) {
    if (!window.confirm('Cancelar este agendamento?')) return
    setCancellingId(id)
    setError('')
    try {
      await apiFetch(`/api/appointments/${id}/cancel/`, { method: 'POST' })
      setReloadKey((k) => k + 1)
    } catch (e) {
      setError(e.message ?? String(e))
    } finally {
      setCancellingId(null)
    }
  }

  const showPeriodTabs = !isStudio || !useAgendaView
  const showTable = !isStudio || !useAgendaView
  const showAgenda = isStudio && useAgendaView

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">{isClient ? 'Meus agendamentos' : 'Agendamentos'}</h1>
          <p className="ic-page__lede">
            {isClient
              ? 'Acompanhe avaliações e sessões. A sessão só pode ser solicitada depois de uma avaliação aprovada.'
              : isStudio && useAgendaView
                ? 'Vista do dia alinhada ao expediente do estúdio. Use os filtros abaixo e “Aplicar” para refinar.'
                : 'Fila de avaliações e sessões com estados e bloqueio de conflito de horário por tatuador.'}
          </p>
        </div>
      </div>

      {isTattooer && user && !user.tattooer_linked ? (
        <div className="ic-mb-2">
          <Alert variant="error">
            Seu perfil de tatuador ainda não está vinculado a um cadastro profissional. Peça ao
            estúdio para concluir o vínculo; até lá, a lista pode aparecer vazia.
          </Alert>
        </div>
      ) : null}

      {isClient ? (
        <p className="ic-muted ic-mb-2">
          <Link to="/tatuadores">Ir para profissionais e agendar</Link>
        </p>
      ) : null}

      {showAgenda ? (
        <div className="ic-agenda-toolbar">
          <div className="ic-agenda-toolbar__title">{formatISODateHeading(agendaDate)}</div>
          <div className="ic-agenda-toolbar__nav">
            <Button type="button" variant="secondary" onClick={() => shiftAgendaDay(-1)}>
              Dia anterior
            </Button>
            <Button type="button" variant="secondary" onClick={goAgendaToday}>
              Hoje
            </Button>
            <Button type="button" variant="secondary" onClick={() => shiftAgendaDay(1)}>
              Próximo dia
            </Button>
            <Input
              type="date"
              value={agendaDate}
              onChange={(e) => {
                setAgendaDate(e.target.value || todayISODateLocal())
                setReloadKey((k) => k + 1)
              }}
              aria-label="Escolher data da agenda"
            />
            <Button type="button" variant="ghost" onClick={() => setUseAgendaView(false)}>
              Modo lista
            </Button>
          </div>
        </div>
      ) : null}

      {isStudio && !useAgendaView ? (
        <div className="ic-inline-actions ic-mb-2">
          <Button type="button" variant="secondary" onClick={() => setUseAgendaView(true)}>
            Modo agenda (dia)
          </Button>
        </div>
      ) : null}

      {showPeriodTabs ? (
        <div className="ic-period-tabs ic-mb-2" role="tablist" aria-label="Período da lista">
          <button
            type="button"
            className={periodTab === '' ? 'ic-period-tabs__btn ic-period-tabs__btn--active' : 'ic-period-tabs__btn'}
            role="tab"
            aria-selected={periodTab === ''}
            onClick={() => setPeriod('')}
          >
            Todos
          </button>
          <button
            type="button"
            className={periodTab === 'day' ? 'ic-period-tabs__btn ic-period-tabs__btn--active' : 'ic-period-tabs__btn'}
            role="tab"
            aria-selected={periodTab === 'day'}
            onClick={() => setPeriod('day')}
          >
            Dia
          </button>
          <button
            type="button"
            className={
              periodTab === 'week' ? 'ic-period-tabs__btn ic-period-tabs__btn--active' : 'ic-period-tabs__btn'
            }
            role="tab"
            aria-selected={periodTab === 'week'}
            onClick={() => setPeriod('week')}
          >
            Semana
          </button>
          <button
            type="button"
            className={
              periodTab === 'month' ? 'ic-period-tabs__btn ic-period-tabs__btn--active' : 'ic-period-tabs__btn'
            }
            role="tab"
            aria-selected={periodTab === 'month'}
            onClick={() => setPeriod('month')}
          >
            Mês
          </button>
        </div>
      ) : null}

      <form className="ic-toolbar" onSubmit={handleSearch}>
        <Field label="Busca" id="appt-q">
          <Input
            id="appt-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Descrição ou nome"
          />
        </Field>
        <Field label="Status" id="appt-status">
          <Select id="appt-status" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">Todos</option>
            {Object.entries(APPOINTMENT_STATUS_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Tipo" id="appt-kind">
          <Select
            id="appt-kind"
            value={appointmentKind}
            onChange={(e) => setAppointmentKind(e.target.value)}
          >
            <option value="">Todos</option>
            <option value="service">{APPOINTMENT_KIND_LABELS.service}</option>
            <option value="consultation">{APPOINTMENT_KIND_LABELS.consultation}</option>
          </Select>
        </Field>
        {showAgenda ? null : (
          <Field
            label="Data"
            id="appt-date"
            hint="Referência do período (Dia/Semana/Mês) ou filtro de um dia quando “Todos”."
          >
            <Input id="appt-date" type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          </Field>
        )}
        <Button type="submit" variant="secondary">
          Aplicar
        </Button>
      </form>

      {error ? (
        <div className="ic-mt-4">
          <Alert variant="error">{error}</Alert>
        </div>
      ) : null}

      {loading ? (
        <div className="ic-loading-block">
          <Spinner large role="status" aria-label="Carregando agendamentos" />
        </div>
      ) : null}

      {!loading && !error && showAgenda ? (
        data.results.length === 0 ? (
          <p className="ic-agenda__empty">Nenhum agendamento neste dia com os filtros atuais.</p>
        ) : (
          <StudioDayAgenda
            appointments={data.results}
            openMin={studioBounds.openMin}
            closeMin={studioBounds.closeMin}
            cancellingId={cancellingId}
            onCancel={handleCancelAppointment}
          />
        )
      ) : null}

      {!loading && !error && showTable ? (
        <>
          <TableWrap>
            <TableWithHead
              head={
                <>
                  <th>Data e hora</th>
                  {!isClient ? <th>Cliente</th> : null}
                  <th>Profissional</th>
                  <th>Tipo</th>
                  <th>Status</th>
                  <th></th>
                </>
              }
            >
              {data.results.map((a) => (
                <tr key={a.id}>
                  <td>{formatDateTime(a.scheduled_at)}</td>
                  {!isClient ? <td>{clientLabel(a)}</td> : null}
                  <td>
                    <Link to={`/tatuadores/${tattooerProfileId(a)}`}>Ver perfil</Link>
                  </td>
                  <td>
                    {a.appointment_kind === 'consultation' ? (
                      <Badge variant="outline">{APPOINTMENT_KIND_LABELS.consultation}</Badge>
                    ) : (
                      <>
                        <span className="ic-muted">{APPOINTMENT_KIND_LABELS.service}</span>
                        {a.source_consultation_summary ? (
                          <div className="ic-muted">Após avaliação</div>
                        ) : null}
                      </>
                    )}
                  </td>
                  <td>
                    <Badge variant="outline">
                      {APPOINTMENT_STATUS_LABELS[a.status] ?? a.status}
                    </Badge>
                    {isClient && hasPendingBudget(a) ? (
                      <div className="ic-muted">
                        Orçamento recebido: {formatBudgetAmount(a.budget_amount)}
                      </div>
                    ) : null}
                  </td>
                  <td>
                    <div className="ic-row-actions">
                      {isClient && hasPendingBudget(a) ? (
                        <Link to={`/agendamentos/${a.id}/editar`}>
                          Ver e responder orçamento
                        </Link>
                      ) : (
                        <Link to={`/agendamentos/${a.id}/editar`}>Detalhes</Link>
                      )}
                      {canCancelRow(a) ? (
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          disabled={cancellingId === a.id}
                          onClick={() => handleCancelAppointment(a.id)}
                        >
                          {cancellingId === a.id ? 'Cancelando…' : 'Cancelar agendamento'}
                        </Button>
                      ) : null}
                    </div>
                  </td>
                </tr>
              ))}
            </TableWithHead>
          </TableWrap>
          <PaginationBar
            count={data.count}
            pageSize={PAGE_SIZE}
            page={page}
            loading={loading}
            onPageChange={setPage}
          />
        </>
      ) : null}
    </>
  )
}
