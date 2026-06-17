import client from './client'

export interface QueueItem {
  part_number: string
  process: string
  spec: string
  material?: string
  quantities?: string
  due_date?: string
  qt_so_number?: string
  cui_itar?: boolean
  rev?: string
  notes?: string
  sent?: string
  submitted_by?: string
}

// Omit<> is a TypeScript utility that creates a new type by removing fields.
// When creating a new item, the server fills in sent and submitted_by —
// the user doesn't supply them. This prevents the form from even having those fields.
export type QueueItemCreate = Omit<QueueItem, 'sent' | 'submitted_by'>

export async function fetchQueue(): Promise<QueueItem[]> {
  const { data } = await client.get<QueueItem[]>('/queue/')
  return data
}

export async function addQueueItem(item: QueueItemCreate): Promise<QueueItem> {
  const { data } = await client.post<QueueItem>('/queue/', item)
  return data
}

export async function removeQueueItem(partNumber: string): Promise<void> {
  await client.delete(`/queue/${encodeURIComponent(partNumber)}`)
}

export interface QueueItemUpdate {
  current_process: string
  spec?: string
  material?: string
  quantities?: string
  qt_so_number?: string
  cui_itar?: string
  rev?: string
  notes?: string
  due_date?: string
  file_location?: string
}

export async function updateQueueItem(partNumber: string, body: QueueItemUpdate): Promise<QueueItem> {
  const { data } = await client.patch<QueueItem>(`/queue/${encodeURIComponent(partNumber)}`, body)
  return data
}

export async function fetchProcesses(): Promise<string[]> {
  const { data } = await client.get<string[]>('/specs/processes')
  return data
}

export async function fetchSpecsForProcess(process: string): Promise<string[]> {
  const { data } = await client.get<string[]>(`/specs/processes/${encodeURIComponent(process)}/specs`)
  return data
}
