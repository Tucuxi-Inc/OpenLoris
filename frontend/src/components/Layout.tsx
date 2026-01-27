import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

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
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link to="/dashboard" className="flex items-center gap-3 no-underline hover:no-underline">
              <img
                src="/loris-images/Loris.png"
                alt="Loris"
                className="h-20 w-auto"
              />
              <div className="flex flex-col">
                <span className="font-serif text-2xl text-ink-primary">Loris</span>
                <span className="font-mono text-[10px] text-ink-tertiary tracking-wide">
                  Slow is smooth, smooth is fast
                </span>
              </div>
            </Link>

            {/* Navigation — role-aware */}
            <nav className="flex items-center gap-8">
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
                </>
              )}

              {/* Admin links */}
              {isAdmin && (
                <Link
                  to="/admin/users"
                  className={`font-serif text-sm no-underline ${
                    isActivePrefix('/admin') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Users
                </Link>
              )}
            </nav>

            {/* User menu */}
            <div className="flex items-center gap-4">
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
