import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import NotificationBell from './NotificationBell'

export default function Layout() {
  const { user, isExpert, isAdmin, logout } = useAuth()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path
  const isActivePrefix = (prefix: string) => location.pathname.startsWith(prefix)

  return (
    <div className="min-h-screen bg-cream">
      {/* Header */}
      <header className="border-b border-rule-light">
        <div className="dashboard-width mx-auto px-8 py-4">
          {/* Row 1: Logo + User info */}
          <div className="flex items-center justify-between mb-3">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-3 no-underline hover:no-underline">
              <img
                src="/loris-images/Loris.png"
                alt="Open Loris"
                className="h-14 w-auto"
              />
              <div className="flex flex-col">
                <span className="font-serif text-2xl text-ink-primary">Open Loris</span>
                <span className="font-mono text-[10px] text-ink-tertiary tracking-wide">
                  Slow is smooth, smooth is fast
                </span>
              </div>
            </Link>

            {/* Notifications + User menu */}
            <div className="flex items-center gap-4">
              <NotificationBell />
              <div className="flex flex-col items-end">
                <span className="font-mono text-xs text-ink-tertiary">
                  {user?.name}
                </span>
                <span className="font-mono text-[10px] text-ink-muted">
                  {user?.role === 'admin' ? 'Admin' : user?.role === 'domain_expert' ? 'Expert' : ''}
                </span>
              </div>
              <button
                onClick={logout}
                className="font-mono text-xs text-ink-secondary hover:text-ink-primary"
              >
                Sign out
              </button>
            </div>
          </div>

          {/* Row 2: Navigation — role-aware */}
          <nav className="flex items-center gap-6 flex-wrap">
            {/* Business user links (visible to all) */}
            <Link
              to="/dashboard"
              className={`font-serif text-sm no-underline ${
                isActive('/dashboard') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              My Questions
            </Link>
            <Link
              to="/ask"
              className={`font-serif text-sm no-underline ${
                isActive('/ask') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              Ask a Question
            </Link>

            {/* Expert links */}
            {isExpert && (
              <>
                <span className="text-rule-medium">|</span>
                <Link
                  to="/expert"
                  className={`font-serif text-sm no-underline ${
                    isActive('/expert') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Dashboard
                </Link>
                <Link
                  to="/expert/queue"
                  className={`font-serif text-sm no-underline ${
                    isActive('/expert/queue') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Queue
                </Link>
                <Link
                  to="/expert/knowledge"
                  className={`font-serif text-sm no-underline ${
                    isActivePrefix('/expert/knowledge') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Knowledge
                </Link>
                <Link
                  to="/expert/documents"
                  className={`font-serif text-sm no-underline ${
                    isActivePrefix('/expert/documents') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Documents
                </Link>
                <Link
                  to="/expert/analytics"
                  className={`font-serif text-sm no-underline ${
                    isActivePrefix('/expert/analytics') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Analytics
                </Link>
              </>
            )}

            {/* Admin links */}
            {isAdmin && (
              <>
                <span className="text-rule-medium">|</span>
                <Link
                  to="/admin/users"
                  className={`font-serif text-sm no-underline ${
                    isActive('/admin/users') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Users
                </Link>
                <Link
                  to="/admin/subdomains"
                  className={`font-serif text-sm no-underline ${
                    isActive('/admin/subdomains') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Sub-Domains
                </Link>
                <Link
                  to="/admin/reassignments"
                  className={`font-serif text-sm no-underline ${
                    isActive('/admin/reassignments') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Reassignments
                </Link>
                <Link
                  to="/admin/settings"
                  className={`font-serif text-sm no-underline ${
                    isActive('/admin/settings') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Settings
                </Link>
                <Link
                  to="/moltenloris"
                  className={`font-serif text-sm no-underline ${
                    isActive('/moltenloris') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  MoltenLoris
                </Link>
              </>
            )}
          </nav>
        </div>
      </header>

      {/* Main content */}
      <main className="page-padding">
        <div className="dashboard-width mx-auto">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
