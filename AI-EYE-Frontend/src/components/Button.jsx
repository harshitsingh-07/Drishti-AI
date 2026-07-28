import styles from './Button.module.css'

function Button({
  children,
  variant = 'primary',
  type = 'button',
  onClick,
  disabled = false,
  className,
  ...rest
}) {
  const variantClass =
    variant === 'secondary' ? styles.secondary : styles.primary

  return (
    <button
      type={type}
      className={[styles.button, variantClass, className]
        .filter(Boolean)
        .join(' ')}
      onClick={onClick}
      disabled={disabled}
      {...rest}
    >
      {children}
    </button>
  )
}

export default Button
