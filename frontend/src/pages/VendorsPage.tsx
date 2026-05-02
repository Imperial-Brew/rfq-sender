/**
 * Vendors page — two tabs:
 *   "Directory"    — search the vendor list, click one to see detail
 *   "Find by Spec" — pick process + spec, see which vendors are approved
 *
 * New TanStack Query pattern introduced here: "dependent queries."
 * The vendor detail query only runs when a vendor has been selected
 * (enabled: !!selectedVendor). Same idea as the spec dropdown in AddToQueueForm
 * — don't fetch until you have the input you need.
 */

import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import Nav from '../components/Nav'
import {
  fetchVendors,
  fetchVendor,
  searchVendorsBySpec,
  type VendorSummary,
  type VendorDetail,
  type Contact,
} from '../api/vendors'
import { fetchProcesses, fetchSpecsForProcess } from '../api/queue'

type Tab = 'directory' | 'find-by-spec'
type DetailTab = 'contacts' | 'processes' | 'approvals'

export default function VendorsPage() {
  const [tab, setTab] = useState<Tab>('directory')

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ padding: 24 }}>
        <h1 style={{ margin: '0 0 16px' }}>Vendors</h1>

        {/* Tab switcher */}
        <div style={{ display: 'flex', gap: 4, marginBottom: 20, borderBottom: '2px solid #e0e0e0' }}>
          {(['directory', 'find-by-spec'] as Tab[]).map((t) => (
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
              }}
            >
              {t === 'directory' ? 'Vendor Directory' : 'Find by Spec'}
            </button>
          ))}
        </div>

        {tab === 'directory' && <DirectoryTab />}
        {tab === 'find-by-spec' && <FindBySpecTab />}
      </div>
    </div>
  )
}

// ─── Directory tab ────────────────────────────────────────────────────────────

function DirectoryTab() {
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<string | null>(null)

  const { data: vendors = [], isLoading } = useQuery({
    queryKey: ['vendors'],
    queryFn: fetchVendors,
  })

  // Only fetches when a vendor is selected — avoids loading all detail upfront
  const { data: detail, isLoading: detailLoading } = useQuery({
    queryKey: ['vendor', selected],
    queryFn: () => fetchVendor(selected!),
    enabled: !!selected,
  })

  const filtered = vendors.filter((v) =>
    v.name.toLowerCase().includes(search.toLowerCase()) ||
    v.processes.some((p) => p.toLowerCase().includes(search.toLowerCase()))
  )

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr', gap: 20 }}>
      {/* Left: vendor list */}
      <div>
        <input
          placeholder="Search vendors or processes…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ marginBottom: 12 }}
        />
        {isLoading && <p style={{ color: '#666', fontSize: 13 }}>Loading…</p>}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {filtered.map((v) => (
            <button
              key={v.name}
              onClick={() => setSelected(v.name)}
              style={{
                textAlign: 'left',
                padding: '8px 10px',
                border: '1px solid',
                borderColor: selected === v.name ? '#1a73e8' : '#e0e0e0',
                borderRadius: 4,
                background: selected === v.name ? '#e8f0fe' : '#fff',
                color: v.active ? '#1a1a1a' : '#999',
                fontSize: 13,
              }}
            >
              <div style={{ fontWeight: 500 }}>{v.name}</div>
              <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                {v.processes.slice(0, 3).join(' · ')}
                {v.processes.length > 3 && ` +${v.processes.length - 3}`}
              </div>
            </button>
          ))}
          {!isLoading && filtered.length === 0 && (
            <p style={{ color: '#666', fontSize: 13 }}>No vendors match.</p>
          )}
        </div>
      </div>

      {/* Right: detail panel */}
      <div>
        {!selected && (
          <div style={{ color: '#666', paddingTop: 40, textAlign: 'center' }}>
            Select a vendor to view details.
          </div>
        )}
        {selected && detailLoading && <p>Loading…</p>}
        {selected && detail && <VendorDetailPanel detail={detail} />}
      </div>
    </div>
  )
}

function VendorDetailPanel({ detail }: { detail: VendorDetail }) {
  const [tab, setTab] = useState<DetailTab>('contacts')

  const tabStyle = (t: DetailTab) => ({
    border: 'none',
    borderBottom: tab === t ? '2px solid #1a73e8' : '2px solid transparent',
    borderRadius: 0,
    background: 'transparent',
    padding: '6px 14px',
    fontWeight: tab === t ? 600 : 400,
    color: tab === t ? '#1a73e8' : '#444',
    marginBottom: -2,
    fontSize: 13,
    cursor: 'pointer',
  })

  const address = Object.values(detail.address).filter(Boolean).join(', ')

  return (
    <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 6, padding: 20 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ margin: '0 0 4px' }}>{detail.name}</h2>
          {address && <p style={{ margin: '0 0 4px', color: '#666', fontSize: 13 }}>{address}</p>}
          {!detail.active && <span style={{ fontSize: 12, color: '#d93025' }}>Inactive</span>}
        </div>
        {detail.rating > 0 && (
          <span style={{ fontSize: 13, color: '#e37400' }}>
            {'★'.repeat(detail.rating)}{'☆'.repeat(5 - detail.rating)}
          </span>
        )}
      </div>

      <div style={{ display: 'flex', gap: 4, margin: '16px 0 0', borderBottom: '2px solid #e0e0e0' }}>
        <button style={tabStyle('contacts')} onClick={() => setTab('contacts')}>Contacts</button>
        <button style={tabStyle('processes')} onClick={() => setTab('processes')}>Processes</button>
        <button style={tabStyle('approvals')} onClick={() => setTab('approvals')}>Approved Specs</button>
      </div>

      <div style={{ paddingTop: 16 }}>
        {tab === 'contacts' && <ContactsTab contacts={detail.contacts} />}
        {tab === 'processes' && <ProcessesTab processes={detail.processes} />}
        {tab === 'approvals' && <ApprovalsTab approvals={detail.approvals} />}
      </div>
    </div>
  )
}

