import { NavLink } from 'react-router-dom'
import { Home, LogOut, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext.jsx'
import styles from './Sidebar.module.css'

const NAV_ITEMS = [
  { to: '/home', label: 'Home', icon: Home },
  { to: '/profile', label: 'Profile', icon: User },
]

function SidebarLinks({ onNavigate }) {
  const { logout } = useAuth()

  const handleLogout = () => {
    logout()
    onNavigate?.()
  }

  return (
    <ul className={styles.list}>
      {NAV_ITEMS.map(({ to, label, icon: Icon }) => (
        <li key={to}>
          <NavLink
            to={to}
            className={({ isActive }) =>
              [styles.link, isActive ? styles.active : null]
                .filter(Boolean)
                .join(' ')
            }
            onClick={onNavigate}
          >
            <Icon size={22} aria-hidden="true" />
            <span>{label}</span>
          </NavLink>
        </li>
      ))}
      <li>
        <button type="button" className={styles.link} onClick={handleLogout}>
          <LogOut size={22} aria-hidden="true" />
          <span>Logout</span>
        </button>
      </li>
    </ul>
  )
}

function Sidebar({ isOpen, onClose }) {
  const links = <SidebarLinks onNavigate={onClose} />

  return (
    <>
      <nav
        className={`${styles.sidebar} ${styles.desktop}`}
        aria-label="Primary"
      >
        {links}
      </nav>

      {isOpen ? (
        <>
          <button
            type="button"
            className={styles.backdrop}
            onClick={onClose}
            aria-label="Close navigation"
          />
          <nav
            className={`${styles.sidebar} ${styles.mobile}`}
            aria-label="Primary"
          >
            {links}
          </nav>
        </>
      ) : null}
    </>
  )
}

export default Sidebar
