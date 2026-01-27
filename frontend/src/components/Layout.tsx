import { Outlet, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function Layout() {
  const { user, isExpert, logout } = useAuth()
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path

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
              <span className="font-serif text-2xl text-ink-primary">Loris</span>
              <span className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
                Legal Q&A
              </span>
            </Link>

            {/* Navigation */}
            <nav className="flex items-center gap-8">
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
              {isExpert && (
                <Link
                  to="/expert/queue"
                  className={`font-serif text-sm no-underline ${
                    isActive('/expert/queue') ? 'text-loris-brown' : 'text-ink-secondary hover:text-ink-primary'
                  }`}
                >
                  Expert Queue
                </Link>
              )}
            </nav>

            {/* User menu */}
            <div className="flex items-center gap-4">
              <span className="font-mono text-xs text-ink-tertiary">
                {user?.name}
              </span>
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
