export function isRequired(value) {
  if (value == null) return false
  if (typeof value === 'string') return value.trim().length > 0
  if (typeof value === 'number') return !Number.isNaN(value)
  if (typeof File !== 'undefined' && value instanceof File) {
    return value.size > 0
  }
  return Boolean(value)
}

export function isValidEmail(value) {
  if (!isRequired(value) || typeof value !== 'string') return false
  const email = value.trim()
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export function isValidPhone(value) {
  if (!isRequired(value) || typeof value !== 'string') return false
  const trimmed = value.trim()
  if (!/^\+?[\d\s().-]+$/.test(trimmed)) return false
  const digits = trimmed.replace(/\D/g, '')
  return digits.length >= 7 && digits.length <= 15
}

export function isValidAge(value) {
  if (value === '' || value == null) return false
  const age = typeof value === 'number' ? value : Number(String(value).trim())
  return Number.isFinite(age) && age >= 1 && age <= 120
}

export function passwordsMatch(password, confirmPassword) {
  if (!isRequired(password) || !isRequired(confirmPassword)) return false
  return password === confirmPassword
}

export function validateRegisterForm(formData) {
  const data = formData ?? {}
  const errors = {}

  if (!isRequired(data.fullName)) {
    errors.fullName = 'Full name is required.'
  }

  if (!isRequired(data.username)) {
    errors.username = 'Username is required.'
  }

  if (!isValidAge(data.age)) {
    errors.age = 'Enter a valid age between 1 and 120.'
  }

  if (!isValidPhone(data.contactNo)) {
    errors.contactNo =
      'Enter a valid phone number (7–15 digits, optional country code).'
  }

  if (!isValidEmail(data.email)) {
    errors.email = 'Enter a valid email address.'
  }

  if (!isRequired(data.visualImpairmentType)) {
    errors.visualImpairmentType = 'Visual impairment type is required.'
  }

  if (!isRequired(data.assistancePreference)) {
    errors.assistancePreference = 'Assistance preference is required.'
  }

  if (!isRequired(data.emergencyContactName)) {
    errors.emergencyContactName = 'Emergency contact name is required.'
  }

  if (!isValidPhone(data.emergencyContactNo)) {
    errors.emergencyContactNo =
      'Enter a valid emergency contact number (7–15 digits, optional country code).'
  }

  if (!isRequired(data.password)) {
    errors.password = 'Password is required.'
  }

  if (!isRequired(data.confirmPassword)) {
    errors.confirmPassword = 'Please confirm your password.'
  } else if (!passwordsMatch(data.password, data.confirmPassword)) {
    errors.confirmPassword = 'Passwords do not match.'
  }

  const file = data.certificateFile
  const hasCertificate =
    typeof File !== 'undefined' && file instanceof File && file.size > 0
  if (!hasCertificate) {
    errors.certificateFile = 'Disability certificate file is required.'
  }

  return {
    isValid: Object.keys(errors).length === 0,
    errors,
  }
}
