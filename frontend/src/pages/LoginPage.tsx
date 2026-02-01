import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'
import LorisAvatar from '../components/LorisAvatar'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const { login } = useAuth()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)

    try {
      await login(email, password)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-cream relative overflow-hidden">
      {/* Content */}
      <div className="min-h-screen flex flex-col items-center justify-center px-4">
        {/* Hero section */}
        <div className="text-center mb-10 max-w-lg">
          <LorisAvatar mood="default" size="xl" className="mx-auto mb-6" />
          <h1 className="font-serif text-5xl text-ink-primary mb-3">Loris</h1>
          <p className="font-serif text-xl text-ink-secondary leading-relaxed mb-4">
            Have a question? Get a definitive answer from Loris.
          </p>
          <p className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-1">
            Intelligent Q&A Platform
          </p>
          <p className="font-mono text-[10px] text-ink-muted">
            Slow is smooth, smooth is fast
          </p>
        </div>

        {/* Login card */}
        <div className="w-full max-w-sm">
          <div className="card-tufte">
            <form onSubmit={handleSubmit} className="space-y-5">
              {error && (
                <div className="p-3 bg-cream-200 border border-status-error rounded-sm">
                  <p className="font-serif text-sm text-status-error">{error}</p>
                </div>
              )}

              <div>
                <label htmlFor="email" className="label-tufte">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-tufte w-full"
                  placeholder="you@company.com"
                  required
                />
              </div>

              <div>
                <label htmlFor="password" className="label-tufte">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-tufte w-full"
                  placeholder="Your password"
                  required
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="btn-primary w-full disabled:opacity-50"
              >
                {isLoading ? 'Signing in...' : 'Sign in'}
              </button>
            </form>
          </div>

          {/* First-time setup hint */}
          <div className="mt-6 text-center">
            <p className="font-mono text-[10px] text-ink-muted">
              First time? Use the default admin account to get started.
            </p>
            <p className="font-mono text-[10px] text-ink-tertiary mt-1">
              admin@loris.local / Password123
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
