import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Nav from '../components/Nav'
import { useAuth } from '../context/AuthContext'
import {
  fetchSpecs,
  fetchIssuers,
  addSpec,
  type SpecEntry,
  type SpecFilters,
} from '../api/specs'
import { fetchProcesses } from '../api/queue'

type Tab = 'view' | 'add'

export default function SpecsPage() {
  const [tab, setTab] = useState<Tab>('view')

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ padding: 24 }}>
        <h1 style={{ margin: '0 0 16px' }}>Specifications</h1>

        <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #e0e0e0' }}>
          {(['view', 'add'] as Tab[]).map((t) => (
            <button
              key={t}
              onClick={() => setTab(t)}
              style={{
                border: 'none',
                borderBottom: tab === t ? '2px solid #1a73e8' : '2px solid transparent',
                borderRadius: 0,
                background: 'transparent',
                padding: '8px 16px',
                fontWeight: tab === t ? 600 : 400,
                color: tab === t ? '#1a73e8' : '#444',
                marginBottom: -2,
                cursor: 'pointer',
              }}
            >
              {t === 'view' ? 'View Specifications' : 'Add Specification'}
            </button>
          ))}
        </div>

        {tab === 'view' && <ViewTab />}
        {tab === 'add' && <AddTab onSuccess={() => setTab('view')} />}
      </div>
    </div>
  )
}

// ─── View tab ─────────────────────────────────────────────────────────────────

