import { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { questionsApi, Question } from '../../lib/api/questions'
import { knowledgeApi } from '../../lib/api/knowledge'
import { subdomainsApi, SubDomainItem } from '../../lib/api/subdomains'

export default function ExpertQuestionDetail() {
  const { questionId } = useParams<{ questionId: string }>()
  const navigate = useNavigate()
  const [question, setQuestion] = useState<Question | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Answer form
  const [answerContent, setAnswerContent] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [answerSubmitted, setAnswerSubmitted] = useState(false)

  // Post-answer actions
  const [showAddToKb, setShowAddToKb] = useState(false)
  const [kbCategory, setKbCategory] = useState('')
  const [kbDomain, setKbDomain] = useState('')

  // Reassignment
  const [subdomains, setSubdomains] = useState<SubDomainItem[]>([])
  const [showReassignment, setShowReassignment] = useState(false)
  const [reassignSubdomain, setReassignSubdomain] = useState('')
  const [reassignReason, setReassignReason] = useState('')
  const [isReassigning, setIsReassigning] = useState(false)
  const [reassignSuccess, setReassignSuccess] = useState('')

  useEffect(() => {
    if (questionId) loadQuestion()
    loadSubdomains()
  }, [questionId])

  const loadSubdomains = async () => {
    try {
      const result = await subdomainsApi.list(true)
      setSubdomains(result.items)
    } catch {
      // Sub-domains not available
    }
  }

  const loadQuestion = async () => {
    try {
      setIsLoading(true)
      const q = await questionsApi.get(questionId!)
      setQuestion(q)

      // Pre-populate answer from gap analysis if available
      const ga = q.gap_analysis as Record<string, unknown> | null
      if (ga) {
        // Check automation suggestion first
        const autoSuggestion = ga.automation_suggestion as Record<string, unknown> | undefined
        if (autoSuggestion?.suggested_answer) {
          setAnswerContent(autoSuggestion.suggested_answer as string)
        }
        // Check knowledge analysis
        const ka = ga.knowledge_analysis as Record<string, unknown> | undefined
        if (ka?.proposed_answer) {
          setAnswerContent(ka.proposed_answer as string)
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load question')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAssign = async () => {
    try {
      await questionsApi.assign(questionId!)
      await loadQuestion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to assign')
    }
  }

  const handleSubmitAnswer = async () => {
    if (!answerContent.trim()) return
    try {
      setIsSubmitting(true)
      await questionsApi.submitAnswer(questionId!, answerContent)
      setAnswerSubmitted(true)
      await loadQuestion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to submit answer')
    } finally {
      setIsSubmitting(false)
    }
  }

  const handleRequestClarification = async (message: string) => {
    try {
      await questionsApi.requestClarification(questionId!, message)
      await loadQuestion()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request clarification')
    }
  }

  const handleAddToKb = async () => {
    try {
      await knowledgeApi.createFromAnswer({
        question_id: questionId!,
        category: kbCategory || undefined,
        domain: kbDomain || undefined,
      })
      setShowAddToKb(false)
      setError('') // clear any previous error
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add to knowledge base')
    }
  }

  const handleRequestReassignment = async () => {
    if (!reassignSubdomain || !reassignReason.trim()) return
    setIsReassigning(true)
    try {
      await subdomainsApi.requestReassignment(questionId!, reassignSubdomain, reassignReason)
      setShowReassignment(false)
      setReassignSubdomain('')
      setReassignReason('')
      setReassignSuccess('Reassignment request submitted. An admin will review it.')
      setTimeout(() => setReassignSuccess(''), 5000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to request reassignment')
    } finally {
      setIsReassigning(false)
    }
  }

  const formatDate = (dateStr: string) => new Date(dateStr).toLocaleString()

  if (isLoading) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-ink-secondary">Loading...</p>
      </div>
    )
  }

  if (!question) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-status-error mb-4">{error || 'Question not found'}</p>
        <button onClick={() => navigate('/expert/queue')} className="btn-secondary">
          Back to Queue
        </button>
      </div>
    )
  }

  const ga = question.gap_analysis as Record<string, unknown> | null
  const knowledgeAnalysis = ga?.knowledge_analysis as Record<string, unknown> | undefined
  const automationSuggestion = ga?.automation_suggestion as Record<string, unknown> | undefined
  const isAnswered = ['answered', 'resolved', 'auto_answered'].includes(question.status)

  return (
    <div className="max-w-4xl">
      {/* Back link */}
      <button
        onClick={() => navigate('/expert/queue')}
        className="font-serif text-sm text-ink-secondary hover:text-ink-primary mb-6 block"
      >
        ← Back to Queue
      </button>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-6">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}
      {reassignSuccess && (
        <div className="p-3 bg-cream-200 border border-status-success rounded-sm mb-6">
          <p className="font-serif text-sm text-status-success">{reassignSuccess}</p>
        </div>
      )}

      {/* Question card */}
      <div className="card-tufte mb-6">
        <div className="flex items-center gap-3 mb-4">
          <span className={`status uppercase ${
            question.priority === 'urgent' ? 'text-status-error' :
            question.priority === 'high' ? 'text-status-warning' : 'text-ink-tertiary'
          }`}>
            {question.priority}
          </span>
          <span className="text-ink-muted">·</span>
          <span className="font-mono text-xs text-ink-secondary">
            {(() => {
              const sdId = (question as any).subdomain_id
              const sd = sdId ? subdomains.find(s => s.id === sdId) : null
              if (sd) {
                const aiFlag = (question as any).ai_classified_subdomain
                return <>{sd.name}{aiFlag && <span className="text-ink-tertiary ml-1" title="AI-classified">(AI)</span>}</>
              }
              return question.category || 'Uncategorized'
            })()}
          </span>
          <span className="text-ink-muted">·</span>
          <span className="font-mono text-xs text-ink-muted">{formatDate(question.created_at)}</span>
          <span className="text-ink-muted">·</span>
          <span className="font-mono text-xs text-ink-secondary">{question.status.replace(/_/g, ' ')}</span>
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

        {/* Assign button if not yet assigned */}
        {['expert_queue', 'human_requested', 'needs_clarification'].includes(question.status) && !question.assigned_to_id && (
          <div className="mt-4 flex gap-3">
            <button onClick={handleAssign} className="btn-primary">
              Assign to Me
            </button>
            {subdomains.length > 0 && (
              <button
                onClick={() => setShowReassignment(true)}
                className="btn-secondary"
              >
                Not My Sub-Domain
              </button>
            )}
          </div>
        )}

        {/* Also show reassignment for assigned questions */}
        {question.assigned_to_id && !isAnswered && subdomains.length > 0 && (
          <div className="mt-4">
            <button
              onClick={() => setShowReassignment(true)}
              className="font-serif text-sm text-ink-secondary hover:text-ink-primary"
            >
              Not my sub-domain — request reassignment
            </button>
          </div>
        )}
      </div>

      {/* Gap Analysis Panel */}
      {(knowledgeAnalysis || automationSuggestion) && (
        <div className="card-tufte card-elevated mb-6">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Gap Analysis
          </h3>

          {automationSuggestion && (
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs text-status-success">Automation Match</span>
                <span className="font-mono text-xs text-ink-muted">
                  ({Math.round((automationSuggestion.similarity as number || 0) * 100)}% confidence)
                </span>
              </div>
              <p className="font-serif text-sm text-ink-secondary leading-relaxed whitespace-pre-wrap">
                {String(automationSuggestion.suggested_answer || '')}
              </p>
            </div>
          )}

          {knowledgeAnalysis && (
            <div>
              {(knowledgeAnalysis.coverage_percentage as number) !== undefined && (
                <div className="flex items-center gap-3 mb-3">
                  <span className="font-mono text-xs text-ink-tertiary">Coverage:</span>
                  <span className="font-mono text-sm text-ink-primary">
                    {Math.round(knowledgeAnalysis.coverage_percentage as number)}%
                  </span>
                  <span className="font-mono text-xs text-ink-tertiary">Confidence:</span>
                  <span className="font-mono text-sm text-ink-primary">
                    {Math.round((knowledgeAnalysis.confidence_score as number || 0) * 100)}%
                  </span>
                </div>
              )}

              {(knowledgeAnalysis.relevant_knowledge as string[])?.length > 0 && (
                <div className="mb-3">
                  <span className="font-mono text-xs text-ink-tertiary">Relevant Knowledge:</span>
                  <ul className="mt-1 space-y-1">
                    {(knowledgeAnalysis.relevant_knowledge as string[]).map((item, i) => (
                      <li key={i} className="font-serif text-sm text-ink-secondary">— {item}</li>
                    ))}
                  </ul>
                </div>
              )}

              {(knowledgeAnalysis.identified_gaps as string[])?.length > 0 && (
                <div className="mb-3">
                  <span className="font-mono text-xs text-status-warning">Identified Gaps:</span>
                  <ul className="mt-1 space-y-1">
                    {(knowledgeAnalysis.identified_gaps as string[]).map((gap, i) => (
                      <li key={i} className="font-serif text-sm text-ink-secondary">— {gap}</li>
                    ))}
                  </ul>
                </div>
              )}

              {Boolean(knowledgeAnalysis.proposed_answer) && (
                <div>
                  <span className="font-mono text-xs text-ink-tertiary">Proposed Answer:</span>
                  <p className="mt-1 font-serif text-sm text-ink-primary leading-relaxed whitespace-pre-wrap">
                    {String(knowledgeAnalysis.proposed_answer)}
                  </p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Answer form (for non-answered questions) */}
      {!isAnswered && question.assigned_to_id && (
        <div className="card-tufte mb-6">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Your Answer
          </h3>
          <textarea
            value={answerContent}
            onChange={(e) => setAnswerContent(e.target.value)}
            className="input-tufte w-full h-48 resize-none mb-4"
            placeholder="Write your expert answer here..."
          />
          <div className="flex gap-3">
            <button
              onClick={handleSubmitAnswer}
              disabled={isSubmitting || !answerContent.trim()}
              className="btn-primary disabled:opacity-50"
            >
              {isSubmitting ? 'Submitting...' : 'Submit Answer'}
            </button>
            <button
              onClick={() => {
                const msg = prompt('Enter clarification request:')
                if (msg) handleRequestClarification(msg)
              }}
              className="btn-secondary"
            >
              Request Clarification
            </button>
          </div>
        </div>
      )}

      {/* Post-answer actions */}
      {(isAnswered || answerSubmitted) && (
        <div className="card-tufte mb-6">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Post-Answer Actions
          </h3>
          <div className="flex gap-3">
            <button
              onClick={() => setShowAddToKb(!showAddToKb)}
              className="btn-secondary"
            >
              Add to Knowledge Base
            </button>
            <Link
              to="/expert/knowledge"
              className="btn-secondary inline-block no-underline"
            >
              Create Automation Rule
            </Link>
          </div>

          {showAddToKb && (
            <div className="mt-4 p-4 bg-cream-200 rounded-sm">
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="label-tufte">Category</label>
                  <input
                    value={kbCategory}
                    onChange={(e) => setKbCategory(e.target.value)}
                    className="input-tufte w-full"
                    placeholder="e.g., Contracts"
                  />
                </div>
                <div>
                  <label className="label-tufte">Domain</label>
                  <input
                    value={kbDomain}
                    onChange={(e) => setKbDomain(e.target.value)}
                    className="input-tufte w-full"
                    placeholder="e.g., Corporate Law"
                  />
                </div>
              </div>
              <button onClick={handleAddToKb} className="btn-primary">
                Save to Knowledge Base
              </button>
            </div>
          )}
        </div>
      )}

      {/* Reassignment Modal */}
      {showReassignment && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-md border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-2">Request Reassignment</h2>
            <p className="font-serif text-sm text-ink-secondary mb-6">
              Suggest a different sub-domain for this question. An admin will review your request.
            </p>

            <div className="mb-4">
              <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">
                Suggested Sub-Domain
              </label>
              <select
                value={reassignSubdomain}
                onChange={(e) => setReassignSubdomain(e.target.value)}
                className="input-tufte w-full"
              >
                <option value="">Select a sub-domain...</option>
                {subdomains.map(sd => (
                  <option key={sd.id} value={sd.id}>{sd.name}</option>
                ))}
              </select>
            </div>

            <div className="mb-6">
              <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">
                Reason
              </label>
              <textarea
                value={reassignReason}
                onChange={(e) => setReassignReason(e.target.value)}
                className="input-tufte w-full"
                rows={3}
                placeholder="Why should this question be reassigned?"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-rule-light">
              <button
                onClick={() => { setShowReassignment(false); setReassignSubdomain(''); setReassignReason('') }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleRequestReassignment}
                disabled={isReassigning || !reassignSubdomain || !reassignReason.trim()}
                className="btn-primary disabled:opacity-50"
              >
                {isReassigning ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
