import { useState } from 'react'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api/client'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import './auth.css'

export function PasswordResetRequestPage() {
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setMessage('')
    setSubmitting(true)
    try {
      const data = await apiFetch('/api/auth/password-reset/request/', {
        method: 'POST',
        skipAuth: true,
        body: JSON.stringify({ email: email.trim() }),
      })
      setMessage(data?.detail || 'Se existir conta com este e-mail, enviaremos instruções.')
    } catch (err) {
      setError(err.message || 'Não foi possível solicitar a redefinição.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="ic-auth">
      <div className="ic-auth__card">
        <Card>
          <CardHeader>
            <h1 className="ic-auth__title">Recuperar senha</h1>
            <p className="ic-auth__lede">Informe seu e-mail para receber o link de redefinição.</p>
          </CardHeader>
          <CardBody>
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
              <Field label="E-mail" id="reset-email">
                <Input
                  id="reset-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <div className="ic-auth__stack">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting ? 'Enviando…' : 'Enviar instruções'}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
        <p className="ic-auth__footer">
          Lembrou a senha? <Link to="/entrar">Entrar</Link>
        </p>
      </div>
    </div>
  )
}
