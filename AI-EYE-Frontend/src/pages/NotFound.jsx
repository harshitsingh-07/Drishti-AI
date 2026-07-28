import { useNavigate } from 'react-router-dom'
import Button from '../components/Button.jsx'
import styles from './NotFound.module.css'

function NotFound() {
  const navigate = useNavigate()

  return (
    <main className={styles.page}>
      <div className={styles.content}>
        <p className={styles.code} aria-hidden="true">
          404
        </p>
        <h1 className={styles.message}>This page doesn&apos;t exist.</h1>

        <div className={styles.buttonWrap}>
          <Button type="button" onClick={() => navigate('/home')}>
            Back to home
          </Button>
        </div>
      </div>
    </main>
  )
}

export default NotFound
