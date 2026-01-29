import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { notificationsApi, Notification } from '../lib/api/notifications'
import LorisAvatar from '../components/LorisAvatar'

export default function NotificationsPage() {
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [loading, setLoading] = useState(true)
  const [unreadOnly, setUnreadOnly] = useState(false)
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [unreadCount, setUnreadCount] = useState(0)
  const pageSize = 20

  useEffect(() => {
    loadNotifications()
  }, [unreadOnly, page])

  const loadNotifications = async () => {
    setLoading(true)
    try {
      const res = await notificationsApi.list({
        unread_only: unreadOnly,
        page,
        page_size: pageSize,
      })
      setNotifications(res.items)
      setTotal(res.total)
      setUnreadCount(res.unread_count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }

  const handleMarkRead = async (id: string) => {
    try {
      await notificationsApi.markRead(id)
      setNotifications(prev => prev.map(n => n.id === id ? { ...n, is_read: true } : n))
      setUnreadCount(prev => Math.max(0, prev - 1))
    } catch {
      // ignore
    }
  }

  const handleMarkAllRead = async () => {
    try {
      await notificationsApi.markAllRead()
      setNotifications(prev => prev.map(n => ({ ...n, is_read: true })))
      setUnreadCount(0)
    } catch {
      // ignore
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await notificationsApi.delete(id)
      setNotifications(prev => prev.filter(n => n.id !== id))
      setTotal(prev => prev - 1)
    } catch {
      // ignore
    }
  }

  const formatTime = (ts: string): string => {
    return new Date(ts).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
    })
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="px-8 py-12 max-w-4xl mx-auto">
      {/* Header */}
      <div className="border-b border-rule-light pb-6 mb-8">
        <h1 className="font-serif text-3xl text-ink-primary">Notifications</h1>
        <p className="font-serif text-sm text-ink-secondary mt-2">
          Stay updated on questions, answers, and knowledge base changes
        </p>
      </div>

      {/* Controls */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <button
            onClick={() => { setUnreadOnly(false); setPage(1) }}
            className={`font-mono text-sm px-3 py-1 border transition-colors ${
              !unreadOnly
                ? 'border-loris-brown text-loris-brown'
                : 'border-rule-light text-ink-secondary hover:text-ink-primary'
            }`}
          >
            All ({total})
          </button>
          <button
            onClick={() => { setUnreadOnly(true); setPage(1) }}
            className={`font-mono text-sm px-3 py-1 border transition-colors ${
              unreadOnly
                ? 'border-loris-brown text-loris-brown'
                : 'border-rule-light text-ink-secondary hover:text-ink-primary'
            }`}
          >
            Unread ({unreadCount})
          </button>
        </div>

        {unreadCount > 0 && (
          <button
            onClick={handleMarkAllRead}
            className="font-mono text-sm text-loris-brown hover:text-ink-primary"
          >
            Mark all read
          </button>
        )}
      </div>

      {/* List */}
      {loading ? (
        <div className="text-center py-12">
          <LorisAvatar mood="thinking" size="lg" animate className="mx-auto mb-4" />
          <p className="font-mono text-sm text-ink-tertiary">Loading notifications...</p>
        </div>
      ) : notifications.length === 0 ? (
        <div className="text-center py-12">
          <LorisAvatar mood="default" size="lg" className="mx-auto mb-4" />
          <p className="font-serif text-ink-secondary">
            {unreadOnly ? 'No unread notifications' : 'No notifications yet'}
          </p>
        </div>
      ) : (
        <div className="border border-rule-light divide-y divide-rule-light">
          {notifications.map(n => (
            <div
              key={n.id}
              className={!n.is_read ? 'bg-cream-100' : ''}
            >
              <Link
                to={n.link_url || '#'}
                onClick={() => {
                  if (!n.is_read) handleMarkRead(n.id)
                }}
                className="block px-6 py-4 hover:bg-cream-100 transition-colors no-underline"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {!n.is_read && (
                        <div className="w-2 h-2 bg-loris-brown rounded-full flex-shrink-0" />
                      )}
                      <span className="font-serif text-base text-ink-primary">
                        {n.title}
                      </span>
                    </div>
                    <p className="font-serif text-sm text-ink-secondary mb-2">
                      {n.message}
                    </p>
                    <p className="font-mono text-xs text-ink-tertiary">
                      {formatTime(n.created_at)}
                    </p>
                  </div>
                  <button
                    onClick={(e) => handleDelete(n.id, e)}
                    className="flex-shrink-0 text-ink-tertiary hover:text-status-error transition-colors"
                    aria-label="Delete notification"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="mt-8 flex items-center justify-center gap-2">
          <button
            onClick={() => setPage(p => Math.max(1, p - 1))}
            disabled={page === 1}
            className="font-mono text-sm px-3 py-1 border border-rule-light disabled:opacity-50 disabled:cursor-not-allowed hover:border-loris-brown hover:text-loris-brown"
          >
            Previous
          </button>
          <span className="font-mono text-sm text-ink-secondary px-4">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="font-mono text-sm px-3 py-1 border border-rule-light disabled:opacity-50 disabled:cursor-not-allowed hover:border-loris-brown hover:text-loris-brown"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
