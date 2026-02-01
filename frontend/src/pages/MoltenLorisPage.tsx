import { useState, useEffect } from 'react'
import LorisAvatar from '../components/LorisAvatar'
import { moltenSyncApi, MoltenActivity, ActivityStats, SoulFileResponse } from '../lib/api/moltenSync'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, PieChart, Pie, Cell
} from 'recharts'

type TabId = 'setup' | 'activity' | 'stats'

export default function MoltenLorisPage() {
  const [activeTab, setActiveTab] = useState<TabId>('setup')

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-4 mb-8">
        <LorisAvatar mood="molten" size="lg" />
        <div>
          <h1 className="text-3xl font-serif text-ink-primary">MoltenLoris</h1>
          <p className="font-serif text-ink-secondary">
            Autonomous Slack-monitoring agent powered by your knowledge base
          </p>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-rule-light mb-6">
        <nav className="flex gap-8">
          {[
            { id: 'setup' as TabId, label: 'Setup' },
            { id: 'activity' as TabId, label: 'Activity' },
            { id: 'stats' as TabId, label: 'Stats' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`pb-3 font-mono text-sm border-b-2 transition-colors ${
                activeTab === tab.id
                  ? 'border-ink-accent text-ink-accent'
                  : 'border-transparent text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      {activeTab === 'setup' && <SetupTab />}
      {activeTab === 'activity' && <ActivityTab />}
      {activeTab === 'stats' && <StatsTab />}
    </div>
  )
}

// ── Setup Tab ────────────────────────────────────────────────────────────

function SetupTab() {
  const [soulFile, setSoulFile] = useState<SoulFileResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const generateSoul = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await moltenSyncApi.generateSoulFile()
      setSoulFile(result)
    } catch (err) {
      setError('Failed to generate SOUL file')
    } finally {
      setLoading(false)
    }
  }

  const copyToClipboard = async () => {
    if (!soulFile) return
    try {
      await navigator.clipboard.writeText(soulFile.soul_content)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      // Fallback for browsers without clipboard API
      const textarea = document.createElement('textarea')
      textarea.value = soulFile.soul_content
      document.body.appendChild(textarea)
      textarea.select()
      document.execCommand('copy')
      document.body.removeChild(textarea)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  return (
    <div className="space-y-8">
      {/* SOUL File Generation */}
      <section className="border border-rule-light p-6">
        <h2 className="text-xl font-serif text-ink-primary mb-4">SOUL File Generation</h2>
        <p className="font-serif text-ink-secondary mb-4">
          Generate a SOUL (Semantic Operational Understanding Layer) configuration file that
          configures MoltenLoris with your organization's knowledge base and answering guidelines.
        </p>

        <button
          onClick={generateSoul}
          disabled={loading}
          className="px-4 py-2 bg-ink-accent text-bg-primary font-mono text-sm hover:bg-ink-accent/90 disabled:opacity-50 transition-colors"
        >
          {loading ? 'Generating...' : 'Generate SOUL File'}
        </button>

        {error && (
          <p className="mt-4 text-ink-error font-mono text-sm">{error}</p>
        )}

        {soulFile && (
          <div className="mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="font-mono text-xs text-ink-tertiary">
                Generated for {soulFile.organization_name} at{' '}
                {new Date(soulFile.generated_at).toLocaleString()}
              </span>
              <button
                onClick={copyToClipboard}
                className="px-3 py-1 border border-ink-accent text-ink-accent font-mono text-xs hover:bg-ink-accent hover:text-bg-primary transition-colors"
              >
                {copied ? 'Copied!' : 'Copy to Clipboard'}
              </button>
            </div>

            {/* Stats summary */}
            <div className="flex gap-4 mb-4 text-sm font-mono">
              <span className="text-ink-secondary">
                Facts: <span className="text-ink-primary">{soulFile.stats.total_facts}</span>
              </span>
              <span className="text-ink-secondary">
                Rules: <span className="text-ink-primary">{soulFile.stats.active_rules}</span>
              </span>
              <span className="text-ink-secondary">
                Sub-domains: <span className="text-ink-primary">{soulFile.stats.active_subdomains}</span>
              </span>
            </div>

            <pre className="bg-bg-secondary border border-rule-light p-4 overflow-auto max-h-96 font-mono text-xs text-ink-secondary whitespace-pre-wrap">
              {soulFile.soul_content}
            </pre>
          </div>
        )}
      </section>

      {/* Setup Guide */}
      <section className="border border-rule-light p-6">
        <h2 className="text-xl font-serif text-ink-primary mb-4">Setup Guide</h2>
        <div className="space-y-4 font-serif text-ink-secondary">
          <p>
            MoltenLoris requires a separate Claude Code instance running with Slack access.
            Follow these steps to set up:
          </p>
          <ol className="list-decimal list-inside space-y-2 ml-4">
            <li>Install Claude Code and configure Slack MCP integration</li>
            <li>Generate your SOUL file above and save it to your Claude Code project</li>
            <li>Configure GDrive sync in Settings to share your knowledge base</li>
            <li>Start MoltenLoris with the channel monitoring command</li>
          </ol>
        </div>

        <a
          href="https://github.com/Tucuxi-Inc/Loris/blob/main/docs/loris-planning/MOLTENLORIS-SETUP-GUIDE.md"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 mt-4 px-4 py-2 border border-ink-accent text-ink-accent font-mono text-sm hover:bg-ink-accent hover:text-bg-primary transition-colors"
        >
          View Full Setup Guide
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </section>

      {/* Key Features */}
      <section className="border border-rule-light p-6">
        <h2 className="text-xl font-serif text-ink-primary mb-4">Key Features</h2>
        <ul className="grid grid-cols-2 gap-4">
          {[
            'Slack channel monitoring',
            'Proactive question detection',
            'Knowledge base integration',
            'Expert escalation when uncertain',
            'Usage analytics and insights',
            'Expert correction feedback loop',
          ].map((feature) => (
            <li key={feature} className="flex gap-2 font-serif text-sm text-ink-secondary">
              <span className="text-ink-muted">-</span>
              {feature}
            </li>
          ))}
        </ul>
      </section>
    </div>
  )
}

// ── Activity Tab ─────────────────────────────────────────────────────────

function ActivityTab() {
  const [activities, setActivities] = useState<MoltenActivity[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [offset, setOffset] = useState(0)
  const [filter, setFilter] = useState<'all' | 'corrected' | 'needs_review'>('all')
  const [selectedActivity, setSelectedActivity] = useState<MoltenActivity | null>(null)
  const limit = 20

  const loadActivities = async () => {
    setLoading(true)
    setError(null)
    try {
      const result = await moltenSyncApi.listActivities({
        limit,
        offset,
        corrected_only: filter === 'corrected',
        needs_review: filter === 'needs_review',
      })
      setActivities(result.activities)
      setTotal(result.total)
    } catch (err) {
      setError('Failed to load activities')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadActivities()
  }, [offset, filter])

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  const getConfidenceBadge = (score: number) => {
    if (score >= 0.8) return { color: 'text-ink-success', label: 'High' }
    if (score >= 0.6) return { color: 'text-ink-warning', label: 'Medium' }
    return { color: 'text-ink-error', label: 'Low' }
  }

  return (
    <div className="space-y-6">
      {/* Filters */}
      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-ink-tertiary uppercase">Filter:</span>
        {[
          { id: 'all' as const, label: 'All' },
          { id: 'corrected' as const, label: 'Corrected' },
          { id: 'needs_review' as const, label: 'Needs Review' },
        ].map((f) => (
          <button
            key={f.id}
            onClick={() => { setFilter(f.id); setOffset(0) }}
            className={`px-3 py-1 font-mono text-xs border transition-colors ${
              filter === f.id
                ? 'border-ink-accent bg-ink-accent text-bg-primary'
                : 'border-rule-light text-ink-secondary hover:border-ink-accent'
            }`}
          >
            {f.label}
          </button>
        ))}
        <span className="ml-auto font-mono text-xs text-ink-tertiary">
          {total} total
        </span>
      </div>

      {/* Activity Table */}
      {loading ? (
        <div className="text-center py-12 font-mono text-ink-tertiary">Loading...</div>
      ) : error ? (
        <div className="text-center py-12 text-ink-error font-mono">{error}</div>
      ) : activities.length === 0 ? (
        <div className="text-center py-12 border border-rule-light">
          <LorisAvatar mood="thinking" size="lg" className="mx-auto mb-4" />
          <p className="font-serif text-ink-secondary">No activity yet</p>
          <p className="font-mono text-xs text-ink-tertiary mt-2">
            MoltenLoris hasn't answered any questions in Slack
          </p>
        </div>
      ) : (
        <>
          <div className="border border-rule-light">
            <table className="w-full">
              <thead>
                <tr className="border-b border-rule-light bg-bg-secondary">
                  <th className="text-left p-3 font-mono text-xs text-ink-tertiary uppercase">Channel</th>
                  <th className="text-left p-3 font-mono text-xs text-ink-tertiary uppercase">Question</th>
                  <th className="text-left p-3 font-mono text-xs text-ink-tertiary uppercase">Confidence</th>
                  <th className="text-left p-3 font-mono text-xs text-ink-tertiary uppercase">Status</th>
                  <th className="text-left p-3 font-mono text-xs text-ink-tertiary uppercase">Time</th>
                </tr>
              </thead>
              <tbody>
                {activities.map((activity) => {
                  const confidence = getConfidenceBadge(activity.confidence_score)
                  return (
                    <tr
                      key={activity.id}
                      onClick={() => setSelectedActivity(activity)}
                      className="border-b border-rule-light hover:bg-bg-secondary cursor-pointer transition-colors"
                    >
                      <td className="p-3 font-mono text-sm text-ink-primary">
                        #{activity.channel_name}
                      </td>
                      <td className="p-3 font-serif text-sm text-ink-secondary max-w-md truncate">
                        {activity.question_text.slice(0, 80)}
                        {activity.question_text.length > 80 && '...'}
                      </td>
                      <td className="p-3">
                        <span className={`font-mono text-xs ${confidence.color}`}>
                          {(activity.confidence_score * 100).toFixed(0)}% ({confidence.label})
                        </span>
                      </td>
                      <td className="p-3">
                        {activity.was_corrected ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink-warning/10 text-ink-warning font-mono text-xs">
                            Corrected
                          </span>
                        ) : activity.confidence_score < 0.6 ? (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-ink-error/10 text-ink-error font-mono text-xs">
                            Needs Review
                          </span>
                        ) : (
                          <span className="font-mono text-xs text-ink-tertiary">-</span>
                        )}
                      </td>
                      <td className="p-3 font-mono text-xs text-ink-tertiary">
                        {formatDate(activity.created_at)}
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {total > limit && (
            <div className="flex items-center justify-center gap-4">
              <button
                onClick={() => setOffset(Math.max(0, offset - limit))}
                disabled={offset === 0}
                className="px-3 py-1 font-mono text-xs border border-rule-light text-ink-secondary hover:border-ink-accent disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Previous
              </button>
              <span className="font-mono text-xs text-ink-tertiary">
                {offset + 1}-{Math.min(offset + limit, total)} of {total}
              </span>
              <button
                onClick={() => setOffset(offset + limit)}
                disabled={offset + limit >= total}
                className="px-3 py-1 font-mono text-xs border border-rule-light text-ink-secondary hover:border-ink-accent disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      {/* Activity Detail Modal */}
      {selectedActivity && (
        <ActivityDetailModal
          activity={selectedActivity}
          onClose={() => setSelectedActivity(null)}
          onCorrected={loadActivities}
        />
      )}
    </div>
  )
}

// ── Activity Detail Modal ────────────────────────────────────────────────

function ActivityDetailModal({
  activity,
  onClose,
  onCorrected,
}: {
  activity: MoltenActivity
  onClose: () => void
  onCorrected: () => void
}) {
  const [correcting, setCorrecting] = useState(false)
  const [correctionText, setCorrectionText] = useState('')
  const [correctionReason, setCorrectionReason] = useState('')
  const [createFact, setCreateFact] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleCorrect = async () => {
    if (!correctionText.trim() || !correctionReason.trim()) {
      setError('Please provide both correction text and reason')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      await moltenSyncApi.correctActivity(activity.id, {
        correction_text: correctionText,
        correction_reason: correctionReason,
        create_fact: createFact,
      })
      onCorrected()
      onClose()
    } catch (err) {
      setError('Failed to submit correction')
    } finally {
      setSubmitting(false)
    }
  }

  const reasons = [
    'Factually incorrect',
    'Outdated information',
    'Missing context',
    'Wrong tone',
    'Incomplete answer',
    'Other',
  ]

  return (
    <div className="fixed inset-0 bg-ink-primary/50 flex items-center justify-center p-4 z-50">
      <div className="bg-bg-primary border border-rule-light max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-rule-light">
          <div>
            <h3 className="font-serif text-lg text-ink-primary">Activity Detail</h3>
            <span className="font-mono text-xs text-ink-tertiary">#{activity.channel_name}</span>
          </div>
          <button
            onClick={onClose}
            className="p-1 text-ink-tertiary hover:text-ink-primary"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {/* Question */}
          <div>
            <label className="font-mono text-xs text-ink-tertiary uppercase block mb-1">Question</label>
            <p className="font-serif text-ink-primary bg-bg-secondary p-3 border border-rule-light">
              {activity.question_text}
            </p>
          </div>

          {/* Original Answer */}
          <div>
            <label className="font-mono text-xs text-ink-tertiary uppercase block mb-1">
              MoltenLoris Answer (Confidence: {(activity.confidence_score * 100).toFixed(0)}%)
            </label>
            <p className="font-serif text-ink-secondary bg-bg-secondary p-3 border border-rule-light">
              {activity.answer_text}
            </p>
          </div>

          {/* Correction Display or Form */}
          {activity.was_corrected ? (
            <div className="border border-ink-warning/30 bg-ink-warning/5 p-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-mono text-xs text-ink-warning uppercase">Corrected</span>
                {activity.corrected_by && (
                  <span className="font-mono text-xs text-ink-tertiary">
                    by {activity.corrected_by.name}
                  </span>
                )}
              </div>
              <p className="font-serif text-ink-primary mb-2">{activity.correction_text}</p>
              <p className="font-mono text-xs text-ink-tertiary">
                Reason: {activity.correction_reason}
              </p>
            </div>
          ) : correcting ? (
            <div className="border border-rule-light p-4 space-y-4">
              <div>
                <label className="font-mono text-xs text-ink-tertiary uppercase block mb-1">
                  Corrected Answer
                </label>
                <textarea
                  value={correctionText}
                  onChange={(e) => setCorrectionText(e.target.value)}
                  className="w-full p-3 border border-rule-light font-serif text-ink-primary bg-bg-primary focus:border-ink-accent focus:outline-none"
                  rows={4}
                  placeholder="Enter the correct answer..."
                />
              </div>

              <div>
                <label className="font-mono text-xs text-ink-tertiary uppercase block mb-1">
                  Reason for Correction
                </label>
                <select
                  value={correctionReason}
                  onChange={(e) => setCorrectionReason(e.target.value)}
                  className="w-full p-2 border border-rule-light font-mono text-sm text-ink-primary bg-bg-primary focus:border-ink-accent focus:outline-none"
                >
                  <option value="">Select a reason...</option>
                  {reasons.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
              </div>

              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={createFact}
                  onChange={(e) => setCreateFact(e.target.checked)}
                  className="rounded border-rule-light"
                />
                <span className="font-mono text-xs text-ink-secondary">
                  Create knowledge fact from correction
                </span>
              </label>

              {error && <p className="text-ink-error font-mono text-xs">{error}</p>}

              <div className="flex gap-2">
                <button
                  onClick={handleCorrect}
                  disabled={submitting}
                  className="px-4 py-2 bg-ink-accent text-bg-primary font-mono text-sm hover:bg-ink-accent/90 disabled:opacity-50"
                >
                  {submitting ? 'Submitting...' : 'Submit Correction'}
                </button>
                <button
                  onClick={() => setCorrecting(false)}
                  className="px-4 py-2 border border-rule-light text-ink-secondary font-mono text-sm hover:border-ink-accent"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => setCorrecting(true)}
              className="px-4 py-2 border border-ink-accent text-ink-accent font-mono text-sm hover:bg-ink-accent hover:text-bg-primary transition-colors"
            >
              Correct This Answer
            </button>
          )}

          {/* Metadata */}
          <div className="pt-4 border-t border-rule-light">
            <div className="grid grid-cols-2 gap-2 font-mono text-xs text-ink-tertiary">
              {activity.user_name && (
                <div>Asked by: {activity.user_name}</div>
              )}
              <div>Time: {new Date(activity.created_at).toLocaleString()}</div>
              {activity.thread_ts && (
                <div>Thread: {activity.thread_ts}</div>
              )}
              {activity.source_facts.length > 0 && (
                <div>Source facts: {activity.source_facts.length}</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

// ── Stats Tab ────────────────────────────────────────────────────────────

const CHART_COLORS = ['#8B5A2B', '#2E5E4E', '#8B6914', '#8B2E2E', '#4A5568']

function StatsTab() {
  const [stats, setStats] = useState<ActivityStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState('30d')

  useEffect(() => {
    const loadStats = async () => {
      setLoading(true)
      setError(null)
      try {
        const result = await moltenSyncApi.getActivityStats(period)
        setStats(result)
      } catch (err) {
        setError('Failed to load statistics')
      } finally {
        setLoading(false)
      }
    }
    loadStats()
  }, [period])

  if (loading) {
    return <div className="text-center py-12 font-mono text-ink-tertiary">Loading...</div>
  }

  if (error) {
    return <div className="text-center py-12 text-ink-error font-mono">{error}</div>
  }

  if (!stats || stats.total_answers === 0) {
    return (
      <div className="text-center py-12 border border-rule-light">
        <LorisAvatar mood="thinking" size="lg" className="mx-auto mb-4" />
        <p className="font-serif text-ink-secondary">No activity data yet</p>
        <p className="font-mono text-xs text-ink-tertiary mt-2">
          Statistics will appear once MoltenLoris starts answering questions
        </p>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      {/* Period Selector */}
      <div className="flex items-center gap-4">
        <span className="font-mono text-xs text-ink-tertiary uppercase">Period:</span>
        {['7d', '30d', '90d', 'all'].map((p) => (
          <button
            key={p}
            onClick={() => setPeriod(p)}
            className={`px-3 py-1 font-mono text-xs border transition-colors ${
              period === p
                ? 'border-ink-accent bg-ink-accent text-bg-primary'
                : 'border-rule-light text-ink-secondary hover:border-ink-accent'
            }`}
          >
            {p === 'all' ? 'All Time' : p.replace('d', ' Days')}
          </button>
        ))}
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-4 gap-4">
        <div className="border border-rule-light p-4">
          <div className="font-mono text-xs text-ink-tertiary uppercase mb-1">Total Answers</div>
          <div className="font-serif text-2xl text-ink-primary">{stats.total_answers}</div>
        </div>
        <div className="border border-rule-light p-4">
          <div className="font-mono text-xs text-ink-tertiary uppercase mb-1">Avg Confidence</div>
          <div className="font-serif text-2xl text-ink-primary">
            {(stats.avg_confidence * 100).toFixed(1)}%
          </div>
        </div>
        <div className="border border-rule-light p-4">
          <div className="font-mono text-xs text-ink-tertiary uppercase mb-1">Correction Rate</div>
          <div className="font-serif text-2xl text-ink-warning">
            {(stats.correction_rate * 100).toFixed(1)}%
          </div>
        </div>
        <div className="border border-rule-light p-4">
          <div className="font-mono text-xs text-ink-tertiary uppercase mb-1">High Confidence</div>
          <div className="font-serif text-2xl text-ink-success">
            {stats.high_confidence_count}
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Daily Trend */}
        <div className="border border-rule-light p-4">
          <h3 className="font-mono text-xs text-ink-tertiary uppercase mb-4">Daily Activity</h3>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={stats.daily_trend}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E4E0" />
              <XAxis
                dataKey="date"
                tick={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }}
                tickFormatter={(v) => v.slice(5)}
              />
              <YAxis tick={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip
                contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              />
              <Line
                type="monotone"
                dataKey="count"
                stroke="#8B5A2B"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Confidence Distribution */}
        <div className="border border-rule-light p-4">
          <h3 className="font-mono text-xs text-ink-tertiary uppercase mb-4">Confidence Distribution</h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={stats.confidence_distribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E5E4E0" />
              <XAxis
                dataKey="range"
                tick={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }}
              />
              <YAxis tick={{ fontSize: 10, fontFamily: 'IBM Plex Mono' }} />
              <Tooltip
                contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }}
              />
              <Bar dataKey="count" fill="#8B5A2B" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Top Channels */}
      <div className="border border-rule-light p-4">
        <h3 className="font-mono text-xs text-ink-tertiary uppercase mb-4">Top Channels</h3>
        {stats.top_channels.length === 0 ? (
          <p className="font-mono text-xs text-ink-tertiary">No channel data</p>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              {stats.top_channels.map((channel, i) => (
                <div key={channel.channel} className="flex items-center gap-2">
                  <span className="font-mono text-xs text-ink-tertiary w-4">{i + 1}.</span>
                  <span className="font-mono text-sm text-ink-primary flex-1">
                    #{channel.channel}
                  </span>
                  <span className="font-mono text-xs text-ink-secondary">
                    {channel.count} answers
                  </span>
                </div>
              ))}
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <PieChart>
                <Pie
                  data={stats.top_channels.slice(0, 5)}
                  dataKey="count"
                  nameKey="channel"
                  cx="50%"
                  cy="50%"
                  innerRadius={40}
                  outerRadius={80}
                  paddingAngle={2}
                >
                  {stats.top_channels.slice(0, 5).map((_, index) => (
                    <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{ fontFamily: 'IBM Plex Mono', fontSize: 11 }}
                  formatter={(value, name) => [value, `#${name}`]}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  )
}
