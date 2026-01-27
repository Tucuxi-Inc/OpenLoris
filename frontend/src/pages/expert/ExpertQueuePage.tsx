import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { questionsApi, Question, QuestionPriority } from '../../lib/api/questions'

export default function ExpertQueuePage() {
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<Question[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [priorityFilter, setPriorityFilter] = useState<QuestionPriority | ''>('')

  useEffect(() => {
    loadQueue()
  }, [page, categoryFilter, priorityFilter])

  const loadQueue = async () => {
    try {
      setIsLoading(true)
      const params: Record<string, string> = { page: String(page), page_size: '20' }
      if (categoryFilter) params.category = categoryFilter
      if (priorityFilter) params.priority = priorityFilter
      const result = await questionsApi.getQueue(params as { category?: string; priority?: QuestionPriority; page?: number })
      setQuestions(result.items)
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load queue:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAssign = async (id: string, e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    try {
      await questionsApi.assign(id)
      navigate(`/expert/questions/${id}`)
    } catch (err) {
      console.error('Failed to assign:', err)
    }
  }

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'text-status-error'
      case 'high': return 'text-status-warning'
      default: return 'text-ink-tertiary'
    }
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

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">Expert Queue</h1>
        <p className="font-serif text-ink-secondary">
          {total} question{total !== 1 ? 's' : ''} awaiting expert review.
        </p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4 mb-8">
        <select
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
          className="input-tufte text-sm"
        >
          <option value="">All categories</option>
          <option value="Contracts">Contracts</option>
          <option value="Employment">Employment</option>
          <option value="Privacy & Data">Privacy & Data</option>
          <option value="Intellectual Property">IP</option>
          <option value="Compliance">Compliance</option>
          <option value="Corporate">Corporate</option>
        </select>
        <select
          value={priorityFilter}
          onChange={(e) => { setPriorityFilter(e.target.value as QuestionPriority | ''); setPage(1) }}
          className="input-tufte text-sm"
        >
          <option value="">All priorities</option>
          <option value="urgent">Urgent</option>
          <option value="high">High</option>
          <option value="normal">Normal</option>
          <option value="low">Low</option>
        </select>
      </div>

      {isLoading ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">Loading queue...</p>
        </div>
      ) : (
        <>
          {/* Queue list */}
          <div className="space-y-4">
            {questions.map((question) => (
              <Link
                key={question.id}
                to={`/expert/questions/${question.id}`}
                className="block no-underline"
              >
                <div className="card-tufte cursor-pointer hover:border-rule-medium transition-colors">
                  {/* Header */}
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-3">
                      <span className={`status uppercase ${getPriorityStyle(question.priority)}`}>
                        {question.priority}
                      </span>
                      <span className="text-ink-muted">·</span>
                      <span className="font-mono text-xs text-ink-secondary">
                        {question.category || 'Uncategorized'}
                      </span>
                    </div>
                    <span className="font-mono text-xs text-ink-muted">{formatDate(question.created_at)}</span>
                  </div>

                  {/* Question text */}
                  <p className="font-serif text-lg leading-relaxed text-ink-primary mb-3">
                    {question.original_text}
                  </p>

                  {/* Gap analysis indicator */}
                  {question.gap_analysis && (
                    <div className="inline-flex items-center gap-2 px-3 py-1 bg-cream-200 rounded-sm mb-3">
                      <span className="font-mono text-xs text-status-success">Gap Analysis Ready</span>
                    </div>
                  )}

                  {/* Footer */}
                  <hr className="my-4" />
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-xs text-ink-tertiary">
                      Status: {question.status.replace(/_/g, ' ')}
                    </span>
                    <div className="flex gap-4">
                      <button
                        onClick={(e) => handleAssign(question.id, e)}
                        className="font-serif text-sm text-ink-secondary hover:text-ink-primary"
                      >
                        Assign to me
                      </button>
                      <span className="font-serif text-sm text-loris-brown">
                        Review →
                      </span>
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary disabled:opacity-50"
              >
                Previous
              </button>
              <span className="font-mono text-xs text-ink-tertiary">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}

          {/* Empty state */}
          {questions.length === 0 && (
            <div className="card-tufte text-center py-12">
              <p className="font-serif text-ink-secondary">
                No questions in the queue. Great work!
              </p>
            </div>
          )}
        </>
      )}
    </div>
  )
}
