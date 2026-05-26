import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Spinner } from '../components/ui/Spinner'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import './auth.css'

export function LoginPage() {
  const { login, user, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from || '/'

  const [email, setEmail] = useState('')
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
      await login(email.trim(), password)
      navigate(from, { replace: true })
    } catch (err) {
      setError(err.message || 'Falha no login.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="ic-auth">
      <div className="ic-auth__card">
        <Card>
          <CardHeader>
            <h1 className="ic-auth__title">Entrar</h1>
            <p className="ic-auth__lede">InkControl — gestão de estúdio</p>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSubmit}>
              {error ? (
                <div className="ic-auth__alert">
                  <Alert variant="error">{error}</Alert>
                </div>
              ) : null}
              <Field label="E-mail" id="login-email">
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="Senha" id="login-password">
                <Input
                  id="login-password"
                  type="password"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <div className="ic-auth__stack">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? 'Entrando…' : 'Entrar'}
                </Button>
              </div>
            </form>
            <p className="ic-auth__footer">
              <Link to="/recuperar-senha">Esqueci minha senha</Link>
            </p>
          </CardBody>
        </Card>
        <p className="ic-auth__footer">
          Não tem conta? <Link to="/cadastro">Criar cadastro</Link>
        </p>
      </div>
    </div>
  )
}
