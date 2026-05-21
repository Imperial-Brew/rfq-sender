import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import Nav from '../components/Nav'
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

// Per-row state tracking
interface RowState {
  // Box
  boxLoading: boolean
  boxResult: BoxResult | null
  boxLink: string        // editable override
  boxPassword: string
  saveLinkLoading: boolean
  saveLinkStatus: 'idle' | 'saved' | 'error'

  // Vendor preview
  vendorsLoading: boolean
  vendors: VendorMatch[] | null

  // Email
  emailLoading: boolean
  emailResults: EmailResult[] | null
}

function defaultRowState(item: SendQueueItem): RowState {
  return {
    boxLoading: false,
    boxResult: null,
    boxLink: item.box_share_link || '',
    boxPassword: item.box_password || '',
    saveLinkLoading: false,
    saveLinkStatus: 'idle',
    vendorsLoading: false,
    vendors: null,
    emailLoading: false,
    emailResults: null,
  }
}

function CuiBadge({ value }: { value: string }) {
  const isCui = ['true', 'yes', 'y', '1'].includes(value.toLowerCase())
  if (!isCui) return null
  return (
    <span style={{
      background: '#fce8e6', color: '#d93025',
      padding: '1px 7px', borderRadius: 10, fontSize: 11, fontWeight: 700,
    }}>
      CUI
    </span>
  )
}

function ResultPill({ success, label }: { success: boolean; label: string }) {
  return (
    <span style={{
      background: success ? '#e6f4ea' : '#fce8e6',
      color: success ? '#137333' : '#d93025',
      padding: '1px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
      marginRight: 3,
    }}>
      {label}
    </span>
  )
}

