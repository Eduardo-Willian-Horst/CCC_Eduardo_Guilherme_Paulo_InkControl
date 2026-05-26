import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { ROLES } from '../lib/constants'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { formatDateTime } from '../lib/format'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Select } from '../components/ui/Select'
import { Textarea } from '../components/ui/Textarea'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'

export function HealthFormFormPage() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()

  const [me, setMe] = useState(null)
  const [updatedAt, setUpdatedAt] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [error, setError] = useState('')

  const [clients, setClients] = useState([])
  const [clientId, setClientId] = useState('')
  const [clientDisplay, setClientDisplay] = useState('')
  const [allergies, setAllergies] = useState('')
  const [chronicDiseases, setChronicDiseases] = useState('')
  const [healingHistory, setHealingHistory] = useState('')
  const [notes, setNotes] = useState('')

  useEffect(() => {
    let cancelled = false
    async function boot() {
      setLoading(true)
      setError('')
      try {
        const user = await apiFetch('/api/auth/me/')
        if (cancelled) return
        setMe(user)

        if (user.role === ROLES.studio || user.role === ROLES.tattooer) {
          try {
            const c = await fetchAllPaginated('/api/clients/?page=1')
            if (!cancelled) setClients(c)
          } catch {
            if (!cancelled) setClients([])
          }
        } else {
          setClients([])
        }

        if (!isNew) {
          const f = await apiFetch(`/api/health-forms/${id}/`)
          if (cancelled) return
          setClientId(String(f.client))
          setClientDisplay(f.client_name || f.client_email || '')
          setAllergies(f.allergies ?? '')
          setChronicDiseases(f.chronic_diseases ?? '')
          setHealingHistory(f.healing_history ?? '')
          setNotes(f.notes ?? '')
          setUpdatedAt(f.updated_at ?? '')
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
  }, [id, isNew])

  useEffect(() => {
    if (!me || !isNew) return
    if (me.role === ROLES.tattooer) navigate('/fichas-saude', { replace: true })
  }, [me, isNew, navigate])

  const isStudio = me?.role === ROLES.studio
  const readOnly = me?.role === ROLES.tattooer && !isNew
  const canDelete = isStudio && !isNew

  async function handleSubmit(e) {
    e.preventDefault()
    if (readOnly) return
    setSaving(true)
    setError('')
    const body = {
      allergies,
      chronic_diseases: chronicDiseases,
      healing_history: healingHistory,
      notes,
    }
    if (!(isNew && me?.role === ROLES.client)) {
      body.client = Number(clientId)
    }
    try {
      if (isNew) {
        await apiFetch('/api/health-forms/', { method: 'POST', body: JSON.stringify(body) })
      } else {
        await apiFetch(`/api/health-forms/${id}/`, { method: 'PUT', body: JSON.stringify(body) })
      }
      navigate('/fichas-saude')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (!canDelete) return
    if (!window.confirm('Excluir esta ficha?')) return
    setRemoving(true)
    setError('')
    try {
      await apiFetch(`/api/health-forms/${id}/`, { method: 'DELETE' })
      navigate('/fichas-saude')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setRemoving(false)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando ficha" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">{isNew ? 'Nova ficha de saúde' : 'Editar ficha de saúde'}</h1>
          <p className="ic-page__lede">
            Informações clínicas relevantes antes da sessão, conforme escopo do produto.
          </p>
        </div>
        <Button type="button" variant="secondary" onClick={() => navigate('/fichas-saude')}>
          Voltar
        </Button>
      </div>

      <Card>
        <CardHeader>
          <h2>Formulário</h2>
        </CardHeader>
        <CardBody>
          {error ? (
            <div className="ic-mb-2">
              <Alert variant="error">{error}</Alert>
            </div>
          ) : null}

          {!isNew && updatedAt ? (
            <p className="ic-muted ic-mb-2">Última atualização: {formatDateTime(updatedAt)}</p>
          ) : null}

          {readOnly ? (
            <Alert variant="neutral" className="ic-mb-2">
              Seu papel pode apenas consultar fichas. Alterações são feitas pelo estúdio ou pelo
              cliente.
            </Alert>
          ) : null}

          <form onSubmit={handleSubmit}>
            {isNew ? (
              me?.role === ROLES.client ? (
                <p className="ic-muted ic-mb-2">
                  A ficha será salva no seu nome, usando o e-mail da sua conta.
                </p>
              ) : clients.length > 0 ? (
                <Field label="Cliente" id="hf-client">
                  <Select
                    id="hf-client"
                    required
                    disabled={readOnly}
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
              ) : (
                <Alert variant="error">
                  Não foi possível carregar a lista de clientes. Volte à lista e tente novamente.
                </Alert>
              )
            ) : (
              <Field label="Cliente" id="hf-client-ro">
                <Input
                  id="hf-client-ro"
                  value={clientDisplay || 'Cliente vinculado'}
                  disabled
                />
              </Field>
            )}

            <Field label="Alergias" id="hf-allergies">
              <Textarea
                id="hf-allergies"
                rows={3}
                readOnly={readOnly}
                value={allergies}
                onChange={(e) => setAllergies(e.target.value)}
              />
            </Field>
            <Field label="Doenças crônicas" id="hf-chronic">
              <Textarea
                id="hf-chronic"
                rows={3}
                readOnly={readOnly}
                value={chronicDiseases}
                onChange={(e) => setChronicDiseases(e.target.value)}
              />
            </Field>
            <Field label="Histórico de cicatrização" id="hf-heal">
              <Textarea
                id="hf-heal"
                rows={3}
                readOnly={readOnly}
                value={healingHistory}
                onChange={(e) => setHealingHistory(e.target.value)}
              />
            </Field>
            <Field label="Observações" id="hf-notes">
              <Textarea
                id="hf-notes"
                rows={3}
                readOnly={readOnly}
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
              />
            </Field>

            {readOnly ? (
              <div className="ic-form-actions">
                <Button type="button" variant="secondary" onClick={() => navigate('/fichas-saude')}>
                  Voltar à lista
                </Button>
              </div>
            ) : (
              <div className="ic-form-actions">
                <Button type="submit" variant="primary" disabled={saving || removing}>
                  {saving ? 'Salvando…' : 'Salvar'}
                </Button>
                <Button
                  type="button"
                  variant="ghost"
                  disabled={saving || removing}
                  onClick={() => navigate('/fichas-saude')}
                >
                  Cancelar
                </Button>
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
            )}
          </form>
        </CardBody>
      </Card>
    </>
  )
}
