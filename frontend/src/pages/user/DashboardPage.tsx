import { Link } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function DashboardPage() {
  const { user } = useAuth()

  // TODO: Fetch questions from API
  const questions = [
    {
      id: '1',
      text: 'Can we add a non-compete clause to the vendor contract?',
      status: 'answered',
      category: 'Contracts',
      createdAt: '2 hours ago',
    },
    {
      id: '2',
      text: 'What are the GDPR requirements for storing customer data in the EU?',
      status: 'expert_queue',
      category: 'Privacy',
      createdAt: '1 day ago',
    },
    {
      id: '3',
      text: 'Is our current NDA template sufficient for international vendors?',
      status: 'auto_answered',
      category: 'Contracts',
      createdAt: '3 days ago',
    },
  ]

  const getStatusLabel = (status: string) => {
    const labels: Record<string, { text: string; class: string }> = {
      submitted: { text: 'Submitted', class: 'text-ink-tertiary' },
      processing: { text: 'Processing', class: 'text-ink-tertiary' },
      auto_answered: { text: 'Automated', class: 'text-status-success' },
      expert_queue: { text: 'Researching', class: 'text-status-warning' },
      in_progress: { text: 'In Progress', class: 'text-status-warning' },
      answered: { text: 'Answered', class: 'text-status-success' },
      resolved: { text: 'Resolved', class: 'text-status-success' },
    }
    return labels[status] || { text: status, class: 'text-ink-tertiary' }
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">My Questions</h1>
        <p className="font-serif text-ink-secondary">
          Welcome back, {user?.name}. Here are your recent questions.
        </p>
      </div>

      {/* Quick action */}
      <div className="mb-8">
        <Link to="/ask" className="btn-primary inline-block">
          Ask a New Question
        </Link>
      </div>

      {/* Questions list */}
      <div className="space-y-4">
        {questions.map((question) => {
          const status = getStatusLabel(question.status)
          return (
            <div
              key={question.id}
              className={`card-tufte cursor-pointer hover:border-rule-medium transition-colors ${
                question.status === 'answered' || question.status === 'auto_answered'
                  ? 'card-elevated'
                  : ''
              }`}
            >
              {/* Status line */}
              <div className="flex items-center gap-2 mb-3">
                <span className={`status ${status.class}`}>{status.text}</span>
                <span className="text-ink-muted">·</span>
                <span className="font-mono text-xs text-ink-muted">{question.createdAt}</span>
              </div>

              {/* Question text */}
              <p className="font-serif text-lg leading-relaxed text-ink-primary">
                {question.text}
              </p>

              {/* Footer */}
              <hr className="my-4" />
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-ink-secondary">{question.category}</span>
                <span className="font-serif text-sm text-loris-brown">View →</span>
              </div>
            </div>
          )
        })}
      </div>

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
    </div>
  )
}
