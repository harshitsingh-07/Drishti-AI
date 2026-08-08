import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import Button from '../components/Button.jsx'
import InputField from '../components/InputField.jsx'
import Loader from '../components/Loader.jsx'
import { useAuth } from '../context/AuthContext.jsx'
import { registerUser } from '../services/authService.js'
import { validateRegisterForm } from '../utils/validation.js'
import styles from './Register.module.css'

const GENDER_OPTIONS = [
  { value: 'Female', label: 'Female' },
  { value: 'Male', label: 'Male' },
  { value: 'Non-binary', label: 'Non-binary' },
  { value: 'Prefer not to say', label: 'Prefer not to say' },
]

const VISUAL_IMPAIRMENT_OPTIONS = [
  { value: 'Fully blind', label: 'Fully blind' },
  { value: 'Low vision', label: 'Low vision' },
  { value: 'Color blind', label: 'Color blind' },
  { value: 'Other', label: 'Other' },
]

const ASSISTANCE_OPTIONS = [
  { value: 'Voice only', label: 'Voice only' },
  { value: 'Haptic only', label: 'Haptic only' },
  { value: 'Voice and haptic', label: 'Voice and haptic' },
]

const INITIAL_FORM = {
  fullName: '',
  username: '',
  age: '',
  gender: '',
  contactNo: '',
  email: '',
  address: '',
  visualImpairmentType: '',
  assistancePreference: '',
  preferredLanguage: '',
  emergencyContactName: '',
  emergencyContactNo: '',
  password: '',
  confirmPassword: '',
}

