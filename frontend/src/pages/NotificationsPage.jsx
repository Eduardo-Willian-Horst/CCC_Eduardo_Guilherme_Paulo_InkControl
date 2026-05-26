import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import { formatDateTime } from '../lib/format'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Spinner } from '../components/ui/Spinner'
import './pages.css'

export function NotificationsPage() {
  const { refreshMe } = useAuth()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [items, setItems] = useState([])
  const [busyId, setBusyId] = useState(null)

  async function load() {
    setLoading(true)
    setError('')
    try {
      const res = await apiFetch('/api/notifications/?page=1')
      setItems(res.results ?? [])
    } catch (e) {
      setError(e.message ?? String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function markRead(id) {
    setBusyId(id)
    setError('')
    try {
      await apiFetch(`/api/notifications/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify({ read: true }),
      })
      await load()
      await refreshMe()
    } catch (e) {
      setError(e.message ?? String(e))
    } finally {
      setBusyId(null)
    }
  }

  if (loading) {
    return (
      <div className="ic-loading-block">
        <Spinner large role="status" aria-label="Carregando notificações" />
      </div>
    )
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Notificações</h1>
          <p className="ic-page__lede">Avisos de agendamentos, orçamentos e pedidos de alteração.</p>
        </div>
      </div>

      {error ? (
        <div className="ic-mb-2">
          <Alert variant="error">{error}</Alert>
        </div>
      ) : null}

      <Card>
        <CardHeader>
          <h2>Caixa de entrada</h2>
        </CardHeader>
        <CardBody>
          {items.length === 0 ? (
            <p className="ic-muted">Nenhuma notificação.</p>
          ) : (
            <ul className="ic-notif-list">
              {items.map((n) => (
                <li key={n.id} className={n.read ? 'ic-notif-list__item' : 'ic-notif-list__item ic-notif-list__item--unread'}>
                  <div>
                    <p>{n.message}</p>
                    <p className="ic-muted">{formatDateTime(n.created_at)}</p>
                    {n.link ? (
                      <p className="ic-mt-4">
                        <Link to={n.link}>Abrir agendamento</Link>
                      </p>
                    ) : null}
                  </div>
                  {!n.read ? (
                    <Button
                      type="button"
                      size="sm"
                      variant="secondary"
                      disabled={busyId === n.id}
                      onClick={() => markRead(n.id)}
                    >
                      {busyId === n.id ? 'Marcando…' : 'Marcar como lida'}
                    </Button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </CardBody>
      </Card>
    </>
  )
}
