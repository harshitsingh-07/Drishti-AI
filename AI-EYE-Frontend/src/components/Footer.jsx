import styles from './Footer.module.css'

function Footer() {
  const currentYear = new Date().getFullYear()

  return (
    <footer className={styles.footer}>
      <p className={styles.text}>
        &copy; {currentYear} AI-EYE. Built for accessible navigation.
      </p>
    </footer>
  )
}

export default Footer
