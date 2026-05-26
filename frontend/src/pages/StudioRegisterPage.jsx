import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Spinner } from '../components/ui/Spinner'
import './auth.css'

export function StudioRegisterPage() {
  const { registerStudio, user, loading } = useAuth()
  const navigate = useNavigate()

  const [studioName, setStudioName] = useState('')
  const [adminName, setAdminName] = useState('')
  const [adminEmail, setAdminEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (loading) {
    return (
      <div className="ic-auth">
        <div className="ic-auth__spinner-wrap">
          <Spinner large role="status" aria-label="Carregando sessão" />
        </div>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/tatuadores" replace />
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await registerStudio({
        studio_name: studioName.trim(),
        admin_name: adminName.trim(),
        admin_email: adminEmail.trim(),
        password,
      })
      navigate('/tatuadores', { replace: true })
    } catch (err) {
      setError(err.message || 'Não foi possível cadastrar o estúdio.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="ic-auth">
      <div className="ic-auth__card">
        <Card>
          <CardHeader>
            <h1 className="ic-auth__title">Cadastrar estúdio</h1>
            <p className="ic-auth__lede">Crie o tenant do estúdio e a conta administradora.</p>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSubmit}>
              {error ? (
                <div className="ic-auth__alert">
                  <Alert variant="error">{error}</Alert>
                </div>
              ) : null}
              <Field label="Nome do estúdio" id="studio-name">
                <Input
                  id="studio-name"
                  required
                  value={studioName}
                  onChange={(e) => setStudioName(e.target.value)}
                />
              </Field>
              <Field label="Nome do administrador" id="studio-admin-name">
                <Input
                  id="studio-admin-name"
                  autoComplete="name"
                  required
                  value={adminName}
                  onChange={(e) => setAdminName(e.target.value)}
                />
              </Field>
              <Field label="E-mail do administrador" id="studio-admin-email">
                <Input
                  id="studio-admin-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={adminEmail}
                  onChange={(e) => setAdminEmail(e.target.value)}
                />
              </Field>
              <Field label="Senha (mín. 8 caracteres)" id="studio-password">
                <Input
                  id="studio-password"
                  type="password"
                  autoComplete="new-password"
                  minLength={8}
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <div className="ic-auth__stack">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? 'Criando…' : 'Cadastrar estúdio'}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
        <p className="ic-auth__footer">
          Já tem conta? <Link to="/entrar">Entrar</Link>
        </p>
      </div>
    </div>
  )
}