function ViewTab() {
  const [processFilter, setProcessFilter] = useState('')
  const [issuerFilter, setIssuerFilter] = useState('')
  const [search, setSearch] = useState('')

  const { data: processes = [] } = useQuery({
    queryKey: ['processes'],
    queryFn: fetchProcesses,
  })

  const { data: issuers = [] } = useQuery({
    queryKey: ['issuers'],
    queryFn: fetchIssuers,
  })

  const activeFilters: SpecFilters = {
    process: processFilter || undefined,
    issuer: issuerFilter || undefined,
    search: search || undefined,
  }

  const { data: specs = [], isLoading, isError } = useQuery({
    queryKey: ['specs', activeFilters],
    queryFn: () => fetchSpecs(activeFilters),
  })

  // Compute stats from all specs (no filters) for the summary row
  const { data: allSpecs = [] } = useQuery({
    queryKey: ['specs', {}],
    queryFn: () => fetchSpecs({}),
  })

  const totalProcesses = new Set(allSpecs.map((s) => s.process)).size
  const totalIssuers = new Set(allSpecs.filter((s) => s.issuer).map((s) => s.issuer)).size

  function handleExport() {
    const header = 'process,spec,issuer,notes'
    const rows = specs.map((s) =>
      [s.process, s.spec, s.issuer, s.notes]
        .map((v) => `"${(v ?? '').replace(/"/g, '""')}"`)
        .join(',')
    )
    const csv = [header, ...rows].join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'familiar_specs_export.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div>
      {/* Stats */}
      <div style={{ display: 'flex', gap: 20, marginBottom: 20 }}>
        {[
          { label: 'Total Specifications', value: allSpecs.length },
          { label: 'Total Processes', value: totalProcesses },
          { label: 'Total Issuers', value: totalIssuers },
        ].map(({ label, value }) => (
          <div
            key={label}
            style={{ background: '#f8f9fa', border: '1px solid #e0e0e0', borderRadius: 6, padding: '12px 20px', minWidth: 160 }}
          >
            <div style={{ fontSize: 24, fontWeight: 700 }}>{value}</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr auto', gap: 12, marginBottom: 16, alignItems: 'end' }}>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>Process</label>
          <select value={processFilter} onChange={(e) => setProcessFilter(e.target.value)}>
            <option value="">All processes</option>
            {processes.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>Issuer</label>
          <select value={issuerFilter} onChange={(e) => setIssuerFilter(e.target.value)}>
            <option value="">All issuers</option>
            {issuers.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>Search</label>
          <input
            placeholder="Keyword search…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <button onClick={handleExport} disabled={specs.length === 0} style={{ whiteSpace: 'nowrap' }}>
          Export CSV
        </button>
      </div>

      {isLoading && <p style={{ color: '#666' }}>Loading…</p>}
      {isError && <p style={{ color: '#d93025' }}>Could not load specifications. Is the API running?</p>}

      {!isLoading && !isError && (
        <>
          <p style={{ color: '#666', margin: '0 0 8px', fontSize: 13 }}>
            {specs.length} specification{specs.length !== 1 ? 's' : ''}
            {(processFilter || issuerFilter || search) ? ' matching filters' : ''}
          </p>
          <table>
            <thead>
              <tr>
                <th>Process</th>
                <th>Specification</th>
                <th>Issuer</th>
                <th>Notes</th>
              </tr>
            </thead>
            <tbody>
              {specs.length === 0 ? (
                <tr>
                  <td colSpan={4} style={{ textAlign: 'center', padding: 32, color: '#666' }}>
                    No specifications match the selected filters.
                  </td>
                </tr>
              ) : (
                specs.map((s: SpecEntry, i: number) => (
                  <tr key={`${s.process}-${s.spec}-${i}`}>
                    <td>
                      <span style={{ background: '#f1f3f4', padding: '2px 8px', borderRadius: 12, fontSize: 13 }}>
                        {s.process}
                      </span>
                    </td>
                    <td><strong>{s.spec}</strong></td>
                    <td style={{ color: '#666', fontSize: 13 }}>{s.issuer}</td>
                    <td style={{ color: '#666', fontSize: 13 }}>{s.notes}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </>
      )}
    </div>
  )
}

// ─── Add tab ──────────────────────────────────────────────────────────────────

function AddTab({ onSuccess }: { onSuccess: () => void }) {
  const { user } = useAuth()
  const queryClient = useQueryClient()

  const { data: processes = [] } = useQuery({
    queryKey: ['processes'],
    queryFn: fetchProcesses,
  })

  const { data: issuers = [] } = useQuery({
    queryKey: ['issuers'],
    queryFn: fetchIssuers,
  })

  const [processSelect, setProcessSelect] = useState('')
  const [newProcess, setNewProcess] = useState('')
  const [issuerSelect, setIssuerSelect] = useState('')
  const [newIssuer, setNewIssuer] = useState('')
  const [spec, setSpec] = useState('')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  const addMutation = useMutation({
    mutationFn: addSpec,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['specs'] })
      queryClient.invalidateQueries({ queryKey: ['processes'] })
      queryClient.invalidateQueries({ queryKey: ['issuers'] })
      onSuccess()
    },
    onError: (err: unknown) => {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ??
        'Failed to add specification.'
      setError(msg)
    },
  })

  if (user?.role !== 'admin') {
    return (
      <div style={{ background: '#fff8e1', border: '1px solid #ffe082', borderRadius: 6, padding: 16, maxWidth: 480 }}>
        Admin privileges are required to add new specifications.
      </div>
    )
  }

  const addingNewProcess = processSelect === '__new__'
  const addingNewIssuer = issuerSelect === '__new__'
  const resolvedProcess = addingNewProcess ? newProcess.trim() : processSelect
  const resolvedIssuer = addingNewIssuer ? newIssuer.trim() : issuerSelect

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    if (!resolvedProcess || !spec.trim()) {
      setError('Process and Specification are required.')
      return
    }
    addMutation.mutate({
      process: resolvedProcess,
      spec: spec.trim(),
      issuer: resolvedIssuer,
      notes: notes.trim(),
    })
  }

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 560 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
        {/* Process */}
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>
            Process <span style={{ color: '#d93025' }}>*</span>
          </label>
          <select
            value={processSelect}
            onChange={(e) => { setProcessSelect(e.target.value); setNewProcess('') }}
          >
            <option value="">Select process…</option>
            {processes.map((p) => <option key={p} value={p}>{p}</option>)}
            <option value="__new__">+ Add New Process</option>
          </select>
          {addingNewProcess && (
            <input
              style={{ marginTop: 8 }}
              placeholder="New process name"
              value={newProcess}
              onChange={(e) => setNewProcess(e.target.value)}
              autoFocus
            />
          )}
        </div>

        {/* Issuer */}
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>
            Issuer
          </label>
          <select
            value={issuerSelect}
            onChange={(e) => { setIssuerSelect(e.target.value); setNewIssuer('') }}
          >
            <option value="">Select issuer…</option>
            {issuers.map((i) => <option key={i} value={i}>{i}</option>)}
            <option value="__new__">+ Add New Issuer</option>
          </select>
          {addingNewIssuer && (
            <input
              style={{ marginTop: 8 }}
              placeholder="New issuer name (e.g. SAE, ASTM)"
              value={newIssuer}
              onChange={(e) => setNewIssuer(e.target.value)}
              autoFocus
            />
          )}
        </div>

        {/* Spec */}
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>
            Specification <span style={{ color: '#d93025' }}>*</span>
          </label>
          <input
            placeholder="e.g. AMS2759"
            value={spec}
            onChange={(e) => setSpec(e.target.value)}
          />
        </div>

        {/* Notes */}
        <div>
          <label style={{ display: 'block', fontSize: 12, color: '#666', marginBottom: 4 }}>
            Notes
          </label>
          <textarea
            placeholder="Additional information…"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            rows={3}
            style={{ width: '100%', resize: 'vertical' }}
          />
        </div>
      </div>

      {error && (
        <p style={{ color: '#d93025', margin: '12px 0 0', fontSize: 13 }}>{error}</p>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button
          type="submit"
          className="primary"
          disabled={addMutation.isPending}
        >
          {addMutation.isPending ? 'Adding…' : 'Add Specification'}
        </button>
      </div>
    </form>
  )
}
