import { useAuth } from '../../contexts/AuthContext'

export default function ExpertQueuePage() {
  const { user } = useAuth()

  // TODO: Fetch from API
  const queuedQuestions = [
    {
      id: '1',
      text: 'What are the GDPR requirements for storing customer data in the EU?',
      category: 'Privacy',
      priority: 'high',
      askedBy: 'Marketing Team',
      createdAt: '1 day ago',
      hasGapAnalysis: true,
    },
    {
      id: '2',
      text: 'Can we use the same contractor agreement template for international contractors?',
      category: 'Employment',
      priority: 'normal',
      askedBy: 'HR Department',
      createdAt: '2 days ago',
      hasGapAnalysis: true,
    },
    {
      id: '3',
      text: 'What liability protections should we include in our SaaS agreement?',
      category: 'Contracts',
      priority: 'urgent',
      askedBy: 'Product Team',
      createdAt: '3 hours ago',
      hasGapAnalysis: false,
    },
  ]

  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'urgent':
        return 'text-status-error'
      case 'high':
        return 'text-status-warning'
      default:
        return 'text-ink-tertiary'
    }
  }

  return (
    <div>
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">Expert Queue</h1>
        <p className="font-serif text-ink-secondary">
          {queuedQuestions.length} questions awaiting your expertise.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <div className="card-tufte text-center">
          <div className="metric-value">{queuedQuestions.length}</div>
          <div className="metric-label">Pending</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">2</div>
          <div className="metric-label">In Progress</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">12</div>
          <div className="metric-label">Answered Today</div>
        </div>
        <div className="card-tufte text-center">
          <div className="metric-value">4.2h</div>
          <div className="metric-label">Avg Response</div>
        </div>
      </div>

      {/* Queue list */}
      <div className="space-y-4">
        {queuedQuestions.map((question) => (
          <div
            key={question.id}
            className="card-tufte cursor-pointer hover:border-rule-medium transition-colors"
          >
            {/* Header */}
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <span className={`status uppercase ${getPriorityStyle(question.priority)}`}>
                  {question.priority}
                </span>
                <span className="text-ink-muted">·</span>
                <span className="font-mono text-xs text-ink-secondary">{question.category}</span>
              </div>
              <span className="font-mono text-xs text-ink-muted">{question.createdAt}</span>
            </div>

            {/* Question text */}
            <p className="font-serif text-lg leading-relaxed text-ink-primary mb-3">
              {question.text}
            </p>

            {/* Gap analysis indicator */}
            {question.hasGapAnalysis && (
              <div className="inline-flex items-center gap-2 px-3 py-1 bg-cream-200 rounded-sm">
                <span className="font-mono text-xs text-status-success">Gap Analysis Ready</span>
              </div>
            )}

            {/* Footer */}
            <hr className="my-4" />
            <div className="flex items-center justify-between">
              <span className="font-mono text-xs text-ink-tertiary">
                Asked by {question.askedBy}
              </span>
              <div className="flex gap-4">
                <button className="font-serif text-sm text-ink-secondary hover:text-ink-primary">
                  Assign to me
                </button>
                <button className="font-serif text-sm text-loris-brown">
                  Review →
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Empty state */}
      {queuedQuestions.length === 0 && (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">
            No questions in the queue. Great work!
          </p>
        </div>
      )}
    </div>
  )
}
