import { useState, useEffect } from 'react'
import { updateQueueItem } from '../api/queue'
import type { SendQueueItem } from '../api/sendRfq'

interface Props {
  item: SendQueueItem | null
  onClose: () => void
  onSaved: () => void
}

const isCuiValue = (v: string) =>
  ['true', 'yes', 'y', '1', 'cui', 'itar', 'cui/itar'].includes(v.toLowerCase().trim())

export default function QueueEditSidebar({ item, onClose, onSaved }: Props) {
  const [form, setForm] = useState({
    spec: '', material: '', quantities: '', qt_so_number: '',
    cui_itar: false, rev: '', notes: '', due_date: '', file_location: '',
  })
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!item) return
    setForm({
      spec: item.spec || '',
      material: item.material || '',
      quantities: item.quantities || '',
      qt_so_number: item.qt_so_number || '',
      cui_itar: isCuiValue(item.cui_itar || ''),
      rev: item.rev || '',
      notes: item.notes || '',
      due_date: item.due_date || '',
      file_location: item.file_location || '',
    })
    setError('')
  }, [item])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  if (!item) return null

  async function handleSave() {
    if (!item) return
    setSaving(true)
    setError('')
    try {
      await updateQueueItem(item.part_number, {
        current_process: item.process,
        spec: form.spec || undefined,
        material: form.material || undefined,
        quantities: form.quantities || undefined,
        qt_so_number: form.qt_so_number || undefined,
        cui_itar: form.cui_itar ? 'TRUE' : 'FALSE',
        rev: form.rev || undefined,
        notes: form.notes || undefined,
        due_date: form.due_date || undefined,
        file_location: form.file_location || undefined,
      })
      onSaved()
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const set = (field: string, value: string | boolean) =>
    setForm(prev => ({ ...prev, [field]: value }))

  return (
    <>
      {/* Backdrop */}
      <div
        onClick={onClose}
        style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.25)', zIndex: 200,
        }}
      />
      {/* Drawer */}
      <div style={{
        position: 'fixed', top: 0, right: 0, bottom: 0, width: 380,
        background: '#fff', boxShadow: '-4px 0 24px rgba(0,0,0,0.12)',
        zIndex: 201, display: 'flex', flexDirection: 'column',
      }}>
        {/* Header */}
        <div style={{
          padding: '16px 20px', borderBottom: '1px solid #e0e0e0',
          display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>{item.part_number}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
              {item.process} · {item.spec}
            </div>
          </div>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#666', padding: 0 }}
          >
            ✕
          </button>
        </div>

        {/* Fields */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: 14 }}>
          <Field label="Spec">
            <input value={form.spec} onChange={e => set('spec', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Material">
            <input value={form.material} onChange={e => set('material', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Quantities">
            <input value={form.quantities} onChange={e => set('quantities', e.target.value)} style={inputStyle} placeholder="e.g. 1,5,10,25" />
          </Field>
          <Field label="QT/SO #">
            <input value={form.qt_so_number} onChange={e => set('qt_so_number', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Rev">
            <input value={form.rev} onChange={e => set('rev', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Due Date">
            <input type="date" value={form.due_date} onChange={e => set('due_date', e.target.value)} style={inputStyle} />
          </Field>
          <Field label="Notes">
            <textarea
              value={form.notes}
              onChange={e => set('notes', e.target.value)}
              rows={3}
              style={{ ...inputStyle, resize: 'vertical' }}
            />
          </Field>
          <Field label="File Location">
            <input value={form.file_location} onChange={e => set('file_location', e.target.value)} style={inputStyle} placeholder="\\server\path\to\files" />
          </Field>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={form.cui_itar}
              onChange={e => set('cui_itar', e.target.checked)}
            />
            CUI / ITAR controlled
          </label>
        </div>

        {/* Footer */}
        <div style={{ padding: '12px 20px', borderTop: '1px solid #e0e0e0' }}>
          {error && <div style={{ color: '#d93025', fontSize: 12, marginBottom: 8 }}>{error}</div>}
          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={onClose} style={{ flex: 1, padding: '8px 0' }}>Cancel</button>
            <button
              className="primary"
              onClick={handleSave}
              disabled={saving}
              style={{ flex: 2, padding: '8px 0' }}
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ display: 'block', fontSize: 11, fontWeight: 600, color: '#555', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.5px' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

const inputStyle: React.CSSProperties = {
  width: '100%', boxSizing: 'border-box', fontSize: 13,
  padding: '6px 8px', border: '1px solid #ccc', borderRadius: 4,
}
