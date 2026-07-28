import { Link } from 'react-router-dom'
import { User } from 'lucide-react'
import styles from './Header.module.css'
import logo from '../assets/assistive_vision_logo.png' // Adjust path based on file location

function AppLogo() {
  return (
    <img 
      src={logo} 
      alt="AI-EYE Logo" 
      className={styles.logo}
      width="36"
      height="36"
    />
  )
}

function Header() {
  return (
    <header className={styles.header}>
      <div className={styles.brand}>
        <AppLogo />
        <span className={styles.appName}>AI-EYE</span>
      </div>

      <Link
        to="/profile"
        className={styles.profileButton}
        aria-label="Open your profile"
      >
        <User size={22} aria-hidden="true" />
      </Link>
    </header>
  )
}

export default Header