import styles from './Loader.module.css'

function Loader({ label = 'Loading' }) {
  return (
    <div className={styles.wrapper} role="status" aria-live="polite">
      <span className={styles.visuallyHidden}>{label}</span>
      <div className={styles.spinner} aria-hidden="true" />
    </div>
  )
}

export default Loader
