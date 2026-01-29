import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { questionsApi, Question, QuestionPriority } from '../../lib/api/questions'
import { knowledgeApi, KnowledgeStats } from '../../lib/api/knowledge'
import LorisAvatar from '../../components/LorisAvatar'

export default function ExpertDashboard() {
  const { user } = useAuth()
  const [queueItems, setQueueItems] = useState<Question[]>([])
  const [stats, setStats] = useState<KnowledgeStats | null>(null)
  const [queueTotal, setQueueTotal] = useState(0)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    loadDashboard()
  }, [])

  const loadDashboard = async () => {
    try {
      setIsLoading(true)
      const [queueResult, knowledgeStats] = await Promise.allSettled([
        questionsApi.getQueue({ page: 1 } as { category?: string; priority?: QuestionPriority; page?: number }),
        knowledgeApi.getStats(),
      ])

      if (queueResult.status === 'fulfilled') {
        setQueueItems(queueResult.value.items)
        setQueueTotal(queueResult.value.total)
      }
      if (knowledgeStats.status === 'fulfilled') {
        setStats(knowledgeStats.value)
      }
    } catch (err) {
      console.error('Dashboard load error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-status-error'
      case 'high': return 'text-status-warning'
      default: return 'text-ink-tertiary'
    }
  }

  if (isLoading) {
    return (
      <div className="card-tufte text-center py-12">
        <LorisAvatar mood="thinking" size="lg" animate className="mx-auto mb-4" />
        <p className="font-serif text-ink-secondary">Loading dashboard...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">Expert Dashboard</h1>
        <p className="font-serif text-ink-secondary">
          Welcome back, {user?.name}. Here's your overview.
        </p>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="card-tufte text-center">
          <div className="metric-value">{queueTotal}</div>
          <div className="metric-label">Pending</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">{stats?.total_facts || 0}</div>
          <div className="metric-label">Knowledge Facts</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">{stats?.expiring_soon || 0}</div>
          <div className="metric-label">Expiring Soon</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">{stats?.recently_added || 0}</div>
          <div className="metric-label">Added Recently</div>
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-2 gap-8">
        {/* Queue preview */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
              Queue Preview
            </h2>
            <Link to="/expert/queue" className="font-serif text-sm text-loris-brown no-underline">
              View all →
            </Link>
          </div>
          {queueItems.length > 0 ? (
            <div className="space-y-3">
              {queueItems.map((q) => (
                <Link
                  key={q.id}
                  to={`/expert/questions/${q.id}`}
                  className="block no-underline"
                >
                  <div className="card-tufte cursor-pointer hover:border-rule-medium transition-colors">
                    <div className="flex items-center gap-2 mb-2">
                      <span className={`status uppercase ${getPriorityStyle(q.priority)}`}>
                        {q.priority}
                      </span>
                      {q.category && (
                        <>
                          <span className="text-ink-muted">·</span>
                          <span className="font-mono text-xs text-ink-secondary">{q.category}</span>
                        </>
                      )}
                    </div>
                    <p className="font-serif text-sm text-ink-primary leading-relaxed line-clamp-2">
                      {q.original_text}
                    </p>
                  </div>
                </Link>
              ))}
            </div>
          ) : (
            <div className="card-tufte text-center py-8">
              <LorisAvatar mood="celebration" size="md" className="mx-auto mb-3" />
              <p className="font-serif text-ink-secondary">Queue is empty. Great work!</p>
            </div>
          )}
        </div>

        {/* Knowledge summary */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
              Knowledge Base
            </h2>
            <Link to="/expert/knowledge" className="font-serif text-sm text-loris-brown no-underline">
              Manage →
            </Link>
          </div>
          <div className="card-tufte">
            {stats && Object.keys(stats.by_tier).length > 0 ? (
              <div className="space-y-3">
                <h3 className="font-mono text-xs text-ink-tertiary">Facts by Tier</h3>
                {Object.entries(stats.by_tier).map(([tier, count]) => (
                  <div key={tier} className="flex items-center justify-between">
                    <span className="font-mono text-xs text-ink-secondary uppercase">{tier}</span>
                    <span className="font-mono text-sm text-ink-primary">{count}</span>
                  </div>
                ))}
                {Object.keys(stats.by_domain).length > 0 && (
                  <>
                    <hr className="my-3" />
                    <h3 className="font-mono text-xs text-ink-tertiary">By Domain</h3>
                    {Object.entries(stats.by_domain).map(([domain, count]) => (
                      <div key={domain} className="flex items-center justify-between">
                        <span className="font-serif text-sm text-ink-secondary">{domain}</span>
                        <span className="font-mono text-sm text-ink-primary">{count}</span>
                      </div>
                    ))}
                  </>
                )}
              </div>
            ) : (
              <div className="text-center py-6">
                <LorisAvatar mood="scholar" size="md" className="mx-auto mb-3" />
                <p className="font-serif text-ink-secondary mb-3">No knowledge facts yet.</p>
                <Link to="/expert/knowledge" className="btn-secondary inline-block text-sm">
                  Create First Fact
                </Link>
              </div>
            )}
          </div>

          {/* Quick links */}
          <div className="mt-6 space-y-2">
            <Link
              to="/expert/documents"
              className="block card-tufte hover:border-rule-medium transition-colors no-underline"
            >
              <span className="font-serif text-sm text-ink-primary">Document Management →</span>
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
