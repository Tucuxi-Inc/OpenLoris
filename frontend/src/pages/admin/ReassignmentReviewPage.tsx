import { useState, useEffect } from 'react'
import { subdomainsApi, ReassignmentRequest } from '../../lib/api/subdomains'

export default function ReassignmentReviewPage() {
  const [requests, setRequests] = useState<ReassignmentRequest[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [statusFilter, setStatusFilter] = useState<string>('pending')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Review modal
  const [reviewing, setReviewing] = useState<ReassignmentRequest | null>(null)
  const [adminNotes, setAdminNotes] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => { loadRequests() }, [statusFilter])

  const loadRequests = async () => {
    try {
      setIsLoading(true)
      const result = await subdomainsApi.listReassignments(statusFilter || undefined)
      setRequests(result)
    } catch (err) {
      console.error('Failed to load reassignments:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleReview = async (approved: boolean) => {
    if (!reviewing) return
    setIsSaving(true)
    try {
      await subdomainsApi.reviewReassignment(reviewing.id, approved, adminNotes || undefined)
      setSuccess(approved ? 'Reassignment approved — question rerouted.' : 'Reassignment rejected.')
      setReviewing(null)
      setAdminNotes('')
      await loadRequests()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Review failed')
    } finally {
      setIsSaving(false)
    }
  }

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'pending': return 'text-status-warning'
      case 'approved': return 'text-status-success'
      case 'rejected': return 'text-status-error'
      default: return 'text-ink-tertiary'
    }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString('en-US', {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
    })
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl text-ink-primary mb-2">Reassignment Requests</h1>
          <p className="font-serif text-ink-secondary">
            Review expert requests to reroute questions to different sub-domains.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-6">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}
      {success && (
        <div className="p-3 bg-cream-200 border border-status-success rounded-sm mb-6">
          <p className="font-serif text-sm text-status-success">{success}</p>
        </div>
      )}

      {/* Status filter */}
      <div className="flex items-center gap-4 mb-6">
        {['pending', 'approved', 'rejected', ''].map(s => (
          <button
            key={s || 'all'}
            onClick={() => setStatusFilter(s)}
            className={`font-mono text-xs pb-1 border-b-2 transition-colors ${
              statusFilter === s
                ? 'text-loris-brown border-loris-brown'
                : 'text-ink-tertiary border-transparent hover:text-ink-primary'
            }`}
          >
            {s || 'All'}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">Loading...</p>
        </div>
      ) : requests.length === 0 ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">
            No {statusFilter ? statusFilter : ''} reassignment requests.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {requests.map(req => (
            <div key={req.id} className="card-tufte">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-2">
                    <span className={`font-mono text-xs uppercase ${getStatusStyle(req.status)}`}>
                      {req.status}
                    </span>
                    <span className="font-mono text-[10px] text-ink-tertiary">
                      {formatDate(req.created_at)}
                    </span>
                  </div>
                  <p className="font-serif text-sm text-ink-primary mb-2">
                    <strong>{req.requested_by_name || 'Expert'}</strong> requests rerouting
                    {req.current_subdomain_name && (
                      <> from <span className="text-loris-brown">{req.current_subdomain_name}</span></>
                    )}
                    {' '}to <span className="text-loris-brown">{req.suggested_subdomain_name || 'Unknown'}</span>
                  </p>
                  <p className="font-serif text-sm text-ink-secondary italic">
                    "{req.reason}"
                  </p>
                  {req.admin_notes && (
                    <p className="font-mono text-xs text-ink-tertiary mt-2">
                      Admin notes: {req.admin_notes}
                    </p>
                  )}
                </div>

                {req.status === 'pending' && (
                  <button
                    onClick={() => { setReviewing(req); setAdminNotes('') }}
                    className="btn-primary text-sm"
                  >
                    Review
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Review Modal */}
      {reviewing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-md border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-4">Review Reassignment</h2>

            <div className="space-y-3 mb-6">
              <p className="font-serif text-sm text-ink-secondary">
                <strong>{reviewing.requested_by_name}</strong> wants to reroute from{' '}
                <span className="text-loris-brown">{reviewing.current_subdomain_name || 'None'}</span> to{' '}
                <span className="text-loris-brown">{reviewing.suggested_subdomain_name}</span>
              </p>
              <p className="font-serif text-sm text-ink-secondary italic">
                "{reviewing.reason}"
              </p>
            </div>

            <div className="mb-6">
              <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">
                Admin Notes (optional)
              </label>
              <textarea
                value={adminNotes}
                onChange={(e) => setAdminNotes(e.target.value)}
                className="input-tufte w-full"
                rows={3}
                placeholder="Add notes for the expert..."
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-rule-light">
              <button
                onClick={() => setReviewing(null)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={() => handleReview(false)}
                disabled={isSaving}
                className="px-4 py-2 bg-status-error text-cream-50 rounded-sm font-mono text-sm hover:opacity-90 disabled:opacity-50"
              >
                Reject
              </button>
              <button
                onClick={() => handleReview(true)}
                disabled={isSaving}
                className="btn-primary disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Approve & Reroute'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
