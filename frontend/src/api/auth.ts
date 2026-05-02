import client from './client'

// TypeScript interfaces define the shape of data.
// These mirror the Pydantic models in api/routers/auth.py.
// If the API response doesn't match this shape, TypeScript will warn you
// at compile time — catching mismatches before they become runtime bugs.

export interface User {
  email: string
  name: string
  role: 'admin' | 'estimator' | 'viewer'
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const { data } = await client.post<LoginResponse>('/auth/login', { email, password })
  return data
}
