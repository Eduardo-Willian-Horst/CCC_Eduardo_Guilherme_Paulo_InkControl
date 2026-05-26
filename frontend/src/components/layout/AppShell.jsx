import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { ROLE_LABELS, ROLES } from '../../lib/constants'
import { Button } from '../ui/Button'
import './AppShell.css'

function navLabel(item, role) {
  if (role === ROLES.client && item.clientLabel) return item.clientLabel
  return item.label
}

const NAV = [
  { to: '/tatuadores', label: 'Profissionais', roles: null, clientLabel: 'Profissionais' },
  { to: '/pedidos', label: 'Pedidos', roles: [ROLES.studio] },
  { to: '/agendamentos', label: 'Agendamentos', roles: null, clientLabel: 'Meus agendamentos' },
  { to: '/notificacoes', label: 'Notificações', roles: null, clientLabel: 'Notificações' },
  { to: '/fichas-saude', label: 'Fichas de saúde', roles: null, clientLabel: 'Minha saúde' },
  { to: '/clientes', label: 'Clientes', roles: [ROLES.studio, ROLES.tattooer] },
  { to: '/estudio/horario', label: 'Horário do estúdio', roles: [ROLES.studio] },
  { to: '/estudio/assinatura', label: 'Assinatura', roles: [ROLES.studio] },
]

export function AppShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const filteredNav = NAV.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role)),
  )

  async function handleLogout() {
    await logout()
    navigate('/entrar', { replace: true })
  }

  return (
    <div className="ic-shell">
      <aside className="ic-sidebar" aria-label="Navegação principal">
        <div className="ic-sidebar__brand">
          <NavLink to="/tatuadores" className="ic-sidebar__brand-link">
            <div className="ic-sidebar__title">InkControl</div>
          </NavLink>
          <div className="ic-sidebar__subtitle">
            {user?.role === ROLES.client
              ? 'Agende com quem combina com você.'
              : 'Gestão do estúdio e vitrine para clientes.'}
          </div>
        </div>
        <nav className="ic-nav">
          {filteredNav.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? 'ic-nav__active' : undefined)}
            >
              <span className="ic-nav__label">
                {navLabel(item, user?.role)}
                {item.to === '/notificacoes' && user?.unread_notifications ? (
                  <span className="ic-nav__badge" aria-label="Não lidas">
                    {user.unread_notifications > 99 ? '99+' : user.unread_notifications}
                  </span>
                ) : null}
              </span>
            </NavLink>
          ))}
        </nav>
        <div className="ic-sidebar__footer">InkControl</div>
      </aside>
      <div className="ic-main">
        <header className="ic-topbar">
          <span className="ic-topbar__eyebrow">InkControl</span>
          <div className="ic-topbar__user">
            {user ? (
              <>
                <span className="ic-topbar__name">{user.name || user.email}</span>
                <span className="ic-role-pill">{ROLE_LABELS[user.role] ?? user.role}</span>
                <Button type="button" variant="secondary" size="sm" onClick={handleLogout}>
                  Sair
                </Button>
              </>
            ) : null}
          </div>
        </header>
        <main className="ic-page">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
