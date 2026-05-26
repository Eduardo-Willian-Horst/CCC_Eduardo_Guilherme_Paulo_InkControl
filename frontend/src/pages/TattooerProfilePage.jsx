import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import { ROLES } from '../lib/constants'
import { fetchAllPaginated } from '../lib/fetchAllPaginated'
import { tattooerPortraitSrc } from '../lib/tattooerPortrait'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'
import './tattooers-vitrine.css'

export function TattooerProfilePage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [t, setT] = useState(null)
  const [hasValidConsultation, setHasValidConsultation] = useState(false)

  const canBook = user?.role === ROLES.client || user?.role === ROLES.studio
  const isStudio = user?.role === ROLES.studio

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      try {
        const row = await apiFetch(`/api/tattooers/${id}/`)
        if (cancelled) return
        setT(row)
        if (user?.role === ROLES.client) {
          const consultations = await fetchAllPaginated(
            `/api/appointments/?tattooer=${row.id}&appointment_kind=consultation`,
          )
          if (!cancelled) {
            setHasValidConsultation(
              consultations.some((a) => a.status === 'confirmed' || a.status === 'done'),
            )
          }
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
  }, [id, user?.role])

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando perfil" />
      </div>
    )
  }

  if (error || !t) {
    return (
      <div className="ic-page__header">
        <Alert variant="error">{error || 'Profissional não encontrado.'}</Alert>
        <Button type="button" variant="secondary" className="ic-mt-4" onClick={() => navigate('/tatuadores')}>
          Voltar aos profissionais
        </Button>
      </div>
    )
  }

  if (!t.is_active && user?.role !== ROLES.studio) {
    return (
      <div className="ic-page__header">
        <Alert variant="neutral">Este profissional não está disponível para novos agendamentos.</Alert>
        <Button type="button" variant="secondary" className="ic-mt-4" onClick={() => navigate('/tatuadores')}>
          Voltar
        </Button>
      </div>
    )
  }

  const portrait = tattooerPortraitSrc(t.id, t.name)

  return (
    <>
      <div className="ic-page__header">
        <div>
          <p className="ic-muted ic-mb-2">
            <Link to="/tatuadores">Profissionais</Link>
          </p>
          <h1 className="ic-page__title">{t.name}</h1>
          <p className="ic-page__lede">{t.artistic_style}</p>
        </div>
        {isStudio ? (
          <Button type="button" variant="secondary" onClick={() => navigate(`/tatuadores/${t.id}/editar`)}>
            Editar cadastro
          </Button>
        ) : null}
      </div>

      <div className="ic-profile-hero">
        <div className="ic-profile-hero__media">
          <img src={portrait} alt="" width={480} height={600} decoding="async" />
        </div>
        <div>
          <p className="ic-muted ic-mb-3">
            Contato: <strong>{t.contact}</strong>
          </p>
          <p style={{ fontSize: 'var(--ds-text-md)', lineHeight: 'var(--ds-line-relaxed)' }}>
            {user?.role === ROLES.client
              ? hasValidConsultation
                ? 'Você já tem uma avaliação aprovada com este profissional. Agora pode solicitar uma sessão, que ainda precisa ser confirmada.'
                : 'Primeiro solicite uma avaliação. O profissional consulta sua ficha de saúde antes de liberar uma sessão.'
              : 'Escolha abaixo para solicitar um horário com este profissional. O estúdio confirma datas e valores conforme a conversa com você.'}
          </p>
          <div className="ic-profile-actions">
            {canBook && t.is_active ? (
              <Button type="button" onClick={() => navigate(`/tatuadores/${t.id}/agendar`)}>
                {user?.role === ROLES.client && hasValidConsultation
                  ? 'Solicitar sessão'
                  : user?.role === ROLES.client
                    ? 'Solicitar avaliação'
                    : `Agendar com ${t.name.split(' ')[0] || t.name}`}
              </Button>
            ) : null}
            <Button type="button" variant="ghost" onClick={() => navigate('/tatuadores')}>
              Ver outros profissionais
            </Button>
          </div>
        </div>
      </div>
    </>
  )
}
