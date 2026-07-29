import axios from 'axios'

const API_BASE_URL = 'http://localhost:5000/api'

function normalizeError(error, fallbackMessage) {
  if (error instanceof Error) {
    return error
  }
  return new Error(fallbackMessage)
}

function buildUser(data) {
  return {
    id: data.id,
    email: data.email,
    username: data.username,
    fullName: data.fullName,
    token: data.token,
  }
}

export async function loginUser(email, password) {
  try {
    if (!email?.trim() || !password) {
      throw new Error('Email and password are required.')
    }

    const response = await axios.post(`${API_BASE_URL}/auth/login`, { email, password })
    return buildUser(response.data)
  } catch (error) {
    const message = error?.response?.data?.message || 'Login failed. Please try again.'
    throw normalizeError(new Error(message), 'Login failed. Please try again.')
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

    const response = await axios.post(`${API_BASE_URL}/auth/register`, {
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
      certificateFile,
      password,
    })

    return buildUser(response.data)
  } catch (error) {
    const message = error?.response?.data?.message || 'Registration failed. Please try again.'
    throw normalizeError(new Error(message), 'Registration failed. Please try again.')
  }
}

export async function detectObjects(imageBase64) {
  const response = await axios.post(`${API_BASE_URL}/detect`, { image: imageBase64 })
  return response.data
}
