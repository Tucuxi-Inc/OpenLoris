import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { subdomainsApi, SubDomainItem } from '../../lib/api/subdomains'
import { orgApi, OrgSettings } from '../../lib/api/org'

export default function AskQuestionPage() {
  const [question, setQuestion] = useState('')
  const [department, setDepartment] = useState('')
  const [subdomainId, setSubdomainId] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [subdomains, setSubdomains] = useState<SubDomainItem[]>([])
  const [orgSettings, setOrgSettings] = useState<OrgSettings | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadSubdomains()
    loadOrgSettings()
  }, [])

  const loadSubdomains = async () => {
    try {
      const result = await subdomainsApi.list(true)
      setSubdomains(result.items)
    } catch {
      // Fallback: sub-domains not available yet — submit without
    }
  }

  const loadOrgSettings = async () => {
    try {
      const result = await orgApi.getSettings()
      setOrgSettings(result)
    } catch {
      // Settings not available — department will be hidden
    }
  }

  const departments = orgSettings?.departments || []
  const requireDepartment = orgSettings?.require_department || false

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const token = localStorage.getItem('access_token')
      const body: Record<string, unknown> = { text: question }
      if (subdomainId) {
        body.subdomain_id = subdomainId
      }
      if (department) {
        body.department = department
      }

      const response = await fetch('/api/v1/questions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify(body),
      })

      if (response.ok) {
        navigate('/dashboard')
      }
    } catch (error) {
      console.error('Failed to submit question:', error)
    } finally {
      setIsSubmitting(false)
    }
  }

  const MIN_WORDS = 5
  const wordCount = question.trim().split(/\s+/).filter(Boolean).length
  const questionLongEnough = wordCount >= MIN_WORDS
  const departmentSatisfied = !requireDepartment || department
  const canSubmit = questionLongEnough && departmentSatisfied

  // Show hints only after the user has started interacting
  const questionTouched = question.trim().length > 0
  const showWordHint = questionTouched && !questionLongEnough

  return (
    <div className="max-w-2xl">
      {/* Page header */}
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">Ask a Question</h1>
        <p className="font-serif text-ink-secondary">
          Describe your legal question and our experts will provide a curated answer.
        </p>
      </div>

      {/* Question form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div>
          <label htmlFor="question" className="label-tufte">
            Your Question
          </label>
          <textarea
            id="question"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            className="input-tufte w-full h-40 resize-none"
            placeholder="What would you like to know? Be as specific as possible..."
            required
          />
          <div className="flex items-center justify-between mt-2">
            <p className="font-mono text-xs text-ink-tertiary">
              Tip: Include relevant context like jurisdiction, contract type, or specific circumstances.
            </p>
            <span className={`font-mono text-xs ${showWordHint ? 'text-status-warning' : 'text-ink-muted'}`}>
              {wordCount} / {MIN_WORDS} words min
            </span>
          </div>
          {showWordHint && (
            <p className="font-mono text-xs text-status-warning mt-1">
              Please provide more detail so our experts can give you a useful answer.
            </p>
          )}
        </div>

        {/* Department dropdown — shown when departments are configured */}
        {departments.length > 0 && (
          <div>
            <label htmlFor="department" className="label-tufte">
              Department{requireDepartment ? '' : ' (Optional)'}
            </label>
            <select
              id="department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              className="input-tufte w-full"
              required={requireDepartment}
            >
              <option value="">
                {requireDepartment ? 'Select your department...' : 'No department'}
              </option>
              {departments.map((dept) => (
                <option key={dept} value={dept}>
                  {dept}
                </option>
              ))}
            </select>
          </div>
        )}

        <div>
          <label htmlFor="subdomain" className="label-tufte">
            Sub-Domain (Optional)
          </label>
          <select
            id="subdomain"
            value={subdomainId}
            onChange={(e) => setSubdomainId(e.target.value)}
            className="input-tufte w-full"
          >
            <option value="">Not sure — let Loris classify it</option>
            {subdomains.map((sd) => (
              <option key={sd.id} value={sd.id}>
                {sd.name}
              </option>
            ))}
          </select>
          <p className="mt-1 font-mono text-[10px] text-ink-tertiary">
            If you leave this blank, Loris will route your question to the right experts automatically.
          </p>
        </div>

        <hr />

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting || !canSubmit}
            className="btn-primary disabled:opacity-50"
          >
            {isSubmitting ? 'Submitting...' : 'Submit Question'}
          </button>
          <button
            type="button"
            onClick={() => navigate('/dashboard')}
            className="btn-secondary"
          >
            Cancel
          </button>
          {!canSubmit && questionTouched && (
            <span className="font-mono text-xs text-ink-muted">
              {!questionLongEnough
                ? `Need at least ${MIN_WORDS} words`
                : !departmentSatisfied
                  ? 'Please select a department'
                  : ''}
            </span>
          )}
        </div>
      </form>

      {/* How it works */}
      <div className="mt-12 pt-8 border-t border-rule-light">
        <h3 className="text-lg text-ink-primary mb-4">How it works</h3>
        <ol className="space-y-3 font-serif text-ink-secondary">
          <li className="flex gap-3">
            <span className="font-mono text-xs text-ink-tertiary">1.</span>
            Submit your question with as much context as possible.
          </li>
          <li className="flex gap-3">
            <span className="font-mono text-xs text-ink-tertiary">2.</span>
            Our system checks if a similar question has been answered before.
          </li>
          <li className="flex gap-3">
            <span className="font-mono text-xs text-ink-tertiary">3.</span>
            If not, your question is routed to the right experts with AI-assisted analysis.
          </li>
          <li className="flex gap-3">
            <span className="font-mono text-xs text-ink-tertiary">4.</span>
            You'll be notified when your answer is ready.
          </li>
        </ol>
      </div>
    </div>
  )
}
