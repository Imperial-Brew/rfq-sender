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

export async function fetchUnsentQueue(includeSent = false): Promise<SendQueueItem[]> {
  const url = includeSent ? '/send-rfq/queue?include_sent=true' : '/send-rfq/queue'
  const { data } = await client.get<SendQueueItem[]>(url)
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
  files: File[] = [],
  access = 'open',
  process?: string,
): Promise<BoxResult> {
  const form = new FormData()
  form.append('access', access)
  if (process) form.append('process', process)
  for (const f of files) form.append('files', f)
  const { data } = await client.post<BoxResult>(
    `/send-rfq/box/${encodeURIComponent(partNumber)}`,
    form,
    // Let axios set Content-Type with the correct boundary automatically
    { headers: { 'Content-Type': undefined } },
  )
  return data
}

export async function saveBoxLink(
  partNumber: string,
  shareLink: string,
  password: string,
  process?: string,
): Promise<BoxResult> {
  const { data } = await client.patch<BoxResult>(
    `/send-rfq/box-link/${encodeURIComponent(partNumber)}`,
    { share_link: shareLink, password, process },
  )
  return data
}

export async function createEmailDrafts(
  partNumber: string,
  shareLink: string,
  password: string,
  process?: string,
): Promise<EmailResult[]> {
  const { data } = await client.post<EmailResult[]>(
    `/send-rfq/email/${encodeURIComponent(partNumber)}`,
    { share_link: shareLink, password, process },
  )
  return Array.isArray(data) ? data : []
}
