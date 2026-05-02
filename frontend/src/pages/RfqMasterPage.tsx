import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Nav from '../components/Nav'
import { useAuth } from '../context/AuthContext'
import {
  fetchMaster,
  updateEntry,
  deleteEntry,
  STATUSES,
  type MasterEntry,
  type MasterUpdate,
} from '../api/rfqMaster'

const STATUS_COLORS: Record<string, { bg: string; color: string }> = {
  pending:   { bg: '#fff8e1', color: '#e37400' },
  received:  { bg: '#e6f4ea', color: '#137333' },
  awarded:   { bg: '#e8f0fe', color: '#1a73e8' },
  declined:  { bg: '#fce8e6', color: '#d93025' },
  cancelled: { bg: '#f1f3f4', color: '#666' },
}

function StatusBadge({ value }: { value: string }) {
  const s = STATUS_COLORS[(value ?? '').toLowerCase()] ?? { bg: '#f1f3f4', color: '#444' }
  return (
    <span style={{ background: s.bg, color: s.color, padding: '2px 10px', borderRadius: 12, fontSize: 12, fontWeight: 600 }}>
      {value || '—'}
    </span>
  )
}

export default function RfqMasterPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [statusFilter, setStatusFilter] = useState('')
  const [search, setSearch] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<MasterUpdate>({})

  const { data: entries = [], isLoading, isError } = useQuery({
    queryKey: ['rfq-master', { statusFilter, search }],
    queryFn: () => fetchMaster({ status: statusFilter || undefined, search: search || undefined }),
  })

  const updateMutation = useMutation({
    mutationFn: ({ rfqId, body }: { rfqId: string; body: MasterUpdate }) => updateEntry(rfqId, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rfq-master'] })
      setEditingId(null)
      setEditDraft({})
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteEntry,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['rfq-master'] }),
  })

  // Stats from full unfiltered data
  const { data: allEntries = [] } = useQuery({
    queryKey: ['rfq-master', {}],
    queryFn: () => fetchMaster({}),
  })
  const statCounts = STATUSES.reduce((acc, s) => {
    acc[s] = allEntries.filter((e) => (e.status ?? '').toLowerCase() === s).length
    return acc
  }, {} as Record<string, number>)

  function handleExport() {
    const header = 'rfq#,qt/so #,part_number,vendor,vendor_contact,status,sent,received,notes,rfq_folder'
    const rows = entries.map((e) =>
      [e.rfq_id, e.qt_so, e.part_number, e.vendor, e.vendor_contact, e.status, e.sent, e.received, e.notes, e.rfq_folder]
        .map((v) => `"${(v ?? '').replace(/"/g, '""')}"`)
        .join(',')
    )
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'rfq_master_export.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  function startEdit(entry: MasterEntry) {
    setEditingId(entry.rfq_id)
    setEditDraft({ status: entry.status, received: entry.received, notes: entry.notes })
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ padding: 24 }}>
        <h1 style={{ margin: '0 0 16px' }}>RFQ Master</h1>

        {/* Stats row */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
          <div style={{ background: '#f8f9fa', border: '1px solid #e0e0e0', borderRadius: 6, padding: '10px 18px', minWidth: 120 }}>
            <div style={{ fontSize: 22, fontWeight: 700 }}>{allEntries.length}</div>
            <div style={{ fontSize: 12, color: '#666' }}>Total RFQs</div>
          </div>
          {STATUSES.map((s) => {
            const c = STATUS_COLORS[s] ?? { bg: '#f1f3f4', color: '#444' }
            return (
              <div
                key={s}
                onClick={() => setStatusFilter(statusFilter === s ? '' : s)}
                style={{
                  background: statusFilter === s ? c.bg : '#f8f9fa',
                  border: `1px solid ${statusFilter === s ? c.color : '#e0e0e0'}`,
                  borderRadius: 6,
                  padding: '10px 18px',
                  minWidth: 100,
                  cursor: 'pointer',
                }}
              >
                <div style={{ fontSize: 22, fontWeight: 700, color: statusFilter === s ? c.color : 'inherit' }}>
                  {statCounts[s] ?? 0}
                </div>
                <div style={{ fontSize: 12, color: '#666', textTransform: 'capitalize' }}>{s}</div>
              </div>
            )
          })}
        </div>

        {/* Filters */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, alignItems: 'center', flexWrap: 'wrap' }}>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} style={{ minWidth: 160 }}>
            <option value="">All statuses</option>
            {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <input
            placeholder="Search part, vendor, RFQ#…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: 260 }}
          />
          <button onClick={handleExport} disabled={entries.length === 0}>Export CSV</button>
        </div>

        {isLoading && <p style={{ color: '#666' }}>Loading…</p>}
        {isError && <p style={{ color: '#d93025' }}>Could not load RFQ master. Is the API running?</p>}

        {!isLoading && !isError && (
          <>
            <p style={{ color: '#666', fontSize: 13, margin: '0 0 8px' }}>
              {entries.length} entr{entries.length !== 1 ? 'ies' : 'y'}
              {(statusFilter || search) ? ' matching filters' : ''}
            </p>
            <table>
              <thead>
                <tr>
                  <th>RFQ #</th>
                  <th>QT/SO #</th>
                  <th>Part</th>
                  <th>Vendor</th>
                  <th>Contact</th>
                  <th>Status</th>
                  <th>Sent</th>
                  <th>Received</th>
                  <th>Notes</th>
                  <th>Files</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {entries.length === 0 ? (
                  <tr>
                    <td colSpan={11} style={{ textAlign: 'center', padding: 32, color: '#666' }}>
                      No entries match the selected filters.
                    </td>
                  </tr>
                ) : (
                  entries.map((entry) => (
                    editingId === entry.rfq_id
                      ? (
                        <tr key={entry.rfq_id} style={{ background: '#f8f9fa' }}>
                          <td><strong>{entry.rfq_id}</strong></td>
                          <td>{entry.qt_so}</td>
                          <td>{entry.part_number}</td>
                          <td>{entry.vendor}</td>
                          <td style={{ fontSize: 12 }}>{entry.vendor_contact}</td>
                          <td>
                            <select
                              value={editDraft.status ?? ''}
                              onChange={(e) => setEditDraft((d) => ({ ...d, status: e.target.value }))}
                              style={{ fontSize: 12 }}
                            >
                              {STATUSES.map((s) => <option key={s} value={s}>{s}</option>)}
                            </select>
                          </td>
                          <td style={{ fontSize: 12 }}>{entry.sent}</td>
                          <td>
                            <input
                              value={editDraft.received ?? ''}
                              onChange={(e) => setEditDraft((d) => ({ ...d, received: e.target.value }))}
                              placeholder="date received"
                              style={{ fontSize: 12, width: 110 }}
                            />
                          </td>
                          <td>
                            <input
                              value={editDraft.notes ?? ''}
                              onChange={(e) => setEditDraft((d) => ({ ...d, notes: e.target.value }))}
                              placeholder="notes"
                              style={{ fontSize: 12, width: 140 }}
                            />
                          </td>
                          <td></td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <button
                              className="primary"
                              style={{ fontSize: 12, padding: '3px 10px', marginRight: 4 }}
                              disabled={updateMutation.isPending}
                              onClick={() => updateMutation.mutate({ rfqId: entry.rfq_id, body: editDraft })}
                            >
                              Save
                            </button>
                            <button
                              style={{ fontSize: 12, padding: '3px 10px' }}
                              onClick={() => { setEditingId(null); setEditDraft({}) }}
                            >
                              Cancel
                            </button>
                          </td>
                        </tr>
                      ) : (
                        <tr key={entry.rfq_id}>
                          <td><strong>{entry.rfq_id}</strong></td>
                          <td>{entry.qt_so}</td>
                          <td>{entry.part_number}</td>
                          <td>{entry.vendor}</td>
                          <td style={{ fontSize: 12, color: '#666' }}>{entry.vendor_contact}</td>
                          <td><StatusBadge value={entry.status} /></td>
                          <td style={{ fontSize: 12, color: '#666' }}>{entry.sent}</td>
                          <td style={{ fontSize: 12, color: '#666' }}>{entry.received}</td>
                          <td style={{ fontSize: 12, color: '#666', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {entry.notes}
                          </td>
                          <td>
                            {entry.rfq_folder && (
                              <a href={entry.rfq_folder} target="_blank" rel="noreferrer" style={{ fontSize: 12 }}>
                                Box
                              </a>
                            )}
                          </td>
                          <td style={{ whiteSpace: 'nowrap' }}>
                            <button
                              style={{ fontSize: 12, padding: '3px 10px', marginRight: 4 }}
                              onClick={() => startEdit(entry)}
                            >
                              Edit
                            </button>
                            {user?.role === 'admin' && (
                              <button
                                className="danger"
                                style={{ fontSize: 12, padding: '3px 10px' }}
                                disabled={deleteMutation.isPending}
                                onClick={() => {
                                  if (confirm(`Delete RFQ "${entry.rfq_id}"?`)) {
                                    deleteMutation.mutate(entry.rfq_id)
                                  }
                                }}
                              >
                                Del
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                  ))
                )}
              </tbody>
            </table>
          </>
        )}
      </div>
    </div>
  )
}
