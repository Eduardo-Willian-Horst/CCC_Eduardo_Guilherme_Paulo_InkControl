import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'

export function ClientFormPage() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()

  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [phone, setPhone] = useState('')
  const [email, setEmail] = useState('')
  const [isActive, setIsActive] = useState('true')
  const [originalIsActive, setOriginalIsActive] = useState('true')
  const [removing, setRemoving] = useState(false)

  useEffect(() => {
    if (isNew) return
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      try {
        const c = await apiFetch(`/api/clients/${id}/`)
        if (cancelled) return
        setName(c.name ?? '')
        setPhone(c.phone ?? '')
        setEmail(c.email ?? '')
        setIsActive(c.is_active ? 'true' : 'false')
        setOriginalIsActive(c.is_active ? 'true' : 'false')
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
  }, [id, isNew])

  async function handleSubmit(e) {
    e.preventDefault()
    setSaving(true)
    setError('')
    const body = {
      name: name.trim(),
      phone: phone.trim(),
      email: email.trim(),
      is_active: isActive === 'true',
    }
    if (!isNew && originalIsActive === 'true' && isActive === 'false') {
      if (!window.confirm('Inativar este cliente?')) {
        setSaving(false)
        return
      }
    }
    try {
      if (isNew) {
        await apiFetch('/api/clients/', { method: 'POST', body: JSON.stringify(body) })
      } else {
        await apiFetch(`/api/clients/${id}/`, { method: 'PUT', body: JSON.stringify(body) })
      }
      navigate('/clientes')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (isNew) return
    if (!window.confirm('Excluir este cliente?')) return
    setRemoving(true)
    setError('')
    try {
      await apiFetch(`/api/clients/${id}/`, { method: 'DELETE' })
      navigate('/clientes')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setRemoving(false)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando cliente" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">{isNew ? 'Novo cliente' : 'Editar cliente'}</h1>
          <p className="ic-page__lede">Dados cadastrais usados em agendamentos e fichas de saúde.</p>
        </div>
        <Button type="button" variant="secondary" onClick={() => navigate('/clientes')}>
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
          <form onSubmit={handleSubmit}>
            <Field label="Nome" id="c-name">
              <Input id="c-name" required value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Telefone" id="c-phone">
              <Input id="c-phone" required value={phone} onChange={(e) => setPhone(e.target.value)} />
            </Field>
            <Field label="E-mail" id="c-email">
              <Input id="c-email" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
            </Field>
            <Field label="Ativo" id="c-active">
              <Select id="c-active" value={isActive} onChange={(e) => setIsActive(e.target.value)}>
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </Select>
            </Field>
            <div className="ic-form-actions">
              <Button type="submit" variant="primary" disabled={saving || removing}>
                {saving ? 'Salvando…' : 'Salvar'}
              </Button>
              <Button type="button" variant="ghost" disabled={saving || removing} onClick={() => navigate('/clientes')}>
                Cancelar
              </Button>
              {!isNew ? (
                <Button type="button" variant="danger" disabled={saving || removing} onClick={handleDelete}>
                  {removing ? 'Excluindo…' : 'Excluir'}
                </Button>
              ) : null}
            </div>
          </form>
        </CardBody>
      </Card>
    </>
  )
}
