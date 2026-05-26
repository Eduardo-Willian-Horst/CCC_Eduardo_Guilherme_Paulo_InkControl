import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Badge } from '../components/ui/Badge'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Spinner } from '../components/ui/Spinner'
import { formatDateTime } from '../lib/format'
import './pages.css'

export function SubscriptionPage() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [note, setNote] = useState('')
  const [simulateFailure, setSimulateFailure] = useState(false)
  const [subscription, setSubscription] = useState(null)

  async function loadSubscription() {
    setLoading(true)
    setError('')
    try {
      const data = await apiFetch('/api/studio/subscription/')
      setSubscription(data)
    } catch (e) {
      setError(e.message ?? String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadSubscription()
  }, [])

  async function handlePay(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const data = await apiFetch('/api/studio/subscription/pay/', {
        method: 'POST',
        body: JSON.stringify({
          note: note.trim() || undefined,
          simulate_failure: simulateFailure,
        }),
      })
      setSuccess(data?.detail || 'Mensalidade atualizada.')
      await loadSubscription()
    } catch (err) {
      setError(err.message ?? String(err))
      await loadSubscription()
    } finally {
      setSaving(false)
    }
  }

  async function handleCancel() {
    if (!window.confirm('Cancelar a renovação da mensalidade?')) return
    setSaving(true)
    setError('')
    setSuccess('')
    try {
      const data = await apiFetch('/api/studio/subscription/cancel/', { method: 'POST' })
      setSuccess(data?.detail || 'Renovação cancelada.')
      await loadSubscription()
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando assinatura" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Assinatura</h1>
          <p className="ic-page__lede">
            Controle acadêmico da mensalidade do estúdio, com pagamento simulado.
          </p>
        </div>
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

      <div className="ic-kpi-grid ic-mb-3">
        <Card>
          <CardBody>
            <p className="ic-muted">Status</p>
            <p className="ic-kpi-value">
              {subscription?.is_active ? <Badge>Ativa</Badge> : <Badge variant="muted">Inativa</Badge>}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="ic-muted">Pago até</p>
            <p className="ic-kpi-value">
              {subscription?.paid_until ? formatDateTime(subscription.paid_until) : 'Não informado'}
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardBody>
            <p className="ic-muted">Última tentativa</p>
            <p className="ic-kpi-value">
              {subscription?.last_payment_attempt_ok === true
                ? 'Aprovada'
                : subscription?.last_payment_attempt_ok === false
                  ? 'Recusada'
                  : 'Sem tentativa'}
            </p>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <h2>Pagamento simulado</h2>
        </CardHeader>
        <CardBody>
          {subscription?.payment_cancelled_at ? (
            <p className="ic-muted ic-mb-2">
              Renovação cancelada em {formatDateTime(subscription.payment_cancelled_at)}.
            </p>
          ) : null}
          {subscription?.last_payment_attempt_note ? (
            <p className="ic-muted ic-mb-2">Nota: {subscription.last_payment_attempt_note}</p>
          ) : null}
          <form onSubmit={handlePay}>
            <Field label="Observação da tentativa" id="sub-note">
              <Input
                id="sub-note"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="Ex.: pagamento mensal"
              />
            </Field>
            <label className="ic-check-row">
              <input
                type="checkbox"
                checked={simulateFailure}
                onChange={(e) => setSimulateFailure(e.target.checked)}
              />
              Simular falha no pagamento
            </label>
            <div className="ic-form-actions">
              <Button type="submit" variant="primary" disabled={saving}>
                {saving ? 'Processando…' : 'Pagar mensalidade'}
              </Button>
              <Button type="button" variant="secondary" disabled={saving} onClick={handleCancel}>
                Cancelar renovação
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </>
  )
}
