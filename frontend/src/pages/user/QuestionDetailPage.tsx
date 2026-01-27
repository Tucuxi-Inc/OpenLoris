import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { questionsApi, Question } from '../../lib/api/questions'

export default function QuestionDetailPage() {
  const { questionId } = useParams<{ questionId: string }>()
  const navigate = useNavigate()
  const [question, setQuestion] = useState<Question | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Feedback state
  const [rating, setRating] = useState(0)
  const [feedbackSubmitted, setFeedbackSubmitted] = useState(false)

  // Reject auto-answer state
  const [rejectReason, setRejectReason] = useState('')
  const [showRejectForm, setShowRejectForm] = useState(false)

  useEffect(() => {
    if (questionId) loadQuestion()
  }, [questionId])

  const loadQuestion = async () => {
    try {
      setIsLoading(true)
      const q = await questionsApi.get(questionId!)
      setQuestion(q)
      // Check if question has satisfaction rating already
      if (q.satisfaction_rating) {
        setRating(q.satisfaction_rating)
        setFeedbackSubmitted(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load question')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAcceptAuto = async () => {
    try {
      await questionsApi.submitFeedback(questionId!, 5)
      setFeedbackSubmitted(true)
      setRating(5)
      await loadQuestion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to accept')
    }
  }

  const handleRejectAuto = async () => {
    if (!rejectReason.trim()) return
    try {
      await questionsApi.requestHumanReview(questionId!, rejectReason)
      setShowRejectForm(false)
      await loadQuestion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request review')
    }
  }

  const handleFeedback = async (value: number) => {
    try {
      await questionsApi.submitFeedback(questionId!, value)
      setRating(value)
      setFeedbackSubmitted(true)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit feedback')
    }
  }

  const getStatusLabel = (status: string) => {
    const labels: Record<string, { text: string; class: string }> = {
      submitted: { text: 'Submitted', class: 'text-ink-tertiary' },
      processing: { text: 'Processing', class: 'text-ink-tertiary' },
      auto_answered: { text: 'Auto-Answered', class: 'text-status-success' },
      human_requested: { text: 'Under Review', class: 'text-status-warning' },
      expert_queue: { text: 'In Expert Queue', class: 'text-status-warning' },
      in_progress: { text: 'Expert Working', class: 'text-status-warning' },
      needs_clarification: { text: 'Needs Your Input', class: 'text-status-error' },
      answered: { text: 'Answered', class: 'text-status-success' },
      resolved: { text: 'Resolved', class: 'text-status-success' },
      closed: { text: 'Closed', class: 'text-ink-tertiary' },
    }
    return labels[status] || { text: status, class: 'text-ink-tertiary' }
  }

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleString()
  }

  if (isLoading) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-ink-secondary">Loading...</p>
      </div>
    )
  }

  if (error || !question) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-status-error mb-4">{error || 'Question not found'}</p>
        <button onClick={() => navigate('/dashboard')} className="btn-secondary">
          Back to Dashboard
        </button>
      </div>
    )
  }

  const status = getStatusLabel(question.status)

  return (
    <div className="max-w-3xl">
      {/* Back link */}
      <button
        onClick={() => navigate('/dashboard')}
        className="font-serif text-sm text-ink-secondary hover:text-ink-primary mb-6 block"
      >
        ← Back to My Questions
      </button>

      {/* Question card */}
      <div className="card-tufte mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className={`status ${status.class}`}>{status.text}</span>
          <span className="text-ink-muted">·</span>
          <span className="font-mono text-xs text-ink-muted">{formatDate(question.created_at)}</span>
          {question.category && (
            <>
              <span className="text-ink-muted">·</span>
              <span className="font-mono text-xs text-ink-secondary">{question.category}</span>
            </>
          )}
        </div>

        <p className="font-serif text-xl leading-relaxed text-ink-primary">
          {question.original_text}
        </p>

        {question.tags && question.tags.length > 0 && (
          <div className="flex gap-2 mt-4">
            {question.tags.map((tag) => (
              <span key={tag} className="font-mono text-xs text-ink-tertiary bg-cream-200 px-2 py-1 rounded-sm">
                {tag}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Auto-answered — show answer with accept/reject */}
      {question.status === 'auto_answered' && (
        <div className="card-tufte card-elevated mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Automated Answer
          </h3>
          <div className="font-serif text-ink-primary leading-relaxed mb-6 whitespace-pre-wrap">
            {(question.gap_analysis as unknown as Record<string, unknown>)?.proposed_answer as string ||
             'An automated answer was provided for this question.'}
          </div>

          <hr className="my-4" />

          <div className="flex items-center gap-4">
            <button onClick={handleAcceptAuto} className="btn-primary">
              Accept Answer
            </button>
            <button
              onClick={() => setShowRejectForm(true)}
              className="btn-secondary"
            >
              Request Human Review
            </button>
          </div>

          {showRejectForm && (
            <div className="mt-4">
              <label className="label-tufte">Why isn't this answer sufficient?</label>
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                className="input-tufte w-full h-24 resize-none"
                placeholder="Help our experts understand what you need..."
              />
              <div className="flex gap-3 mt-3">
                <button
                  onClick={handleRejectAuto}
                  disabled={!rejectReason.trim()}
                  className="btn-primary disabled:opacity-50"
                >
                  Submit
                </button>
                <button
                  onClick={() => setShowRejectForm(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Expert answer */}
      {(question.status === 'answered' || question.status === 'resolved') && (
        <div className="card-tufte card-elevated mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Expert Answer
          </h3>
          <div className="font-serif text-ink-primary leading-relaxed whitespace-pre-wrap">
            {(question.gap_analysis as unknown as Record<string, unknown>)?.expert_answer as string ||
             'Your question has been answered by an expert.'}
          </div>

          {question.first_response_at && (
            <p className="mt-4 font-mono text-xs text-ink-muted">
              Answered {formatDate(question.first_response_at)}
            </p>
          )}

          {/* Feedback */}
          <hr className="my-4" />
          {feedbackSubmitted ? (
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-ink-tertiary">Your rating:</span>
              <div className="flex gap-1">
                {[1, 2, 3, 4, 5].map((star) => (
                  <span
                    key={star}
                    className={`text-lg ${star <= rating ? 'text-status-warning' : 'text-ink-muted'}`}
                  >
                    *
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <div>
              <p className="font-mono text-xs text-ink-tertiary mb-2">Rate this answer:</p>
              <div className="flex gap-2">
                {[1, 2, 3, 4, 5].map((value) => (
                  <button
                    key={value}
                    onClick={() => handleFeedback(value)}
                    className="w-8 h-8 rounded-sm border border-rule-light hover:border-loris-brown hover:text-loris-brown font-mono text-sm text-ink-secondary transition-colors"
                  >
                    {value}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Status messages for in-queue states */}
      {['expert_queue', 'in_progress', 'human_requested'].includes(question.status) && (
        <div className="card-tufte mb-8">
          <div className="text-center py-6">
            <p className="font-serif text-ink-secondary">
              {question.status === 'expert_queue'
                ? 'Your question is in the expert queue. Our team is working through questions in order of priority.'
                : question.status === 'in_progress'
                ? 'An expert is currently working on your question.'
                : 'Your request for human review has been received. An expert will respond soon.'}
            </p>
          </div>
        </div>
      )}

      {/* Timeline */}
      <div className="card-tufte">
        <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">Timeline</h3>
        <div className="space-y-3">
          <div className="flex gap-3">
            <span className="font-mono text-xs text-ink-muted w-36 shrink-0">{formatDate(question.created_at)}</span>
            <span className="font-serif text-sm text-ink-secondary">Question submitted</span>
          </div>
          {question.first_response_at && (
            <div className="flex gap-3">
              <span className="font-mono text-xs text-ink-muted w-36 shrink-0">{formatDate(question.first_response_at)}</span>
              <span className="font-serif text-sm text-ink-secondary">First response</span>
            </div>
          )}
          {question.resolved_at && (
            <div className="flex gap-3">
              <span className="font-mono text-xs text-ink-muted w-36 shrink-0">{formatDate(question.resolved_at)}</span>
              <span className="font-serif text-sm text-ink-secondary">Resolved</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
