import { useState, useEffect, useRef, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { notificationsApi, Notification } from '../lib/api/notifications'

export default function NotificationBell() {
  const [unreadCount, setUnreadCount] = useState(0)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const [isOpen, setIsOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  // Poll for unread count every 30 seconds
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await notificationsApi.getUnreadCount()
        setUnreadCount(res.unread_count)
      } catch {
        // Silently ignore polling errors
      }
    }
    fetchCount()
    const interval = setInterval(fetchCount, 30000)
    return () => clearInterval(interval)
  }, [])

  // Load notifications when dropdown opens
  const loadNotifications = useCallback(async () => {
    setLoading(true)
    try {
      const res = await notificationsApi.list({ page: 1, page_size: 10 })
      setNotifications(res.items)
      setUnreadCount(res.unread_count)
    } catch {
      // ignore
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isOpen) loadNotifications()
  }, [isOpen, loadNotifications])

  // Close dropdown on outside click
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setIsOpen(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [isOpen])

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

  const timeAgo = (ts: string): string => {
    const diff = Math.floor((Date.now() - new Date(ts).getTime()) / 1000)
    if (diff < 60) return 'just now'
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
    if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`
    return new Date(ts).toLocaleDateString()
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setIsOpen(o => !o)}
        className="relative p-2 text-ink-secondary hover:text-ink-primary transition-colors"
        aria-label="Notifications"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          strokeWidth={1.5}
          stroke="currentColor"
          className="w-5 h-5"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0"
          />
        </svg>
        {unreadCount > 0 && (
          <span className="absolute -top-0.5 -right-0.5 inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 text-[10px] font-mono font-semibold leading-none text-cream bg-loris-brown rounded-full">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-96 bg-cream border border-rule-light z-50">
          {/* Header */}
          <div className="px-4 py-3 border-b border-rule-light flex items-center justify-between">
            <span className="font-serif text-sm text-ink-primary">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="font-mono text-xs text-loris-brown hover:text-ink-primary"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* List */}
          <div className="max-h-96 overflow-y-auto">
            {loading ? (
              <div className="px-4 py-8 text-center font-mono text-xs text-ink-tertiary">
                Loading...
              </div>
            ) : notifications.length === 0 ? (
              <div className="px-4 py-8 text-center font-mono text-xs text-ink-tertiary">
                No notifications
              </div>
            ) : (
              <div className="divide-y divide-rule-light">
                {notifications.map(n => (
                  <Link
                    key={n.id}
                    to={n.link_url || '/notifications'}
                    onClick={() => {
                      if (!n.is_read) handleMarkRead(n.id)
                      setIsOpen(false)
                    }}
                    className={`block px-4 py-3 hover:bg-cream-100 transition-colors no-underline ${
                      !n.is_read ? 'bg-cream-100' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="flex-1 min-w-0">
                        <p className="font-serif text-sm text-ink-primary truncate">
                          {n.title}
                        </p>
                        <p className="font-serif text-xs text-ink-secondary mt-0.5 line-clamp-2">
                          {n.message}
                        </p>
                        <p className="font-mono text-[10px] text-ink-tertiary mt-1">
                          {timeAgo(n.created_at)}
                        </p>
                      </div>
                      {!n.is_read && (
                        <div className="flex-shrink-0 w-2 h-2 bg-loris-brown rounded-full mt-1.5" />
                      )}
                    </div>
                  </Link>
                ))}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-4 py-2 border-t border-rule-light">
            <Link
              to="/notifications"
              onClick={() => setIsOpen(false)}
              className="font-mono text-xs text-loris-brown hover:text-ink-primary no-underline block text-center"
            >
              View all notifications
            </Link>
          </div>
        </div>
      )}
    </div>
  )
}
