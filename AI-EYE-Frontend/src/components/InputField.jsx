import styles from './InputField.module.css'

function InputField({
  id,
  label,
  type = 'text',
  value,
  onChange,
  required = false,
  helpText,
  error,
  className,
  ...rest
}) {
  const helpId = helpText ? `${id}-help` : undefined
  const errorId = error ? `${id}-error` : undefined
  const describedBy =
    [helpId, errorId].filter(Boolean).join(' ') || undefined

  return (
    <div className={styles.field}>
      <label htmlFor={id} className={styles.label}>
        {label}
        {required ? (
          <span className={styles.required} aria-hidden="true">
            {' '}
            *
          </span>
        ) : null}
      </label>
      <input
        id={id}
        type={type}
        value={value}
        onChange={onChange}
        required={required}
        aria-required={required || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={[styles.input, error && styles.inputError, className]
          .filter(Boolean)
          .join(' ')}
        {...rest}
      />
      {helpText ? (
        <p id={helpId} className={styles.helpText}>
          {helpText}
        </p>
      ) : null}
      {error ? (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

export default InputField
