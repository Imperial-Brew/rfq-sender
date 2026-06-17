import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Nav from '../components/Nav'
import BoxUploadModal from '../components/BoxUploadModal'
import QueueEditSidebar from '../components/QueueEditSidebar'
import AddToQueueForm from '../components/AddToQueueForm'
import { useAuth } from '../context/AuthContext'
import { removeQueueItem } from '../api/queue'
import {
  fetchUnsentQueue,
  fetchVendors,
  createBoxFolder,
  saveBoxLink,
  createEmailDrafts,
  type SendQueueItem,
  type VendorMatch,
  type BoxResult,
  type EmailResult,
} from '../api/sendRfq'

// ── State types ──────────────────────────────────────────────────────────────

interface PartState {
  expanded: boolean
  boxLoading: boolean
  boxResult: BoxResult | null
  boxLink: string
  boxPassword: string
  showPwd: boolean
  saveLinkLoading: boolean
  saveLinkStatus: 'idle' | 'saved' | 'error'
  draftAllLoading: boolean
}

interface ProcState {
  vendorsLoading: boolean
  vendors: VendorMatch[] | null
  emailLoading: boolean
  emailResults: EmailResult[] | null
}

// ── Key helpers ──────────────────────────────────────────────────────────────

function partKey(item: SendQueueItem): string {
  return `${item.part_number}|${item.qt_so_number || ''}`
}

function procKey(item: SendQueueItem): string {
  return `${partKey(item)}|${item.process}`
}

function defaultPartState(items: SendQueueItem[]): PartState {
  const first = items[0]
  return {
    expanded: false,
    boxLoading: false,
    boxResult: null,
    boxLink: first?.box_share_link || '',
    boxPassword: first?.box_password || '',
    showPwd: false,
    saveLinkLoading: false,
    saveLinkStatus: 'idle',
    draftAllLoading: false,
  }
}

const defaultProcState = (): ProcState => ({
  vendorsLoading: false, vendors: null, emailLoading: false, emailResults: null,
})

// ── CUI badge ─────────────────────────────────────────────────────────────────

const CUI_VALUES = ['true', 'yes', 'y', '1', 'cui', 'itar', 'cui/itar']

