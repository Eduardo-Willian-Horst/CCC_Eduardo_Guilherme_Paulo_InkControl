import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { apiFetch } from '../api/client'
import { ROLES } from '../lib/constants'
import { formatDateTime } from '../lib/format'
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

export function ClientsPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const canWrite = user?.role === ROLES.studio

  const [q, setQ] = useState('')
  const [isActive, setIsActive] = useState('')
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
      if (isActive === 'true' || isActive === 'false') params.set('is_active', isActive)
      try {
        const res = await apiFetch(`/api/clients/?${params.toString()}`)
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
  }, [page, q, isActive, reloadKey])

  function handleSearch(e) {
    e.preventDefault()
    setPage(1)
    setReloadKey((k) => k + 1)
  }

  return (
    <>
      <div className="ic-page__header">
        <div>
          <h1 className="ic-page__title">Clientes</h1>
          <p className="ic-page__lede">
            Cadastro de clientes do estúdio. Apenas o papel estúdio cria, edita ou inativa
            registros.
          </p>
        </div>
        {canWrite ? (
          <Button type="button" onClick={() => navigate('/clientes/novo')}>
            Novo cliente
          </Button>
        ) : null}
      </div>

      <form className="ic-toolbar" onSubmit={handleSearch}>
        <Field label="Busca" id="clients-q">
          <Input id="clients-q" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nome, telefone ou e-mail" />
        </Field>
        <Field label="Situação" id="clients-active">
          <Select
            id="clients-active"
            value={isActive}
            onChange={(e) => setIsActive(e.target.value)}
          >
            <option value="">Todos</option>
            <option value="true">Ativos</option>
            <option value="false">Inativos</option>
          </Select>
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
          <Spinner large role="status" aria-label="Carregando clientes" />
        </div>
      ) : null}

      {!loading && !error ? (
        <>
          <TableWrap>
            <TableWithHead
              head={
                <>
                  <th>Nome</th>
                  <th>Contato</th>
                  <th>E-mail</th>
                  <th>Ativo</th>
                  <th>Atualizado</th>
                  <th></th>
                </>
              }
            >
              {data.results.map((c) => (
                <tr key={c.id}>
                  <td>{c.name}</td>
                  <td>{c.phone}</td>
                  <td>{c.email}</td>
                  <td>
                    {c.is_active ? (
                      <Badge>Sim</Badge>
                    ) : (
                      <Badge variant="muted">Não</Badge>
                    )}
                  </td>
                  <td className="ic-muted">{formatDateTime(c.updated_at)}</td>
                  <td>
                    <div className="ic-row-actions">
                      {canWrite ? (
                        <Link to={`/clientes/${c.id}/editar`}>Editar</Link>
                      ) : (
                        <span className="ic-muted">Somente leitura</span>
                      )}
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
