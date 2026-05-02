import client from './client'

export interface SpecEntry {
  process: string
  spec: string
  issuer: string
  notes: string
}

export interface SpecCreate {
  process: string
  spec: string
  issuer?: string
  notes?: string
}

export interface SpecFilters {
  process?: string
  issuer?: string
  search?: string
}

export async function fetchSpecs(filters: SpecFilters = {}): Promise<SpecEntry[]> {
  const params = new URLSearchParams()
  if (filters.process) params.set('process', filters.process)
  if (filters.issuer) params.set('issuer', filters.issuer)
  if (filters.search) params.set('search', filters.search)
  const { data } = await client.get<SpecEntry[]>(`/specs/?${params.toString()}`)
  return data
}

export async function fetchIssuers(): Promise<string[]> {
  const { data } = await client.get<string[]>('/specs/issuers')
  return data
}

export async function addSpec(body: SpecCreate): Promise<SpecEntry> {
  const { data } = await client.post<SpecEntry>('/specs/', body)
  return data
}
