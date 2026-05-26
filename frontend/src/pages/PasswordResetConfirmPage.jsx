import { useMemo, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import './auth.css'

export function PasswordResetConfirmPage() {
  const location = useLocation()
  const params = useMemo(() => new URLSearchParams(location.search), [location.search])
  const uid = params.get('uid') || ''
  const token = params.get('token') || ''

  const [password, setPassword] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      const data = await apiFetch('/api/auth/password-reset/confirm/', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ uid, token, new_password: password }),
      })
      setMessage(data?.detail || 'Senha redefinida com sucesso.')
    } catch (err) {
      setError(err.message || 'Não foi possível redefinir a senha.')
    } finally {
      setSubmitting(false)
    }
  }

  const missingLinkData = !uid || !token

  return (
    <div className="ic-auth">
      <div className="ic-auth__card">
        <Card>
          <CardHeader>
            <h1 className="ic-auth__title">Redefinir senha</h1>
            <p className="ic-auth__lede">Escolha uma nova senha para sua conta.</p>
          </CardHeader>
          <CardBody>
            {missingLinkData ? (
              <Alert variant="error">Link inválido. Solicite uma nova recuperação de senha.</Alert>
            ) : (
              <form onSubmit={handleSubmit}>
                {error ? (
                  <div className="ic-auth__alert">
                    <Alert variant="error">{error}</Alert>
                  </div>
                ) : null}
                {message ? (
                  <div className="ic-auth__alert">
                    <Alert>{message}</Alert>
                  </div>
                ) : null}
                <Field label="Nova senha (mín. 8 caracteres)" id="reset-password">
                  <Input
                    id="reset-password"
                    type="password"
                    autoComplete="new-password"
                    required
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                  />
                </Field>
                <div className="ic-auth__stack">
                  <Button type="submit" variant="primary" disabled={submitting || Boolean(message)}>
                    {submitting ? 'Salvando…' : 'Redefinir senha'}
                  </Button>
                </div>
              </form>
            )}
          </CardBody>
        </Card>
        <p className="ic-auth__footer">
          <Link to="/entrar">Voltar para o login</Link>
        </p>
      </div>
    </div>
  )
}
