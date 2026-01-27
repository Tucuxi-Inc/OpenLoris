import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'
import { questionsApi, Question, QuestionStatus } from '../../lib/api/questions'

export default function DashboardPage() {
  const { user } = useAuth()
  const [questions, setQuestions] = useState<Question[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [filter, setFilter] = useState<QuestionStatus | ''>('')

  useEffect(() => {
    loadQuestions()
  }, [filter])

  const loadQuestions = async () => {
    try {
      setIsLoading(true)
      const params: Record<string, string> = { page_size: '50' }
      if (filter) params.status = filter
      const result = await questionsApi.list(params as { status?: QuestionStatus; page?: number; page_size?: number })
      setQuestions(result.items)
    } catch (err) {
      console.error('Failed to load questions:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, { text: string; class: string }> = {
      submitted: { text: 'Submitted', class: 'text-ink-tertiary' },
      processing: { text: 'Processing', class: 'text-ink-tertiary' },
      auto_answered: { text: 'Auto-Answered', class: 'text-status-success' },
      human_requested: { text: 'Under Review', class: 'text-status-warning' },
      expert_queue: { text: 'Researching', class: 'text-status-warning' },
      in_progress: { text: 'In Progress', class: 'text-status-warning' },
      needs_clarification: { text: 'Needs Info', class: 'text-status-error' },
      answered: { text: 'Answered', class: 'text-status-success' },
      resolved: { text: 'Resolved', class: 'text-status-success' },
      closed: { text: 'Closed', class: 'text-ink-tertiary' },
    }
    return labels[status] || { text: status, class: 'text-ink-tertiary' }
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHours < 1) return 'Just now'
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    if (diffDays < 7) return `${diffDays}d ago`
    return date.toLocaleDateString()
  }

  // Actionable questions first (auto_answered, answered), then by date
  const actionable = questions.filter(q =>
    ['auto_answered', 'answered', 'needs_clarification'].includes(q.status)
  )
  const rest = questions.filter(q =>
    !['auto_answered', 'answered', 'needs_clarification'].includes(q.status)
  )

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">My Questions</h1>
        <p className="font-serif text-ink-secondary">
          Welcome back, {user?.name}. Here are your recent questions.
        </p>
      </div>

      {/* Quick action + filter */}
      <div className="flex items-center justify-between mb-8">
        <Link to="/ask" className="btn-primary inline-block">
          Ask a New Question
        </Link>
        <select
          value={filter}
          onChange={(e) => setFilter(e.target.value as QuestionStatus | '')}
          className="input-tufte text-sm"
        >
          <option value="">All statuses</option>
          <option value="submitted">Submitted</option>
          <option value="auto_answered">Auto-Answered</option>
          <option value="expert_queue">In Queue</option>
          <option value="in_progress">In Progress</option>
          <option value="answered">Answered</option>
          <option value="resolved">Resolved</option>
        </select>
      </div>

      {isLoading ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">Loading questions...</p>
        </div>
      ) : (
        <>
          {/* Actionable items */}
          {actionable.length > 0 && (
            <div className="mb-6">
              <h2 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
                Needs Your Attention
              </h2>
              <div className="space-y-4">
                {actionable.map((question) => {
                  const status = getStatusLabel(question.status)
                  return (
                    <Link
                      key={question.id}
                      to={`/questions/${question.id}`}
                      className="block no-underline"
                    >
                      <div className="card-tufte card-elevated cursor-pointer hover:border-rule-medium transition-colors">
                        <div className="flex items-center gap-2 mb-3">
                          <span className={`status ${status.class}`}>{status.text}</span>
                          <span className="text-ink-muted">·</span>
                          <span className="font-mono text-xs text-ink-muted">{formatDate(question.created_at)}</span>
                        </div>
                        <p className="font-serif text-lg leading-relaxed text-ink-primary">
                          {question.original_text}
                        </p>
                        <hr className="my-4" />
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-ink-secondary">{question.category || 'Uncategorized'}</span>
                          <span className="font-serif text-sm text-loris-brown">
                            {question.status === 'auto_answered' ? 'Review Answer' :
                             question.status === 'answered' ? 'View Answer' :
                             'Respond'} →
                          </span>
                        </div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}

          {/* Other questions */}
          {rest.length > 0 && (
            <div>
              {actionable.length > 0 && (
                <h2 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
                  Other Questions
                </h2>
              )}
              <div className="space-y-4">
                {rest.map((question) => {
                  const status = getStatusLabel(question.status)
                  return (
                    <Link
                      key={question.id}
                      to={`/questions/${question.id}`}
                      className="block no-underline"
                    >
                      <div className="card-tufte cursor-pointer hover:border-rule-medium transition-colors">
                        <div className="flex items-center gap-2 mb-3">
                          <span className={`status ${status.class}`}>{status.text}</span>
                          <span className="text-ink-muted">·</span>
                          <span className="font-mono text-xs text-ink-muted">{formatDate(question.created_at)}</span>
                        </div>
                        <p className="font-serif text-lg leading-relaxed text-ink-primary">
                          {question.original_text}
                        </p>
                        <hr className="my-4" />
                        <div className="flex items-center justify-between">
                          <span className="font-mono text-xs text-ink-secondary">{question.category || 'Uncategorized'}</span>
                          <span className="font-serif text-sm text-loris-brown">View →</span>
                        </div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            </div>
          )}

          {/* Empty state */}
          {questions.length === 0 && (
            <div className="card-tufte text-center py-12">
              <p className="font-serif text-ink-secondary mb-4">
                You haven't asked any questions yet.
              </p>
              <Link to="/ask" className="btn-secondary inline-block">
                Ask Your First Question
              </Link>
            </div>
          )}
        </>
      )}
    </div>
  )
}
