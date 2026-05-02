/**
 * Queue page — the main table view + add form.
 *
 * TanStack Query pattern used here:
 *
 *   useQuery fetches the queue on mount and caches it under the key ['queue'].
 *   useMutation handles DELETE. When it succeeds, we call
 *   queryClient.invalidateQueries({ queryKey: ['queue'] }) which tells TQ
 *   "the cached queue data is stale — re-fetch it." The table updates
 *   automatically without us manually tracking the list in state.
 *
 * This is the biggest ergonomic win over Streamlit: no page rerun,
 * no re-running all the Python, just a targeted cache invalidation.
 */

import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchQueue, removeQueueItem, type QueueItem } from '../api/queue'
import { useAuth } from '../context/AuthContext'
import AddToQueueForm from '../components/AddToQueueForm'
import Nav from '../components/Nav'

export default function QueuePage() {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [showForm, setShowForm] = useState(false)

  const { data: queue = [], isLoading, isError } = useQuery({
    queryKey: ['queue'],
    queryFn: fetchQueue,
  })

  const deleteMutation = useMutation({
    mutationFn: removeQueueItem,
    onSuccess: () => {
      // Invalidate = mark cached data stale → triggers a background re-fetch
      queryClient.invalidateQueries({ queryKey: ['queue'] })
    },
  })

  function handleAddSuccess() {
    setShowForm(false)
    queryClient.invalidateQueries({ queryKey: ['queue'] })
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      <Nav />
    <div style={{ padding: 24 }}>
      <h1 style={{ margin: '0 0 20px', fontSize: 20 }}>📋 RFQ Queue</h1>

      {/* Add button — only visible to estimators and admins */}
      {(user?.role === 'estimator' || user?.role === 'admin') && (
        <button
          className={showForm ? '' : 'primary'}
          onClick={() => setShowForm((v) => !v)}
          style={{ marginBottom: 8 }}
        >
          {showForm ? '✕ Cancel' : '+ Add to Queue'}
        </button>
      )}

      {showForm && <AddToQueueForm onSuccess={handleAddSuccess} />}

      {/* Status messages */}
      {isLoading && <p>Loading queue…</p>}
      {isError && <p style={{ color: '#d93025' }}>Could not load queue. Is the API running?</p>}

      {/* Queue table */}
      {!isLoading && !isError && (
        <>
          <p style={{ color: '#666', margin: '16px 0 8px' }}>
            {queue.length} item{queue.length !== 1 ? 's' : ''} in queue
          </p>
          <table>
            <thead>
              <tr>
                <th>Part #</th>
                <th>Rev</th>
                <th>Process</th>
                <th>Spec</th>
                <th>Material</th>
                <th>Qty</th>
                <th>Due Date</th>
                <th>QT/SO #</th>
                <th>CUI/ITAR</th>
                <th>Submitted By</th>
                <th>Sent</th>
                {user?.role === 'admin' && <th></th>}
              </tr>
            </thead>
            <tbody>
              {queue.length === 0 ? (
                <tr>
                  <td colSpan={12} style={{ textAlign: 'center', padding: 32, color: '#666' }}>
                    Queue is empty. Add a part to get started.
                  </td>
                </tr>
              ) : (
                queue.map((item: QueueItem, i: number) => (
                  <tr key={`${item.part_number}-${item.process}-${i}`}>
                    <td><strong>{item.part_number}</strong></td>
                    <td>{item.rev}</td>
                    <td>{item.process}</td>
                    <td>{item.spec}</td>
                    <td>{item.material}</td>
                    <td>{item.quantities}</td>
                    <td>{item.due_date}</td>
                    <td>{item.qt_so_number}</td>
                    <td>
                      {item.cui_itar
                        ? <span style={{ color: '#e37400', fontWeight: 600 }}>⚠ Yes</span>
                        : <span style={{ color: '#666' }}>No</span>
                      }
                    </td>
                    <td style={{ color: '#666', fontSize: 13 }}>{item.submitted_by}</td>
                    <td style={{ color: '#666', fontSize: 13 }}>{item.sent}</td>
                    {user?.role === 'admin' && (
                      <td>
                        <button
                          className="danger"
                          style={{ padding: '3px 10px', fontSize: 12 }}
                          disabled={deleteMutation.isPending}
                          onClick={() => {
                            if (confirm(`Remove "${item.part_number}" from queue?`)) {
                              deleteMutation.mutate(item.part_number)
                            }
                          }}
                        >
                          Remove
                        </button>
                      </td>
                    )}
                  </tr>
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
