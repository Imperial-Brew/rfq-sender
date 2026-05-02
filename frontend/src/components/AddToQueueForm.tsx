/**
 * Add-to-queue form.
 *
 * Two TanStack Query concepts used here:
 *
 *   useQuery — fetches data and caches it. The spec dropdown uses two:
 *     one for processes, one for specs (which re-fetches whenever the
 *     selected process changes via the `enabled` and `queryKey` options).
 *
 *   useMutation — for write operations (POST, PUT, DELETE). Unlike useQuery
 *     it doesn't run automatically — you call mutation.mutate(data) manually.
 *     It tracks isPending, isError, and calls onSuccess when done.
 */

import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import {
  fetchProcesses,
  fetchSpecsForProcess,
  addQueueItem,
  type QueueItemCreate,
} from '../api/queue'

interface Props {
  onSuccess: () => void
}

const EMPTY: Partial<QueueItemCreate> = { cui_itar: false }

export default function AddToQueueForm({ onSuccess }: Props) {
  const [form, setForm] = useState<Partial<QueueItemCreate>>(EMPTY)

  // Fetch processes from the API — same data that drives Streamlit's selectbox
  const { data: processes = [] } = useQuery({
    queryKey: ['processes'],
    queryFn: fetchProcesses,
  })

  // Fetch specs for the selected process. The `enabled` option means
  // "don't run this query until a process has been selected."
  // The queryKey includes the process name — TQ re-fetches automatically
  // whenever the key changes (i.e., whenever the user picks a different process).
  const { data: specs = [] } = useQuery({
    queryKey: ['specs', form.process],
    queryFn: () => fetchSpecsForProcess(form.process!),
    enabled: !!form.process,
  })

  const mutation = useMutation({
    mutationFn: addQueueItem,
    onSuccess,
  })

  function set<K extends keyof QueueItemCreate>(field: K, value: QueueItemCreate[K]) {
    setForm((f) => ({ ...f, [field]: value }))
    // Clear spec when process changes — old spec won't be valid for new process
    if (field === 'process') {
      setForm((f) => ({ ...f, process: value as string, spec: '' }))
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!form.part_number || !form.process || !form.spec) return
    mutation.mutate(form as QueueItemCreate)
  }

  const fieldStyle = { display: 'flex', flexDirection: 'column' as const, gap: 4 }

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        background: '#fff',
        border: '1px solid #e0e0e0',
        borderRadius: 6,
        padding: 20,
        marginTop: 16,
      }}
    >
      <h3 style={{ marginTop: 0 }}>Add Part to Queue</h3>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 16, marginBottom: 16 }}>
        <div style={fieldStyle}>
          <label>Part Number *</label>
          <input
            value={form.part_number ?? ''}
            onChange={(e) => set('part_number', e.target.value)}
            placeholder="e.g. 12345-001"
            required
          />
        </div>

        <div style={fieldStyle}>
          <label>Process *</label>
          <select
            value={form.process ?? ''}
            onChange={(e) => set('process', e.target.value)}
            required
          >
            <option value="">Select process…</option>
            {processes.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>

        <div style={fieldStyle}>
          <label>Spec *</label>
          {/* Spec dropdown is disabled until a process is chosen */}
          <select
            value={form.spec ?? ''}
            onChange={(e) => set('spec', e.target.value)}
            required
            disabled={!form.process}
          >
            <option value="">
              {form.process ? 'Select spec…' : 'Choose process first'}
            </option>
            {specs.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div style={fieldStyle}>
          <label>Material</label>
          <input
            value={form.material ?? ''}
            onChange={(e) => set('material', e.target.value)}
            placeholder="e.g. 6061-T6 Aluminum"
          />
        </div>

        <div style={fieldStyle}>
          <label>Quantities</label>
          <input
            value={form.quantities ?? ''}
            onChange={(e) => set('quantities', e.target.value)}
            placeholder="e.g. 10, 25, 50"
          />
        </div>

        <div style={fieldStyle}>
          <label>Due Date</label>
          <input
            type="date"
            value={form.due_date ?? ''}
            onChange={(e) => set('due_date', e.target.value)}
          />
        </div>

        <div style={fieldStyle}>
          <label>QT / SO #</label>
          <input
            value={form.qt_so_number ?? ''}
            onChange={(e) => set('qt_so_number', e.target.value)}
          />
        </div>

        <div style={fieldStyle}>
          <label>Rev</label>
          <input
            value={form.rev ?? ''}
            onChange={(e) => set('rev', e.target.value)}
            style={{ maxWidth: 80 }}
          />
        </div>

        <div style={{ ...fieldStyle, justifyContent: 'flex-end' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 500 }}>
            <input
              type="checkbox"
              style={{ width: 'auto' }}
              checked={!!form.cui_itar}
              onChange={(e) => set('cui_itar', e.target.checked)}
            />
            CUI / ITAR
          </label>
        </div>
      </div>

      <div style={fieldStyle}>
        <label>Notes</label>
        <input
          value={form.notes ?? ''}
          onChange={(e) => set('notes', e.target.value)}
        />
      </div>

      {mutation.isError && (
        <p style={{ color: '#d93025', marginTop: 12 }}>
          Failed to add item. Check that the API is running.
        </p>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button type="submit" className="primary" disabled={mutation.isPending}>
          {mutation.isPending ? 'Adding…' : 'Add to Queue'}
        </button>
      </div>
    </form>
  )
}
