import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

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
    <div className="min-h-screen bg-cream flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-12">
          <img
            src="/loris-images/Loris.png"
            alt="Loris"
            className="h-48 w-auto mx-auto mb-4"
          />
          <h1 className="font-serif text-4xl text-ink-primary mb-2">Loris</h1>
          <p className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
            Intelligent Legal Q&A
          </p>
        </div>

        {/* Login form */}
        <div className="card-tufte">
          <form onSubmit={handleSubmit} className="space-y-6">
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

        {/* Footer */}
        <p className="mt-8 text-center font-serif text-sm text-ink-tertiary">
          Ask questions. Get answers.
        </p>
      </div>
    </div>
  )
}
