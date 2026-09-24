import client from './client'

// TypeScript interfaces define the shape of data.
// These mirror the Pydantic models in api/routers/auth.py.
// If the API response doesn't match this shape, TypeScript will warn you
// at compile time — catching mismatches before they become runtime bugs.

// Mirrors _ROLE_RANK in api/deps.py — keep the two in sync.
//   viewer: read only · buyer/engineer: + Box, drafts, RFQ Master edits
//   estimator: + queue add/edit, vendor approvals · admin: + deletes, specs
export type Role = 'viewer' | 'buyer' | 'engineer' | 'estimator' | 'admin'

const ROLE_RANK: Record<Role, number> = { viewer: 0, buyer: 1, engineer: 1, estimator: 2, admin: 3 }

export interface User {
  email: string
  name: string
  role: Role
}

/** True if the user's role is at least `minimum` (unknown roles count as viewer). */
export function hasRole(user: User | null | undefined, minimum: Role): boolean {
  const rank = ROLE_RANK[(user?.role ?? 'viewer') as Role] ?? 0
  return rank >= ROLE_RANK[minimum]
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