function SelectField({
  id,
  label,
  value,
  onChange,
  options,
  required = false,
  error,
  disabled = false,
  placeholder = 'Select an option',
}) {
  const errorId = error ? `${id}-error` : undefined

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
      <select
        id={id}
        value={value}
        onChange={onChange}
        required={required}
        disabled={disabled}
        aria-required={required || undefined}
        aria-invalid={error ? true : undefined}
        aria-describedby={errorId}
        className={[styles.select, error ? styles.selectError : null]
          .filter(Boolean)
          .join(' ')}
      >
        <option value="">{placeholder}</option>
        {options.map(({ value: optionValue, label: optionLabel }) => (
          <option key={optionValue} value={optionValue}>
            {optionLabel}
          </option>
        ))}
      </select>
      {error ? (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

function CertificateUpload({ id, file, onChange, error, disabled }) {
  const errorId = error ? `${id}-error` : undefined
  const labelId = `${id}-label`

  return (
    <div className={styles.field}>
      <span id={labelId} className={styles.label}>
        Disability certificate
        <span className={styles.required} aria-hidden="true">
          {' '}
          *
        </span>
      </span>
      <label
        htmlFor={id}
        className={[styles.dropZone, error ? styles.dropZoneError : null]
          .filter(Boolean)
          .join(' ')}
      >
        <input
          id={id}
          type="file"
          accept=".pdf,.jpg,.jpeg,.png"
          required
          disabled={disabled}
          onChange={(event) => onChange(event.target.files?.[0] ?? null)}
          className={styles.visuallyHidden}
          aria-labelledby={labelId}
          aria-describedby={errorId}
          aria-invalid={error ? true : undefined}
        />
        {file
          ? `Selected: ${file.name}`
          : 'Choose a PDF or image file (.pdf, .jpg, .jpeg, .png)'}
      </label>
      {error ? (
        <p id={errorId} className={styles.error} role="alert">
          {error}
        </p>
      ) : null}
    </div>
  )
}

function Register() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [form, setForm] = useState(INITIAL_FORM)
  const [certificateFile, setCertificateFile] = useState(null)
  const [fieldErrors, setFieldErrors] = useState({})
  const [submitError, setSubmitError] = useState(null)
  const [loading, setLoading] = useState(false)

  const updateField = (name, value) => {
    setForm((current) => ({ ...current, [name]: value }))
    setFieldErrors((current) => {
      if (!current[name]) return current
      const next = { ...current }
      delete next[name]
      return next
    })
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    setSubmitError(null)

    const formData = { ...form, certificateFile }
    const { isValid, errors } = validateRegisterForm(formData)

    if (!isValid) {
      setFieldErrors(errors)
      return
    }

    setFieldErrors({})
    setLoading(true)

    try {
      const result = await registerUser(formData)
      login(result)
      navigate('/home')
    } catch (err) {
      setSubmitError(
        err instanceof Error
          ? err.message
          : 'Registration failed. Please try again.',
      )
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className={styles.page}>
      <div className={styles.formWrapper}>
        <h1 className={styles.title}>Create your AI-EYE account</h1>

        {submitError ? (
          <p className={styles.alert} role="alert">
            {submitError}
          </p>
        ) : null}

        <form className={styles.form} onSubmit={handleSubmit} noValidate>
          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Personal details</legend>

            <InputField
              id="register-fullName"
              label="Full name"
              value={form.fullName}
              onChange={(event) => updateField('fullName', event.target.value)}
              required
              autoComplete="name"
              disabled={loading}
              error={fieldErrors.fullName}
            />
            <InputField
              id="register-username"
              label="Username"
              value={form.username}
              onChange={(event) => updateField('username', event.target.value)}
              required
              autoComplete="username"
              disabled={loading}
              error={fieldErrors.username}
            />
            <InputField
              id="register-age"
              label="Age"
              type="number"
              value={form.age}
              onChange={(event) => updateField('age', event.target.value)}
              required
              min={1}
              max={120}
              inputMode="numeric"
              disabled={loading}
              error={fieldErrors.age}
            />
            <SelectField
              id="register-gender"
              label="Gender"
              value={form.gender}
              onChange={(event) => updateField('gender', event.target.value)}
              options={GENDER_OPTIONS}
              disabled={loading}
              placeholder="Select gender"
            />
            <InputField
              id="register-contactNo"
              label="Contact number"
              type="tel"
              value={form.contactNo}
              onChange={(event) => updateField('contactNo', event.target.value)}
              required
              autoComplete="tel"
              disabled={loading}
              error={fieldErrors.contactNo}
            />
            <InputField
              id="register-email"
              label="Email"
              type="email"
              value={form.email}
              onChange={(event) => updateField('email', event.target.value)}
              required
              autoComplete="email"
              disabled={loading}
              error={fieldErrors.email}
            />
            <InputField
              id="register-address"
              label="Address"
              value={form.address}
              onChange={(event) => updateField('address', event.target.value)}
              autoComplete="street-address"
              disabled={loading}
            />
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Accessibility details</legend>

            <SelectField
              id="register-visualImpairmentType"
              label="Visual impairment type"
              value={form.visualImpairmentType}
              onChange={(event) =>
                updateField('visualImpairmentType', event.target.value)
              }
              options={VISUAL_IMPAIRMENT_OPTIONS}
              required
              disabled={loading}
              error={fieldErrors.visualImpairmentType}
              placeholder="Select impairment type"
            />
            <SelectField
              id="register-assistancePreference"
              label="Assistance preference"
              value={form.assistancePreference}
              onChange={(event) =>
                updateField('assistancePreference', event.target.value)
              }
              options={ASSISTANCE_OPTIONS}
              required
              disabled={loading}
              error={fieldErrors.assistancePreference}
              placeholder="Select assistance preference"
            />
            <InputField
              id="register-preferredLanguage"
              label="Preferred language"
              value={form.preferredLanguage}
              onChange={(event) =>
                updateField('preferredLanguage', event.target.value)
              }
              autoComplete="language"
              disabled={loading}
            />
            <CertificateUpload
              id="register-certificate"
              file={certificateFile}
              onChange={(file) => {
                setCertificateFile(file)
                setFieldErrors((current) => {
                  if (!current.certificateFile) return current
                  const next = { ...current }
                  delete next.certificateFile
                  return next
                })
              }}
              error={fieldErrors.certificateFile}
              disabled={loading}
            />
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Emergency contact</legend>

            <InputField
              id="register-emergencyContactName"
              label="Emergency contact name"
              value={form.emergencyContactName}
              onChange={(event) =>
                updateField('emergencyContactName', event.target.value)
              }
              required
              autoComplete="name"
              disabled={loading}
              error={fieldErrors.emergencyContactName}
            />
            <InputField
              id="register-emergencyContactNo"
              label="Emergency contact number"
              type="tel"
              value={form.emergencyContactNo}
              onChange={(event) =>
                updateField('emergencyContactNo', event.target.value)
              }
              required
              autoComplete="tel"
              disabled={loading}
              error={fieldErrors.emergencyContactNo}
            />
          </fieldset>

          <fieldset className={styles.fieldset}>
            <legend className={styles.legend}>Account security</legend>

            <InputField
              id="register-password"
              label="Password"
              type="password"
              value={form.password}
              onChange={(event) => updateField('password', event.target.value)}
              required
              autoComplete="new-password"
              disabled={loading}
              error={fieldErrors.password}
            />
            <InputField
              id="register-confirmPassword"
              label="Confirm password"
              type="password"
              value={form.confirmPassword}
              onChange={(event) =>
                updateField('confirmPassword', event.target.value)
              }
              required
              autoComplete="new-password"
              disabled={loading}
              error={fieldErrors.confirmPassword}
            />
          </fieldset>

          {loading ? (
            <div className={styles.loaderWrap}>
              <Loader label="Creating account" />
            </div>
          ) : (
            <Button type="submit">Create account</Button>
          )}
        </form>

        <p className={styles.footerText}>
          Already have an account?{' '}
          <Link to="/" className={styles.footerLink}>
            Log in
          </Link>
        </p>
      </div>
    </main>
  )
}

export default Register
