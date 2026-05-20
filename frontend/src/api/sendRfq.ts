import client from './client'

export interface SendQueueItem {
  part_number: string
  process: string
  spec: string
  material: string
  quantities: string
  qt_so_number: string
  cui_itar: string
  rev: string
  notes: string
  file_location: string
  sent: string
  box_share_link: string
  box_password: string
}

export interface VendorMatch {
  name: string
  contact_name: string
  contact_email: string
}

export interface BoxResult {
  share_link: string
  password: string
  is_cui: boolean
  files_uploaded: number
  error?: string
}

export interface EmailResult {
  vendor: string
  contact_email: string
  success: boolean
  error?: string
}

export async function fetchUnsentQueue(): Promise<SendQueueItem[]> {
  const { data } = await client.get<SendQueueItem[]>('/send-rfq/queue')
  return Array.isArray(data) ? data : []
}

export async function fetchVendors(process: string, spec: string): Promise<VendorMatch[]> {
  const p = new URLSearchParams({ process })
  if (spec) p.set('spec', spec)
  const { data } = await client.get<VendorMatch[]>(`/send-rfq/vendors?${p.toString()}`)
  return Array.isArray(data) ? data : []
}

export async function createBoxFolder(
  partNumber: string,
  access = 'open',
): Promise<BoxResult> {
  const { data } = await client.post<BoxResult>(
    `/send-rfq/box/${encodeURIComponent(partNumber)}`,
    { access },
  )
  return data
}

export async function createEmailDrafts(
  partNumber: string,
  shareLink: string,
  password: string,
): Promise<EmailResult[]> {
  const { data } = await client.post<EmailResult[]>(
    `/send-rfq/email/${encodeURIComponent(partNumber)}`,
    { share_link: shareLink, password },
  )
  return Array.isArray(data) ? data : []
}
