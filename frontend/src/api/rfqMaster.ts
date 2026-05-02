import client from './client'

export interface MasterEntry {
  rfq_id: string
  qt_so: string
  part_number: string
  vendor: string
  vendor_contact: string
  rfq_folder: string
  status: string
  sent: string
  received: string
  notes: string
}

export interface MasterUpdate {
  status?: string
  received?: string
  notes?: string
}

export const STATUSES = ['pending', 'received', 'declined', 'awarded', 'cancelled']

export async function fetchMaster(params: { status?: string; search?: string } = {}): Promise<MasterEntry[]> {
  const p = new URLSearchParams()
  if (params.status) p.set('status', params.status)
  if (params.search) p.set('search', params.search)
  const { data } = await client.get<MasterEntry[]>(`/api/rfq-master/?${p.toString()}`)
  return Array.isArray(data) ? data : []
}

export async function updateEntry(rfqId: string, body: MasterUpdate): Promise<MasterEntry> {
  const { data } = await client.put<MasterEntry>(`/api/rfq-master/${encodeURIComponent(rfqId)}`, body)
  return data
}

export async function deleteEntry(rfqId: string): Promise<void> {
  await client.delete(`/api/rfq-master/${encodeURIComponent(rfqId)}`)
}