function ContactsTab({ contacts }: { contacts: Contact[] }) {
  if (contacts.length === 0) return <p style={{ color: '#666' }}>No contacts on file.</p>
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 12 }}>
      {contacts.map((c, i) => (
        <div key={i} style={{ border: '1px solid #e0e0e0', borderRadius: 6, padding: 12 }}>
          <div style={{ fontWeight: 600, marginBottom: 4 }}>
            {c.name || `${c.first_name} ${c.last_name}`.trim()}
            {c.primary && (
              <span style={{ marginLeft: 6, fontSize: 11, background: '#e8f0fe', color: '#1a73e8', padding: '1px 6px', borderRadius: 10 }}>
                Primary
              </span>
            )}
          </div>
          {c.email && <div style={{ fontSize: 13 }}><a href={`mailto:${c.email}`}>{c.email}</a></div>}
          {c.phone && <div style={{ fontSize: 13, color: '#666' }}>{c.phone}</div>}
          {c.state && <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>{c.state}</div>}
        </div>
      ))}
    </div>
  )
}

function ProcessesTab({ processes }: { processes: string[] }) {
  if (processes.length === 0) return <p style={{ color: '#666' }}>No processes listed.</p>
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
      {processes.map((p) => (
        <span key={p} style={{ background: '#f1f3f4', padding: '4px 10px', borderRadius: 14, fontSize: 13 }}>
          {p}
        </span>
      ))}
    </div>
  )
}

function ApprovalsTab({ approvals }: { approvals: Record<string, string[]> }) {
  const processes = Object.keys(approvals).sort()
  if (processes.length === 0) return <p style={{ color: '#666' }}>No approved specs on file.</p>
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {processes.map((process) => (
        <div key={process}>
          <div style={{ fontWeight: 600, marginBottom: 6 }}>{process}</div>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
            {approvals[process].map((spec) => (
              <span key={spec} style={{ background: '#e6f4ea', color: '#137333', padding: '3px 10px', borderRadius: 12, fontSize: 12 }}>
                {spec}
              </span>
            ))}
            {approvals[process].length === 0 && (
              <span style={{ color: '#999', fontSize: 13 }}>None listed</span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

// ─── Find by Spec tab ─────────────────────────────────────────────────────────

function FindBySpecTab() {
  const [selectedProcess, setSelectedProcess] = useState('')
  const [selectedSpec, setSelectedSpec] = useState('')

  const { data: processes = [] } = useQuery({
    queryKey: ['processes'],
    queryFn: fetchProcesses,
  })

  const { data: specs = [] } = useQuery({
    queryKey: ['specs', selectedProcess],
    queryFn: () => fetchSpecsForProcess(selectedProcess),
    enabled: !!selectedProcess,
  })

  // Only searches when both process and spec are chosen
  const { data: results, isLoading: searching, isFetching } = useQuery({
    queryKey: ['vendors-by-spec', selectedProcess, selectedSpec],
    queryFn: () => searchVendorsBySpec(selectedProcess, selectedSpec),
    enabled: !!selectedProcess && !!selectedSpec,
  })

  return (
    <div style={{ maxWidth: 700 }}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>
        <div>
          <label>Process</label>
          <select
            value={selectedProcess}
            onChange={(e) => { setSelectedProcess(e.target.value); setSelectedSpec('') }}
          >
            <option value="">Select process…</option>
            {processes.map((p) => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label>Specification</label>
          <select
            value={selectedSpec}
            onChange={(e) => setSelectedSpec(e.target.value)}
            disabled={!selectedProcess}
          >
            <option value="">{selectedProcess ? 'Select spec…' : 'Choose process first'}</option>
            {specs.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>

      {/* Results auto-appear once both dropdowns are set — no Search button needed */}
      {(searching || isFetching) && <p style={{ color: '#666' }}>Searching…</p>}

      {results && !isFetching && (
        <>
          <p style={{ color: '#666', marginBottom: 12 }}>
            {results.length === 0
              ? `No vendors approved for ${selectedSpec} (${selectedProcess}).`
              : `${results.length} vendor${results.length !== 1 ? 's' : ''} approved for ${selectedSpec}`}
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {results.map((v: VendorSummary) => (
              <div key={v.name} style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 6, padding: 14 }}>
                <div style={{ fontWeight: 600, marginBottom: 6 }}>{v.name}</div>
                {v.primary_contact && (
                  <div style={{ fontSize: 13, color: '#444' }}>
                    {v.primary_contact.name && <span>{v.primary_contact.name} · </span>}
                    {v.primary_contact.email && <a href={`mailto:${v.primary_contact.email}`}>{v.primary_contact.email}</a>}
                    {v.primary_contact.phone && <span> · {v.primary_contact.phone}</span>}
                  </div>
                )}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
