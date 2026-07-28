const AUTH_DELAY_MS = 500

function delay(ms) {
  return new Promise((resolve) => {
    setTimeout(resolve, ms)
  })
}

function normalizeError(error, fallbackMessage) {
  if (error instanceof Error) {
    return error
  }
  return new Error(fallbackMessage)
}

function buildStubUser({ email, username, fullName, ...profile }) {
  return {
    id: `user_${Date.now()}`,
    email,
    username: username ?? email?.split('@')[0] ?? 'user',
    fullName: fullName ?? username ?? 'AI-EYE User',
    token: `stub_token_${Date.now()}`,
    ...profile,
  }
}

export async function loginUser(email, password) {
  try {
    if (!email?.trim() || !password) {
      throw new Error('Email and password are required.')
    }

    // replace with real fetch/axios call
    await delay(AUTH_DELAY_MS)

    return buildStubUser({
      email: email.trim(),
      username: email.trim().split('@')[0],
      fullName: email.trim().split('@')[0],
    })
  } catch (error) {
    throw normalizeError(error, 'Login failed. Please try again.')
  }
}

export async function registerUser(formData) {
  try {
    const {
      fullName,
      username,
      age,
      gender,
      contactNo,
      email,
      address,
      visualImpairmentType,
      assistancePreference,
      preferredLanguage,
      emergencyContactName,
      emergencyContactNo,
      certificateFile,
      password,
    } = formData ?? {}

    if (!email?.trim() || !password) {
      throw new Error('Email and password are required.')
    }
    if (!fullName?.trim() || !username?.trim()) {
      throw new Error('Full name and username are required.')
    }

    // replace with real fetch/axios call
    await delay(AUTH_DELAY_MS)

    return buildStubUser({
      fullName: fullName.trim(),
      username: username.trim(),
      email: email.trim(),
      age,
      gender,
      contactNo,
      address,
      visualImpairmentType,
      assistancePreference,
      preferredLanguage,
      emergencyContactName,
      emergencyContactNo,
      hasCertificate: Boolean(certificateFile),
    })
  } catch (error) {
    throw normalizeError(error, 'Registration failed. Please try again.')
  }
}
