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

export function TattooerFormPage() {
  const { id } = useParams()
  const isNew = !id
  const navigate = useNavigate()

  const [loading, setLoading] = useState(!isNew)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [name, setName] = useState('')
  const [artisticStyle, setArtisticStyle] = useState('')
  const [contact, setContact] = useState('')
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
        const t = await apiFetch(`/api/tattooers/${id}/`)
        if (cancelled) return
        setName(t.name ?? '')
        setArtisticStyle(t.artistic_style ?? '')
        setContact(t.contact ?? '')
        setIsActive(t.is_active ? 'true' : 'false')
        setOriginalIsActive(t.is_active ? 'true' : 'false')
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
      artistic_style: artisticStyle.trim(),
      contact: contact.trim(),
      is_active: isActive === 'true',
    }
    if (!isNew && originalIsActive === 'true' && isActive === 'false') {
      if (!window.confirm('Inativar este tatuador?')) {
        setSaving(false)
        return
      }
    }
    try {
      if (isNew) {
        await apiFetch('/api/tattooers/', { method: 'POST', body: JSON.stringify(body) })
      } else {
        await apiFetch(`/api/tattooers/${id}/`, { method: 'PUT', body: JSON.stringify(body) })
      }
      navigate('/tatuadores')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setSaving(false)
    }
  }

  async function handleDelete() {
    if (isNew) return
    if (!window.confirm('Excluir este tatuador?')) return
    setRemoving(true)
    setError('')
    try {
      await apiFetch(`/api/tattooers/${id}/`, { method: 'DELETE' })
      navigate('/tatuadores')
    } catch (err) {
      setError(err.message ?? String(err))
    } finally {
      setRemoving(false)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando tatuador" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">{isNew ? 'Novo tatuador' : 'Editar tatuador'}</h1>
          <p className="ic-page__lede">Perfil profissional exibido internamente e para clientes.</p>
        </div>
        <Button type="button" variant="secondary" onClick={() => navigate('/tatuadores')}>
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
            <Field label="Nome" id="t-name">
              <Input id="t-name" required value={name} onChange={(e) => setName(e.target.value)} />
            </Field>
            <Field label="Estilo artístico" id="t-style">
              <Input
                id="t-style"
                required
                value={artisticStyle}
                onChange={(e) => setArtisticStyle(e.target.value)}
              />
            </Field>
            <Field label="Contato" id="t-contact">
              <Input
                id="t-contact"
                required
                value={contact}
                onChange={(e) => setContact(e.target.value)}
              />
            </Field>
            <Field label="Ativo" id="t-active">
              <Select id="t-active" value={isActive} onChange={(e) => setIsActive(e.target.value)}>
                <option value="true">Sim</option>
                <option value="false">Não</option>
              </Select>
            </Field>
            <div className="ic-form-actions">
              <Button type="submit" variant="primary" disabled={saving || removing}>
                {saving ? 'Salvando…' : 'Salvar'}
              </Button>
              <Button type="button" variant="ghost" disabled={saving || removing} onClick={() => navigate('/tatuadores')}>
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
