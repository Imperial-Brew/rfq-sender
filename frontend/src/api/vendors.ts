import client from './client'

export interface Contact {
  name: string
  first_name: string
  last_name: string
  email: string
  phone: string
  primary: boolean
  state: string
  website: string
}

export interface VendorSummary {
  name: string
  processes: string[]
  active: boolean
  rating: number
  primary_contact: Contact | null
}

export interface VendorDetail extends VendorSummary {
  id: string
  notes: string
  address: Record<string, string>
  contacts: Contact[]
  // { "Anodize": ["AMS 2468", ...] }
  approvals: Record<string, string[]>
}

export async function fetchVendors(): Promise<VendorSummary[]> {
  const { data } = await client.get<VendorSummary[]>('/vendors/')
  return data
}

export async function fetchVendor(name: string): Promise<VendorDetail> {
  const { data } = await client.get<VendorDetail>(`/vendors/${encodeURIComponent(name)}`)
  return data
}

export async function searchVendorsBySpec(
  process: string,
  spec?: string,
): Promise<VendorSummary[]> {
  const params: Record<string, string> = { process }
  if (spec) params.spec = spec
  const { data } = await client.get<VendorSummary[]>('/vendors/search', { params })
  return data
}

export async function addVendorApproval(
  vendorName: string,
  process: string,
  spec: string,
): Promise<Record<string, string[]>> {
  const { data } = await client.post<Record<string, string[]>>(
    `/vendors/${encodeURIComponent(vendorName)}/approvals`,
    { process, spec },
  )
  return data
}