export default function SendRfqsPage() {
  const queryClient = useQueryClient()
  const [showSent, setShowSent] = useState(false)

  const { data: items = [], isLoading, isError, refetch } = useQuery({
    queryKey: ['send-rfq-queue', showSent],
    queryFn: () => fetchUnsentQueue(showSent),
  })

  // Per-row state keyed by part_number
  const [rows, setRows] = useState<Record<string, RowState>>({})

  function getRow(item: SendQueueItem): RowState {
    return rows[item.part_number] ?? defaultRowState(item)
  }

  function setRow(partNumber: string, patch: Partial<RowState>) {
    setRows(prev => ({
      ...prev,
      [partNumber]: { ...(prev[partNumber] ?? defaultRowState({ part_number: partNumber } as SendQueueItem)), ...patch },
    }))
  }

  async function handlePreviewVendors(item: SendQueueItem) {
    setRow(item.part_number, { vendorsLoading: true, vendors: null })
    try {
      const v = await fetchVendors(item.process, item.spec)
      setRow(item.part_number, { vendorsLoading: false, vendors: v })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setRow(item.part_number, { vendorsLoading: false, vendors: [] })
      alert(`Vendor lookup failed: ${msg}`)
    }
  }

  async function handleSaveLink(item: SendQueueItem) {
    const row = getRow(item)
    setRow(item.part_number, { saveLinkLoading: true, saveLinkStatus: 'idle' })
    try {
      await saveBoxLink(item.part_number, row.boxLink, row.boxPassword)
      setRow(item.part_number, { saveLinkLoading: false, saveLinkStatus: 'saved' })
      // Reset the "Saved ✓" badge after 3 seconds
      setTimeout(() => setRow(item.part_number, { saveLinkStatus: 'idle' }), 3000)
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setRow(item.part_number, { saveLinkLoading: false, saveLinkStatus: 'error' })
      alert(`Save failed: ${msg}`)
    }
  }

  async function handleCreateBox(item: SendQueueItem) {
    setRow(item.part_number, { boxLoading: true, boxResult: null })
    try {
      const result = await createBoxFolder(item.part_number)
      setRow(item.part_number, {
        boxLoading: false,
        boxResult: result,
        boxLink: result.share_link || getRow(item).boxLink,
        boxPassword: result.password || '',
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setRow(item.part_number, { boxLoading: false, boxResult: { share_link: '', password: '', is_cui: false, files_uploaded: 0, error: msg } })
    }
  }

  async function handleCreateEmails(item: SendQueueItem) {
    const row = getRow(item)
    setRow(item.part_number, { emailLoading: true, emailResults: null })
    try {
      const results = await createEmailDrafts(item.part_number, row.boxLink, row.boxPassword)
      setRow(item.part_number, { emailLoading: false, emailResults: results })
      // Refresh the queue — item will disappear from unsent view, or update sent date in "show sent" view
      if (results.some(r => r.success)) {
        queryClient.invalidateQueries({ queryKey: ['send-rfq-queue'] })
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e)
      setRow(item.part_number, { emailLoading: false, emailResults: [{ vendor: '—', contact_email: '', success: false, error: msg }] })
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
      <div style={{ padding: 24 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 16, marginBottom: 20 }}>
          <h1 style={{ margin: 0 }}>Send RFQs</h1>
          <span style={{ background: '#fff8e1', color: '#e37400', padding: '3px 12px', borderRadius: 12, fontSize: 13, fontWeight: 600 }}>
            {items.length} {showSent ? 'total' : 'unsent'}
          </span>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, cursor: 'pointer', userSelect: 'none' }}>
            <input
              type="checkbox"
              checked={showSent}
              onChange={(e) => setShowSent(e.target.checked)}
            />
            Show sent
          </label>
          <button onClick={() => refetch()} style={{ marginLeft: 'auto' }}>Refresh</button>
        </div>

        {isLoading && <p style={{ color: '#666' }}>Loading queue…</p>}
        {isError && <p style={{ color: '#d93025' }}>Could not load queue. Is the API running?</p>}

        {!isLoading && !isError && items.length === 0 && (
          <p style={{ color: '#666' }}>No unsent items in queue.</p>
        )}

        {!isLoading && !isError && items.length > 0 && (
          <table>
            <thead>
              <tr>
                <th>Part #</th>
                <th>Process / Spec</th>
                <th>QT/SO</th>
                <th>Qty</th>
                <th style={{ minWidth: 80 }}>Flags</th>
                <th style={{ minWidth: 220 }}>Box Folder Link</th>
                <th style={{ minWidth: 360 }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const row = getRow(item)
                return (
                  <ItemRow
                    key={item.part_number}
                    item={item}
                    row={row}
                    onPreviewVendors={() => handlePreviewVendors(item)}
                    onSaveLink={() => handleSaveLink(item)}
                    onCreateBox={() => handleCreateBox(item)}
                    onCreateEmails={() => handleCreateEmails(item)}
                    onBoxLinkChange={(v) => setRow(item.part_number, { boxLink: v, saveLinkStatus: 'idle' })}
                  />
                )
              })}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}

// Split into sub-component to keep JSX readable
interface ItemRowProps {
  item: SendQueueItem
  row: RowState
  onPreviewVendors: () => void
  onSaveLink: () => void
  onCreateBox: () => void
  onCreateEmails: () => void
  onBoxLinkChange: (v: string) => void
}

function ItemRow({ item, row, onPreviewVendors, onSaveLink, onCreateBox, onCreateEmails, onBoxLinkChange }: ItemRowProps) {
  const boxError = row.boxResult?.error
  const emailSuccessCount = row.emailResults?.filter(r => r.success).length ?? 0
  const emailFailCount = row.emailResults?.filter(r => !r.success).length ?? 0

  return (
    <>
      <tr>
        <td><strong>{item.part_number}</strong></td>
        <td>
          <div style={{ fontSize: 13 }}>{item.process}</div>
          <div style={{ fontSize: 11, color: '#666' }}>{item.spec}</div>
        </td>
        <td style={{ fontSize: 12, color: '#666' }}>{item.qt_so_number}</td>
        <td style={{ fontSize: 12, color: '#666' }}>{item.quantities}</td>
        <td>
          <CuiBadge value={item.cui_itar} />
          {item.sent && (
            <div style={{ fontSize: 10, color: '#888', marginTop: 2 }}>
              drafted {item.sent}
            </div>
          )}
        </td>
        <td>
          <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
            <input
              value={row.boxLink}
              onChange={(e) => onBoxLinkChange(e.target.value)}
              placeholder="Paste or create Box link…"
              style={{ fontSize: 12, flex: 1, minWidth: 160 }}
            />
            <button
              onClick={onSaveLink}
              disabled={row.saveLinkLoading || !row.boxLink}
              title="Save link to queue"
              style={{ fontSize: 11, padding: '3px 8px', whiteSpace: 'nowrap' }}
            >
              {row.saveLinkLoading ? '…' : 'Save'}
            </button>
            {row.saveLinkStatus === 'saved' && (
              <span style={{ fontSize: 11, color: '#137333' }}>✓</span>
            )}
            {row.saveLinkStatus === 'error' && (
              <span style={{ fontSize: 11, color: '#d93025' }}>✗</span>
            )}
          </div>
          {row.boxResult?.is_cui && row.boxResult.password && (
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Password: <code style={{ userSelect: 'all' }}>{row.boxResult.password}</code>
            </div>
          )}
          {row.boxPassword && !row.boxResult && (
            <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
              Stored pwd: <code style={{ userSelect: 'all' }}>{row.boxPassword}</code>
            </div>
          )}
        </td>
        <td style={{ whiteSpace: 'nowrap', verticalAlign: 'top', paddingTop: 8 }}>
          <button
            style={{ fontSize: 12, padding: '3px 10px', marginRight: 4 }}
            onClick={onPreviewVendors}
            disabled={row.vendorsLoading}
          >
            {row.vendorsLoading ? '…' : row.vendors !== null ? 'Vendors ▾' : 'Vendors'}
          </button>
          <button
            style={{ fontSize: 12, padding: '3px 10px', marginRight: 4 }}
            onClick={onCreateBox}
            disabled={row.boxLoading}
          >
            {row.boxLoading ? 'Creating…' : row.boxLink ? '↺ Box' : '+ Box'}
          </button>
          <button
            className="primary"
            style={{ fontSize: 12, padding: '3px 10px' }}
            onClick={onCreateEmails}
            disabled={row.emailLoading}
          >
            {row.emailLoading ? 'Sending…' : item.sent ? 'Re-draft' : 'Draft Emails'}
          </button>
        </td>
      </tr>

      {/* Box error row */}
      {boxError && (
        <tr>
          <td colSpan={7} style={{ background: '#fff0f0', fontSize: 12, color: '#d93025', padding: '4px 12px' }}>
            Box error: {boxError}
          </td>
        </tr>
      )}

      {/* Vendor preview row */}
      {row.vendors !== null && (
        <tr>
          <td colSpan={7} style={{ background: '#f8f9fa', padding: '6px 12px' }}>
            {row.vendors.length === 0 ? (
              <span style={{ fontSize: 12, color: '#d93025' }}>No matching vendors found.</span>
            ) : (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {row.vendors.map((v) => (
                  <div key={v.name} style={{ fontSize: 12, background: '#fff', border: '1px solid #e0e0e0', borderRadius: 6, padding: '4px 10px' }}>
                    <strong>{v.name}</strong>
                    {v.contact_name && <span style={{ color: '#666' }}> · {v.contact_name}</span>}
                    {v.contact_email && <span style={{ color: '#1a73e8' }}> &lt;{v.contact_email}&gt;</span>}
                  </div>
                ))}
              </div>
            )}
          </td>
        </tr>
      )}

      {/* Email results row */}
      {row.emailResults !== null && (
        <tr>
          <td colSpan={7} style={{ background: emailFailCount > 0 ? '#fff8e1' : '#e6f4ea', padding: '6px 12px' }}>
            <div style={{ fontSize: 12, marginBottom: 4, fontWeight: 600 }}>
              Email drafts: {emailSuccessCount} created
              {emailFailCount > 0 && `, ${emailFailCount} failed`}
            </div>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
              {row.emailResults.map((r, i) => (
                <span key={i} title={r.error ?? ''}>
                  <ResultPill success={r.success} label={r.vendor || r.contact_email} />
                </span>
              ))}
            </div>
          </td>
        </tr>
      )}
    </>
  )
}
