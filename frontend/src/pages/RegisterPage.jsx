import { useState } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { ROLE_LABELS, ROLES } from '../lib/constants'
import { Alert } from '../components/ui/Alert'
import { Button } from '../components/ui/Button'
import { Card, CardBody, CardHeader } from '../components/ui/Card'
import { Field, Input } from '../components/ui/Field'
import { Select } from '../components/ui/Select'
import { Spinner } from '../components/ui/Spinner'
import './auth.css'

export function RegisterPage() {
  const { register, registerStudio, user, loading } = useAuth()
  const navigate = useNavigate()

  const [name, setName] = useState('')
  const [studioName, setStudioName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState(ROLES.client)
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
      if (role === ROLES.studio) {
        await registerStudio({
          studio_name: studioName.trim(),
          admin_name: name.trim(),
          admin_email: email.trim(),
          password,
        })
      } else {
        await register({
          name: name.trim(),
          email: email.trim(),
          password,
          role: ROLES.client,
        })
      }
      navigate('/tatuadores', { replace: true })
    } catch (err) {
      setError(err.message || 'Não foi possível cadastrar.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="ic-auth">
      <div className="ic-auth__card">
        <Card>
          <CardHeader>
            <h1 className="ic-auth__title">Criar conta</h1>
            <p className="ic-auth__lede">
              Cadastre-se como cliente para agendar ou como estúdio para administrar a agenda.
            </p>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleSubmit}>
              {error ? (
                <div className="ic-auth__alert">
                  <Alert variant="error">{error}</Alert>
                </div>
              ) : null}
              <Field label="Tipo de cadastro" id="reg-role">
                <Select
                  id="reg-role"
                  value={role}
                  onChange={(e) => setRole(e.target.value)}
                >
                  <option value={ROLES.client}>{ROLE_LABELS.client}</option>
                  <option value={ROLES.studio}>{ROLE_LABELS.studio}</option>
                </Select>
              </Field>
              {role === ROLES.studio ? (
                <Field label="Nome do estúdio" id="reg-studio-name">
                  <Input
                    id="reg-studio-name"
                    required
                    value={studioName}
                    onChange={(e) => setStudioName(e.target.value)}
                  />
                </Field>
              ) : null}
              <Field
                label={role === ROLES.studio ? 'Nome do administrador' : 'Nome completo'}
                id="reg-name"
              >
                <Input
                  id="reg-name"
                  autoComplete="name"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="E-mail" id="reg-email">
                <Input
                  id="reg-email"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
              <Field label="Senha (mín. 8 caracteres)" id="reg-password">
                <Input
                  id="reg-password"
                  type="password"
                  autoComplete="new-password"
                  required
                  minLength={8}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </Field>
              <div className="ic-auth__stack">
                <Button type="submit" variant="primary" disabled={submitting}>
                  {submitting
                    ? 'Criando…'
                    : role === ROLES.studio
                      ? 'Cadastrar estúdio'
                      : 'Cadastrar cliente'}
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
