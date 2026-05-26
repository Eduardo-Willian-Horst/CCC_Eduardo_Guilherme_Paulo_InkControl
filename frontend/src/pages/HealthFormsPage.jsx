import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import { ROLES } from '../lib/constants'
import { formatDateTime } from '../lib/format'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Field, Input } from '../components/ui/Field'
import { PaginationBar } from '../components/ui/PaginationBar'
import { Spinner } from '../components/ui/Spinner'
import { TableWrap, TableWithHead } from '../components/ui/Table'
import './pages.css'

const PAGE_SIZE = 10

export function HealthFormsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const canCreate = user?.role === ROLES.studio || user?.role === ROLES.client

  const [q, setQ] = useState('')
  const [page, setPage] = useState(1)
  const [reloadKey, setReloadKey] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [data, setData] = useState({ count: 0, results: [] })

  useEffect(() => {
    let cancelled = false
    async function run() {
      setLoading(true)
      setError('')
      const params = new URLSearchParams()
      params.set('page', String(page))
      if (q.trim()) params.set('q', q.trim())
      try {
        const res = await apiFetch(`/api/health-forms/?${params.toString()}`)
        if (!cancelled) setData({ count: res.count ?? 0, results: res.results ?? [] })
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
  }, [page, q, reloadKey])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setReloadKey((k) => k + 1)
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Fichas de saúde</h1>
          <p className="ic-page__lede">
            Registro único por cliente (OneToOne): alergias, doenças crônicas e histórico de
            cicatrização.
          </p>
        </div>
        {canCreate ? (
          <Button type="button" onClick={() => navigate('/fichas-saude/novo')}>
            Nova ficha
          </Button>
        ) : null}
      </div>

      <form className="ic-toolbar" onSubmit={handleSearch}>
        <Field label="Busca" id="hf-q">
          <Input
            id="hf-q"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Cliente ou campos clínicos"
          />
        </Field>
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
          <Spinner large role="status" aria-label="Carregando fichas" />
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <TableWrap>
            <TableWithHead
              head={
                <>
                  <th>Cliente</th>
                  <th>Resumo</th>
                  <th>Atualizado</th>
                  <th></th>
                </>
              }
            >
              {data.results.map((f) => (
                <tr key={f.id}>
                  <td>
                    <div>{f.client_name || 'Cliente'}</div>
                    {f.client_email ? <div className="ic-muted">{f.client_email}</div> : null}
                  </td>
                  <td className="ic-muted">
                    {(f.allergies || '').slice(0, 80)}
                    {(f.allergies || '').length > 80 ? '…' : ''}
                  </td>
                  <td>{formatDateTime(f.updated_at)}</td>
                  <td>
                    <Link to={`/fichas-saude/${f.id}/editar`}>Abrir</Link>
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
