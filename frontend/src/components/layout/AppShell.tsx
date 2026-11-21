import { ClipboardList, Coffee, CreditCard, Home, User } from 'lucide-react'
import { Link, NavLink, Outlet } from 'react-router'

import { useSignOut } from '../../hooks/useSignOut'
import { isSignedIn, useAuthStore } from '../../lib/auth-store'
import { Logo } from '../ui/Logo'
import styles from './AppShell.module.css'

const NAV_ITEMS = [
  { to: '/', label: 'Home', icon: Home, end: true },
  { to: '/shops', label: 'Cafés', icon: Coffee, end: false },
  { to: '/pass', label: 'Pass', icon: CreditCard, end: false },
  { to: '/orders', label: 'Orders', icon: ClipboardList, end: false },
  { to: '/profile', label: 'Profile', icon: User, end: false },
]

export function AppShell() {
  const signedIn = useAuthStore(isSignedIn)
  const signOut = useSignOut()

  return (
    <div className={styles.shell}>
      <a href="#main" className={styles.skipLink}>
        Skip to content
      </a>
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <Link to="/" aria-label="BrewPass home" className={styles.brand}>
            <Logo />
          </Link>
          {signedIn && (
            <nav aria-label="Main" className={styles.topNav}>
              {NAV_ITEMS.map(({ to, label, end }) => (
                <NavLink
                  key={to}
                  to={to}
                  end={end}
                  className={({ isActive }) => (isActive ? styles.activeLink : styles.link)}
                >
                  {label}
                </NavLink>
              ))}
              <button type="button" className={styles.link} onClick={signOut}>
                Sign out
              </button>
            </nav>
          )}
        </div>
      </header>

      <main id="main" className={styles.main} tabIndex={-1}>
        <Outlet />
      </main>

      {signedIn && (
        <nav aria-label="Main" className={styles.bottomNav}>
          {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) => (isActive ? styles.activeTab : styles.tab)}
            >
              <Icon size={22} aria-hidden />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  )
}