function CuiBadge({ value }: { value: string }) {
  if (!CUI_VALUES.includes((value || '').toLowerCase().trim())) return null
  return (
    <span style={{ background: '#fce8e6', color: '#C82022', padding: '1px 7px', borderRadius: 10, fontSize: 11, fontWeight: 700 }}>
      CUI
    </span>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function SendRfqsPage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const isAdmin = user?.role === 'admin'
  const canEdit = user?.role === 'admin' || user?.role === 'estimator'

  const [showSent, setShowSent] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [partStates, setPartStates] = useState<Record<string, PartState>>({})
  const [procStates, setProcStates] = useState<Record<string, ProcState>>({})
  const [boxModalGroup, setBoxModalGroup] = useState<{ key: string; items: SendQueueItem[] } | null>(null)
  const [editItem, setEditItem] = useState<SendQueueItem | null>(null)

  const { data: items = [], isLoading, isError } = useQuery({
    queryKey: ['send-rfq-queue', showSent],
    queryFn: () => fetchUnsentQueue(showSent),
  })

  const deleteMutation = useMutation({
    mutationFn: removeQueueItem,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
      queryClient.invalidateQueries({ queryKey: ['queue'] })
    },
  })

  // Group by part_number + qt_so_number
  const groups = useMemo(() => {
    const map = new Map<string, { key: string; items: SendQueueItem[] }>()
    for (const item of items) {
      const k = partKey(item)
      if (!map.has(k)) map.set(k, { key: k, items: [] })
      map.get(k)!.items.push(item)
    }
    return Array.from(map.values())
  }, [items])

  // ── State helpers ──────────────────────────────────────────────────────────

  function getPart(key: string, groupItems: SendQueueItem[]): PartState {
    return partStates[key] ?? defaultPartState(groupItems)
  }

  function setPart(key: string, patch: Partial<PartState>) {
    setPartStates(prev => ({ ...prev, [key]: { ...(prev[key] ?? defaultPartState([])), ...patch } }))
  }

  function getProc(item: SendQueueItem): ProcState {
    return procStates[procKey(item)] ?? defaultProcState()
  }

  function setProc(item: SendQueueItem, patch: Partial<ProcState>) {
    const k = procKey(item)
    setProcStates(prev => ({ ...prev, [k]: { ...(prev[k] ?? defaultProcState()), ...patch } }))
  }

  // ── Handlers ──────────────────────────────────────────────────────────────

  function handleToggle(key: string, groupItems: SendQueueItem[]) {
    setPart(key, { expanded: !getPart(key, groupItems).expanded })
  }

  async function handlePreviewVendors(item: SendQueueItem) {
    setProc(item, { vendorsLoading: true, vendors: null })
    try {
      const v = await fetchVendors(item.process, item.spec)
      setProc(item, { vendorsLoading: false, vendors: v })
    } catch {
      setProc(item, { vendorsLoading: false, vendors: [] })
    }
  }

  async function handleSaveLink(key: string, groupItems: SendQueueItem[]) {
    const part = getPart(key, groupItems)
    setPart(key, { saveLinkLoading: true, saveLinkStatus: 'idle' })
    try {
      for (const item of groupItems) {
        await saveBoxLink(item.part_number, part.boxLink, part.boxPassword, item.process)
      }
      setPart(key, { saveLinkLoading: false, saveLinkStatus: 'saved' })
      setTimeout(() => setPart(key, { saveLinkStatus: 'idle' }), 3000)
    } catch (e: unknown) {
      setPart(key, { saveLinkLoading: false, saveLinkStatus: 'error' })
      alert(`Save failed: ${e instanceof Error ? e.message : e}`)
    }
  }

  async function handleBoxConfirm(files: File[]) {
    const group = boxModalGroup
    setBoxModalGroup(null)
    if (!group) return
    const { key, items: groupItems } = group
    setPart(key, { boxLoading: true, boxResult: null })
    try {
      const result = await createBoxFolder(groupItems[0].part_number, files, 'open')
      setPart(key, {
        boxLoading: false,
        boxResult: result,
        boxLink: result.share_link || getPart(key, groupItems).boxLink,
        boxPassword: result.password || '',
      })
      if (result.share_link) queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setPart(key, { boxLoading: false, boxResult: { share_link: '', password: '', is_cui: false, files_uploaded: 0, error: msg } })
    }
  }

  async function handleDraftProcess(item: SendQueueItem, part: PartState) {
    setProc(item, { emailLoading: true, emailResults: null })
    try {
      const results = await createEmailDrafts(item.part_number, part.boxLink, part.boxPassword, item.process)
      setProc(item, { emailLoading: false, emailResults: results })
      if (results.some(r => r.success)) queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setProc(item, { emailLoading: false, emailResults: [{ vendor: '—', contact_email: '', success: false, error: msg }] })
    }
  }

  async function handleDraftAll(key: string, groupItems: SendQueueItem[]) {
    const part = getPart(key, groupItems)
    const allSent = groupItems.every(i => !!i.sent)
    // Re-draft All: send all processes. Draft All: send only unsent.
    const toSend = allSent ? groupItems : groupItems.filter(i => !i.sent)
    setPart(key, { expanded: true, draftAllLoading: true })
    for (const item of toSend) {
      await handleDraftProcess(item, part)
    }
    setPart(key, { draftAllLoading: false })
    queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
  }

  function handleDelete(partNumber: string) {
    if (!confirm(`Remove all queue entries for "${partNumber}"?`)) return
    deleteMutation.mutate(partNumber)
  }

  // ── Render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ flex: 1, padding: '24px 32px', maxWidth: 1100, margin: '0 auto', width: '100%' }}>

        {/* Toolbar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
          <h2 style={{ margin: 0, fontSize: 20 }}>
            RFQ Queue
            {groups.length > 0 && (
              <span style={{ fontSize: 13, fontWeight: 400, color: '#666', marginLeft: 10 }}>
                {groups.length} part{groups.length !== 1 ? 's' : ''}
              </span>
            )}
          </h2>
          {canEdit && (
            <button
              className={showAddForm ? '' : 'primary'}
              onClick={() => setShowAddForm(v => !v)}
              style={{ fontSize: 13, padding: '5px 14px' }}
            >
              {showAddForm ? '✕ Cancel' : '+ Add Part'}
            </button>
          )}
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, marginLeft: 'auto', cursor: 'pointer' }}>
            <input type="checkbox" checked={showSent} onChange={e => setShowSent(e.target.checked)} />
            Show sent
          </label>
        </div>

        {/* Add form */}
        {showAddForm && (
          <div style={{ marginBottom: 20 }}>
            <AddToQueueForm onSuccess={() => {
              setShowAddForm(false)
              queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
              queryClient.invalidateQueries({ queryKey: ['queue'] })
            }} />
          </div>
        )}

        {isLoading && <div style={{ color: '#666', fontSize: 13 }}>Loading…</div>}
        {isError && <div style={{ color: '#d93025', fontSize: 13 }}>Failed to load queue.</div>}
        {!isLoading && groups.length === 0 && (
          <div style={{ color: '#888', fontSize: 13 }}>
            {showSent ? 'No items in queue.' : 'No unsent items — check "Show sent" to see history, or add a part above.'}
          </div>
        )}

        {/* Part groups */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {groups.map(({ key, items: groupItems }) => {
            const part = getPart(key, groupItems)
            const allSent = groupItems.every(i => !!i.sent)
            const unsentCount = groupItems.filter(i => !i.sent).length
            const anyProcLoading = groupItems.some(i => getProc(i).emailLoading)
            const rep = groupItems[0]

            return (
              <div key={key} style={{ border: '1px solid #e0e0e0', borderRadius: 8, overflow: 'hidden', background: '#fff' }}>

                {/* ── Part header ── */}
                <div style={{
                  display: 'grid',
                  gridTemplateColumns: 'auto 1fr auto auto auto auto auto',
                  alignItems: 'center',
                  gap: 10,
                  padding: '10px 14px',
                  background: part.expanded ? '#f8f9fa' : '#fff',
                  borderBottom: part.expanded ? '1px solid #e8e8e8' : 'none',
                }}>

                  <button
                    onClick={() => handleToggle(key, groupItems)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: '#555', padding: '2px 4px' }}
                    title={part.expanded ? 'Collapse' : 'Expand processes'}
                  >
                    {part.expanded ? '▼' : '▶'}
                  </button>

                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                      <strong style={{ fontSize: 14 }}>{rep.part_number}</strong>
                      {rep.qt_so_number && <span style={{ fontSize: 12, color: '#666' }}>QT {rep.qt_so_number}</span>}
                      <CuiBadge value={rep.cui_itar} />
                      {allSent && <span style={{ fontSize: 11, color: '#888' }}>all sent</span>}
                    </div>
                    <div style={{ fontSize: 11, color: '#999', marginTop: 2 }}>
                      {groupItems.map(i => i.process).join(' · ')}
                    </div>
                  </div>

                  {/* Box link */}
                  <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                    <input
                      value={part.boxLink}
                      onChange={e => setPart(key, { boxLink: e.target.value, saveLinkStatus: 'idle' })}
                      placeholder="Box folder link…"
                      style={{ fontSize: 12, width: 170, padding: '4px 6px', border: '1px solid #ccc', borderRadius: 4 }}
                    />
                    {part.saveLinkStatus === 'saved' && <span style={{ fontSize: 11, color: '#137333' }}>✓</span>}
                    {part.saveLinkStatus === 'error' && <span style={{ fontSize: 11, color: '#d93025' }}>✗</span>}
                  </div>

                  <button
                    onClick={() => handleSaveLink(key, groupItems)}
                    disabled={part.saveLinkLoading || !part.boxLink}
                    style={{ fontSize: 12, padding: '4px 10px' }}
                  >
                    {part.saveLinkLoading ? '…' : 'Save'}
                  </button>

                  <button
                    onClick={() => setBoxModalGroup({ key, items: groupItems })}
                    disabled={part.boxLoading}
                    style={{ fontSize: 12, padding: '4px 10px' }}
                  >
                    {part.boxLoading ? 'Creating…' : part.boxLink ? '↺ Box' : '+ Box'}
                  </button>

                  {/* Draft All / Re-draft All — never sends, always creates Outlook drafts */}
                  <button
                    className="primary"
                    onClick={() => handleDraftAll(key, groupItems)}
                    disabled={part.draftAllLoading || anyProcLoading}
                    style={{ fontSize: 12, padding: '4px 12px', whiteSpace: 'nowrap' }}
                    title="Creates Outlook drafts for review — does not send automatically"
                  >
                    {part.draftAllLoading
                      ? 'Drafting…'
                      : allSent
                        ? 'Re-draft All'
                        : `Draft All${unsentCount < groupItems.length ? ` (${unsentCount})` : ''}`}
                  </button>
                </div>

                {/* Password / error sub-row */}
                {(part.boxResult?.error || part.boxPassword) && (
                  <div style={{
                    padding: '4px 14px 4px 42px', fontSize: 11,
                    background: '#f8f9fa',
                    borderBottom: part.expanded ? '1px solid #e8e8e8' : 'none',
                    display: 'flex', alignItems: 'center', gap: 6,
                  }}>
                    {part.boxResult?.error && <span style={{ color: '#d93025' }}>Box error: {part.boxResult.error}</span>}
                    {part.boxPassword && !part.boxResult?.error && (
                      <>
                        <span style={{ color: '#666' }}>Box pwd:</span>
                        <code style={{ userSelect: 'all', letterSpacing: part.showPwd ? 0 : 2 }}>
                          {part.showPwd ? part.boxPassword : '••••••••••••••'}
                        </code>
                        <button
                          onClick={() => setPart(key, { showPwd: !part.showPwd })}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, padding: '0 2px', color: '#666' }}
                          title={part.showPwd ? 'Hide password' : 'Show password'}
                        >
                          {part.showPwd ? '🙈' : '👁'}
                        </button>
                      </>
                    )}
                  </div>
                )}

                {/* ── Process rows ── */}
                {part.expanded && groupItems.map(item => {
                  const proc = getProc(item)
                  const successCount = proc.emailResults?.filter(r => r.success).length ?? 0
                  const failCount = proc.emailResults?.filter(r => !r.success).length ?? 0

                  return (
                    <div key={procKey(item)}>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: '1fr auto auto auto auto',
                        alignItems: 'center',
                        gap: 10,
                        padding: '8px 14px 8px 40px',
                        borderTop: '1px solid #f0f0f0',
                        background: '#fafafa',
                      }}>
                        <div>
                          <span style={{ fontSize: 13, fontWeight: 500 }}>{item.process}</span>
                          {item.spec && <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>{item.spec}</span>}
                          {item.quantities && <span style={{ fontSize: 11, color: '#999', marginLeft: 8 }}>qty: {item.quantities}</span>}
                          {item.sent && <span style={{ fontSize: 11, color: '#888', marginLeft: 8 }}>· drafted {item.sent}</span>}
                        </div>

                        <button
                          style={{ fontSize: 12, padding: '3px 10px' }}
                          onClick={() => handlePreviewVendors(item)}
                          disabled={proc.vendorsLoading}
                        >
                          {proc.vendorsLoading ? '…' : proc.vendors !== null ? 'Vendors ▾' : 'Vendors'}
                        </button>

                        {/* "Draft" — creates an Outlook draft, never auto-sends */}
                        <button
                          className={item.sent ? '' : 'primary'}
                          style={{ fontSize: 12, padding: '3px 10px', whiteSpace: 'nowrap' }}
                          onClick={() => handleDraftProcess(item, getPart(key, groupItems))}
                          disabled={proc.emailLoading}
                          title="Creates an Outlook draft for your review — does not send automatically"
                        >
                          {proc.emailLoading ? 'Drafting…' : item.sent ? 'Re-draft' : 'Draft'}
                        </button>

                        <button
                          onClick={() => setEditItem(item)}
                          style={{ fontSize: 12, padding: '3px 8px', background: 'none', border: '1px solid #ccc', cursor: 'pointer', borderRadius: 4 }}
                          title="Edit queue row"
                        >✏</button>

                        {isAdmin && (
                          <button
                            onClick={() => handleDelete(item.part_number)}
                            disabled={deleteMutation.isPending}
                            style={{ fontSize: 12, padding: '3px 8px', background: 'none', border: '1px solid #f5c6c6', color: '#d93025', cursor: 'pointer', borderRadius: 4 }}
                            title="Remove from queue"
                          >✕</button>
                        )}
                      </div>

                      {proc.vendors !== null && (
                        <div style={{ padding: '6px 14px 6px 60px', background: '#f0f4ff', borderTop: '1px solid #e8e8e8' }}>
                          {proc.vendors.length === 0
                            ? <span style={{ fontSize: 12, color: '#d93025' }}>No matching vendors found.</span>
                            : (
                              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                                {proc.vendors.map(v => (
                                  <div key={v.name} style={{ fontSize: 12, background: '#fff', border: '1px solid #d0d7de', borderRadius: 6, padding: '3px 10px' }}>
                                    <strong>{v.name}</strong>
                                    {v.contact_name && <span style={{ color: '#666' }}> · {v.contact_name}</span>}
                                    {v.contact_email && <span style={{ color: '#1a73e8' }}> &lt;{v.contact_email}&gt;</span>}
                                  </div>
                                ))}
                              </div>
                            )}
                        </div>
                      )}

                      {proc.emailResults !== null && (
                        <div style={{
                          padding: '6px 14px 6px 60px',
                          background: failCount > 0 ? '#fff8e1' : '#e8f5e9',
                          borderTop: '1px solid #e8e8e8', fontSize: 12,
                        }}>
                          <strong>{successCount} Outlook draft{successCount !== 1 ? 's' : ''} created</strong>
                          {failCount > 0 && <span style={{ color: '#d93025', marginLeft: 8 }}>{failCount} failed</span>}
                          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 4 }}>
                            {proc.emailResults.map((r, i) => (
                              <span key={i} style={{
                                background: r.success ? '#c8e6c9' : '#ffcdd2',
                                color: r.success ? '#1b5e20' : '#b71c1c',
                                padding: '1px 8px', borderRadius: 10, fontSize: 11,
                              }}>
                                {r.vendor}{r.error ? ` — ${r.error}` : ''}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            )
          })}
        </div>
      </div>

      {boxModalGroup && (
        <BoxUploadModal
          partNumber={boxModalGroup.items[0].part_number}
          onConfirm={handleBoxConfirm}
          onCancel={() => setBoxModalGroup(null)}
        />
      )}

      <QueueEditSidebar
        item={editItem}
        onClose={() => setEditItem(null)}
        onSaved={() => {
          setEditItem(null)
          queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
          queryClient.invalidateQueries({ queryKey: ['queue'] })
        }}
      />
    </div>
  )
}
