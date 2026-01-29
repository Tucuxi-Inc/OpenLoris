import { useState } from 'react'
import { useAuth } from '../contexts/AuthContext'

// Dev-only quick login accounts (remove for production)
const DEV_ACCOUNTS = [
  { email: 'carol@loris.dev', password: 'Test1234!', name: 'Carol', role: 'Business User', apiRole: 'business_user' },
  { email: 'bob@loris.dev', password: 'Test1234!', name: 'Bob', role: 'Domain Expert', apiRole: 'domain_expert' },
  { email: 'alice@loris.dev', password: 'Test1234!', name: 'Alice', role: 'Admin', apiRole: 'admin' },
]

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

  const handleQuickLogin = async (account: typeof DEV_ACCOUNTS[0]) => {
    setError('')
    setIsLoading(true)
    try {
      await login(account.email, account.password)
    } catch (err) {
      // If login fails, try to register the account
      const errorMsg = err instanceof Error ? err.message : 'Login failed'
      if (errorMsg.includes('Incorrect email or password')) {
        try {
          // Register the account
          const response = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              email: account.email,
              password: account.password,
              name: account.name,
              organization_name: 'Loris Development',
              role: account.apiRole,
            }),
          })

          if (response.ok) {
            const data = await response.json()
            localStorage.setItem('access_token', data.access_token)
            localStorage.setItem('refresh_token', data.refresh_token)
            // Reload to pick up the new session
            window.location.href = '/dashboard'
            return
          } else {
            const errData = await response.json()
            setError(errData.detail || 'Registration failed')
          }
        } catch (regErr) {
          setError('Failed to create account')
        }
      } else {
        setError(errorMsg)
      }
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
          <img
            src="/loris-images/Loris.png"
            alt="Loris"
            className="h-36 w-auto mx-auto mb-6"
          />
          <h1 className="font-serif text-5xl text-ink-primary mb-3">Loris</h1>
          <p className="font-serif text-xl text-ink-secondary leading-relaxed mb-4">
            Have a question? Get a definitive answer from Loris.
          </p>
          <p className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-1">
            Intelligent Legal Q&A Platform
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

          {/* Dev quick-login accounts */}
          <div className="mt-6">
            <p className="font-mono text-[10px] text-ink-muted text-center mb-3 uppercase tracking-wide">
              Development Quick Login
            </p>
            <div className="space-y-2">
              {DEV_ACCOUNTS.map((account) => (
                <button
                  key={account.email}
                  onClick={() => handleQuickLogin(account)}
                  disabled={isLoading}
                  className="w-full flex items-center justify-between px-4 py-3 bg-white border border-rule-light rounded-sm hover:border-loris-brown hover:bg-cream-200 transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-serif text-sm text-ink-primary">{account.name}</span>
                    <span className="font-mono text-[10px] text-ink-muted">{account.email}</span>
                  </div>
                  <span className={`font-mono text-xs ${
                    account.role === 'Admin' ? 'text-status-error' :
                    account.role === 'Domain Expert' ? 'text-status-warning' :
                    'text-ink-tertiary'
                  }`}>
                    {account.role}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
