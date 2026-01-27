import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

export default function AskQuestionPage() {
  const [question, setQuestion] = useState('')
  const [category, setCategory] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const navigate = useNavigate()

  const categories = [
    'Contracts',
    'Employment',
    'Privacy & Data',
    'Intellectual Property',
    'Compliance',
    'Corporate',
    'Other',
  ]

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setIsSubmitting(true)

    try {
      const token = localStorage.getItem('access_token')
      const response = await fetch('/api/v1/questions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          text: question,
          category: category || null,
        }),
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
          <p className="mt-2 font-mono text-xs text-ink-tertiary">
            Tip: Include relevant context like jurisdiction, contract type, or specific circumstances.
          </p>
        </div>

        <div>
          <label htmlFor="category" className="label-tufte">
            Category (Optional)
          </label>
          <select
            id="category"
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="input-tufte w-full"
          >
            <option value="">Select a category...</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat}
              </option>
            ))}
          </select>
        </div>

        <hr />

        <div className="flex items-center gap-4">
          <button
            type="submit"
            disabled={isSubmitting || !question.trim()}
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
            If not, your question goes to our expert queue with AI-assisted analysis.
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
