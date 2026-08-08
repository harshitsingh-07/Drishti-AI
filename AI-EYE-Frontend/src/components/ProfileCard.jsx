import styles from './ProfileCard.module.css'

export function ProfileCard({ label, value }) {
  return (
    <section className={styles.field} aria-label={label}>
      <p className={styles.label}>{label}</p>
      <p className={styles.value}>{value}</p>
    </section>
  )
}

export function ProfileSection({ title, children }) {
  return (
    <section className={styles.section}>
      <h2 className={styles.title}>{title}</h2>
      {children}
    </section>
  )
}
