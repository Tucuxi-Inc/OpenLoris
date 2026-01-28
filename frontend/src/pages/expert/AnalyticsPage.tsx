import { useState, useEffect } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, CartesianGrid, Legend,
} from 'recharts'
import {
  analyticsApi,
  OverviewData,
  QuestionTrendsData,
  AutomationPerformanceData,
  KnowledgeCoverageData,
} from '../../lib/api/analytics'

type Period = '7d' | '30d' | '90d' | 'all'
type Tab = 'overview' | 'questions' | 'automation' | 'knowledge'

const PERIODS: { value: Period; label: string }[] = [
  { value: '7d', label: '7 days' },
  { value: '30d', label: '30 days' },
  { value: '90d', label: '90 days' },
  { value: 'all', label: 'All time' },
]

const TABS: { value: Tab; label: string }[] = [
  { value: 'overview', label: 'Overview' },
  { value: 'questions', label: 'Questions' },
  { value: 'automation', label: 'Automation' },
  { value: 'knowledge', label: 'Knowledge' },
]

// Tufte palette
const COLORS = {
  brown: '#8B5A2B',
  green: '#2E5E4E',
  ochre: '#8B6914',
  burgundy: '#8B2E2E',
  grid: '#E5E4E0',
  cream: '#FAF9F6',
}

const tooltipStyle = {
  contentStyle: {
    backgroundColor: COLORS.cream,
    border: `1px solid ${COLORS.grid}`,
    borderRadius: 2,
    fontFamily: 'Georgia, serif',
    fontSize: 13,
  },
}

function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  const h = Math.floor(seconds / 3600)
  const m = Math.round((seconds % 3600) / 60)
  return m > 0 ? `${h}h ${m}m` : `${h}h`
}

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return `${d.getMonth() + 1}/${d.getDate()}`
}

export default function AnalyticsPage() {
  const [period, setPeriod] = useState<Period>('30d')
  const [tab, setTab] = useState<Tab>('overview')
  const [isLoading, setIsLoading] = useState(true)

  const [overview, setOverview] = useState<OverviewData | null>(null)
  const [trends, setTrends] = useState<QuestionTrendsData | null>(null)
  const [automation, setAutomation] = useState<AutomationPerformanceData | null>(null)
  const [knowledge, setKnowledge] = useState<KnowledgeCoverageData | null>(null)

  useEffect(() => {
    loadData()
  }, [period])

  const loadData = async () => {
    setIsLoading(true)
    try {
      const results = await Promise.allSettled([
        analyticsApi.getOverview(period),
        analyticsApi.getQuestionTrends(period),
        analyticsApi.getAutomationPerformance(period),
        analyticsApi.getKnowledgeCoverage(),
      ])
      if (results[0].status === 'fulfilled') setOverview(results[0].value)
      if (results[1].status === 'fulfilled') setTrends(results[1].value)
      if (results[2].status === 'fulfilled') setAutomation(results[2].value)
      if (results[3].status === 'fulfilled') setKnowledge(results[3].value)
    } catch (err) {
      console.error('Analytics load error:', err)
    } finally {
      setIsLoading(false)
    }
  }

  if (isLoading && !overview) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-ink-secondary">Loading analytics...</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-3xl text-ink-primary mb-2">Analytics</h1>
        <p className="font-serif text-ink-secondary">
          Performance metrics and trends across your organization.
        </p>
      </div>

      {/* Period selector + Tabs */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex gap-1">
          {TABS.map((t) => (
            <button
              key={t.value}
              onClick={() => setTab(t.value)}
              className={`px-3 py-1.5 font-serif text-sm border-b-2 transition-colors ${
                tab === t.value
                  ? 'border-loris-brown text-loris-brown'
                  : 'border-transparent text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
        <div className="flex gap-1">
          {PERIODS.map((p) => (
            <button
              key={p.value}
              onClick={() => setPeriod(p.value)}
              className={`px-3 py-1 font-mono text-xs rounded-sm transition-colors ${
                period === p.value
                  ? 'bg-loris-brown text-white'
                  : 'text-ink-secondary hover:text-ink-primary'
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>

      {/* Tab content */}
      {tab === 'overview' && <OverviewTab overview={overview} trends={trends} />}
      {tab === 'questions' && <QuestionsTab trends={trends} />}
      {tab === 'automation' && <AutomationTab automation={automation} />}
      {tab === 'knowledge' && <KnowledgeTab knowledge={knowledge} />}
    </div>
  )
}

// ── Overview Tab ─────────────────────────────────────────────────────

function OverviewTab({
  overview,
  trends,
}: {
  overview: OverviewData | null
  trends: QuestionTrendsData | null
}) {
  if (!overview) return <EmptyState />

  const trendPct =
    overview.prev_period_question_count > 0
      ? Math.round(
          ((overview.period_question_count - overview.prev_period_question_count) /
            overview.prev_period_question_count) *
            100
        )
      : null

  return (
    <div>
      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <KPICard
          label="Total Questions"
          value={overview.total_questions}
          trend={trendPct}
          sub={`${overview.period_question_count} this period`}
        />
        <KPICard
          label="Automation Rate"
          value={`${overview.automation_rate}%`}
        />
        <KPICard
          label="Avg Response Time"
          value={formatDuration(overview.avg_response_time_seconds)}
        />
        <KPICard
          label="Avg Satisfaction"
          value={overview.avg_satisfaction !== null ? `${overview.avg_satisfaction}/5` : '—'}
        />
      </div>

      {/* Volume chart */}
      {trends && trends.daily_volumes.length > 0 && (
        <div className="card-tufte mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Question Volume
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={trends.daily_volumes}>
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={{ stroke: COLORS.grid }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip {...tooltipStyle} labelFormatter={(v) => `Date: ${v}`} />
              <Area
                type="monotone"
                dataKey="total"
                stroke={COLORS.brown}
                fill={COLORS.brown}
                fillOpacity={0.1}
                strokeWidth={2}
                name="Total"
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Status + Priority side by side */}
      {trends && (
        <div className="grid grid-cols-2 gap-8">
          <DistributionCard
            title="By Status"
            data={trends.status_distribution}
            color={COLORS.brown}
          />
          <DistributionCard
            title="By Priority"
            data={trends.priority_distribution}
            color={COLORS.green}
          />
        </div>
      )}
    </div>
  )
}

// ── Questions Tab ────────────────────────────────────────────────────

function QuestionsTab({ trends }: { trends: QuestionTrendsData | null }) {
  if (!trends) return <EmptyState />

  return (
    <div>
      {/* Volume chart */}
      {trends.daily_volumes.length > 0 ? (
        <div className="card-tufte mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Daily Volume — Auto-answered vs Expert-answered
          </h3>
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={trends.daily_volumes}>
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={{ stroke: COLORS.grid }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip {...tooltipStyle} labelFormatter={(v) => `Date: ${v}`} />
              <Legend
                wrapperStyle={{ fontFamily: 'Georgia', fontSize: 12 }}
              />
              <Bar dataKey="auto_answered" stackId="a" fill={COLORS.green} name="Auto-answered" />
              <Bar dataKey="expert_answered" stackId="a" fill={COLORS.brown} name="Expert-answered" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="card-tufte text-center py-8 mb-8">
          <p className="font-serif text-ink-secondary">No question data for this period.</p>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        <DistributionCard
          title="Status Distribution"
          data={trends.status_distribution}
          color={COLORS.brown}
        />
        <DistributionCard
          title="Priority Distribution"
          data={trends.priority_distribution}
          color={COLORS.green}
        />
      </div>
    </div>
  )
}

// ── Automation Tab ───────────────────────────────────────────────────

function AutomationTab({
  automation,
}: {
  automation: AutomationPerformanceData | null
}) {
  if (!automation) return <EmptyState />

  return (
    <div>
      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <KPICard label="Total Triggers" value={automation.total_triggers} />
        <KPICard label="Accepted" value={automation.total_accepted} />
        <KPICard label="Rejected" value={automation.total_rejected} />
        <KPICard
          label="Acceptance Rate"
          value={
            automation.overall_acceptance_rate !== null
              ? `${automation.overall_acceptance_rate}%`
              : '—'
          }
        />
      </div>

      {/* Daily trend */}
      {automation.daily_trend.length > 0 && (
        <div className="card-tufte mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Daily Automation Activity
          </h3>
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={automation.daily_trend}>
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" vertical={false} />
              <XAxis
                dataKey="date"
                tickFormatter={formatDate}
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={{ stroke: COLORS.grid }}
                tickLine={false}
              />
              <YAxis
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip {...tooltipStyle} labelFormatter={(v) => `Date: ${v}`} />
              <Legend wrapperStyle={{ fontFamily: 'Georgia', fontSize: 12 }} />
              <Bar dataKey="accepted" stackId="a" fill={COLORS.green} name="Accepted" />
              <Bar dataKey="rejected" stackId="a" fill={COLORS.burgundy} name="Rejected" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Rules table */}
      {automation.rules.length > 0 && (
        <div className="card-tufte">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Rule Performance
          </h3>
          <table className="w-full">
            <thead>
              <tr className="border-b border-rule-light">
                <th className="text-left font-mono text-xs text-ink-tertiary py-2 pr-4">Rule</th>
                <th className="text-right font-mono text-xs text-ink-tertiary py-2 px-3">Triggered</th>
                <th className="text-right font-mono text-xs text-ink-tertiary py-2 px-3">Accepted</th>
                <th className="text-right font-mono text-xs text-ink-tertiary py-2 px-3">Rejected</th>
                <th className="text-right font-mono text-xs text-ink-tertiary py-2 px-3">Rate</th>
                <th className="text-right font-mono text-xs text-ink-tertiary py-2 pl-3">Status</th>
              </tr>
            </thead>
            <tbody>
              {automation.rules.map((rule) => (
                <tr key={rule.rule_id} className="border-b border-rule-light last:border-0">
                  <td className="font-serif text-sm text-ink-primary py-2 pr-4">{rule.name}</td>
                  <td className="text-right font-mono text-sm text-ink-primary py-2 px-3">
                    {rule.times_triggered}
                  </td>
                  <td className="text-right font-mono text-sm text-status-success py-2 px-3">
                    {rule.times_accepted}
                  </td>
                  <td className="text-right font-mono text-sm text-status-error py-2 px-3">
                    {rule.times_rejected}
                  </td>
                  <td className="text-right font-mono text-sm text-ink-primary py-2 px-3">
                    {rule.acceptance_rate !== null ? `${rule.acceptance_rate}%` : '—'}
                  </td>
                  <td className="text-right font-mono text-xs py-2 pl-3">
                    <span className={rule.is_enabled ? 'text-status-success' : 'text-ink-muted'}>
                      {rule.is_enabled ? 'Active' : 'Disabled'}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {automation.rules.length === 0 && automation.daily_trend.length === 0 && (
        <div className="card-tufte text-center py-8">
          <p className="font-serif text-ink-secondary">No automation data for this period.</p>
        </div>
      )}
    </div>
  )
}

// ── Knowledge Tab ────────────────────────────────────────────────────

function KnowledgeTab({
  knowledge,
}: {
  knowledge: KnowledgeCoverageData | null
}) {
  if (!knowledge) return <EmptyState />

  const tierData = Object.entries(knowledge.by_tier).map(([tier, count]) => ({
    tier: tier.replace('tier_', 'Tier ').toUpperCase(),
    count,
  }))

  return (
    <div>
      {/* KPI cards */}
      <div className="grid grid-cols-4 gap-6 mb-8">
        <KPICard label="Total Facts" value={knowledge.total_facts} />
        <KPICard label="Expiring Soon" value={knowledge.expiring_soon} />
        <KPICard label="Added (7 days)" value={knowledge.recently_added} />
        <KPICard
          label="Avg Confidence"
          value={knowledge.avg_confidence !== null ? `${knowledge.avg_confidence}` : '—'}
        />
      </div>

      {/* Tier chart */}
      {tierData.length > 0 ? (
        <div className="card-tufte mb-8">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Facts by Tier
          </h3>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={tierData} layout="vertical">
              <CartesianGrid stroke={COLORS.grid} strokeDasharray="3 3" horizontal={false} />
              <XAxis
                type="number"
                tick={{ fontFamily: 'Georgia', fontSize: 11, fill: '#666' }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="tier"
                tick={{ fontFamily: 'Georgia', fontSize: 12, fill: '#1A1A1A' }}
                axisLine={false}
                tickLine={false}
                width={80}
              />
              <Tooltip {...tooltipStyle} />
              <Bar dataKey="count" fill={COLORS.brown} name="Facts" barSize={20} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <div className="card-tufte text-center py-8">
          <p className="font-serif text-ink-secondary">No knowledge facts in the database yet.</p>
        </div>
      )}
    </div>
  )
}

// ── Shared components ────────────────────────────────────────────────

function KPICard({
  label,
  value,
  trend,
  sub,
}: {
  label: string
  value: string | number
  trend?: number | null
  sub?: string
}) {
  return (
    <div className="card-tufte text-center">
      <div className="metric-value">
        {value}
        {trend !== undefined && trend !== null && (
          <span
            className={`ml-2 text-sm font-mono ${
              trend >= 0 ? 'text-status-success' : 'text-status-error'
            }`}
          >
            {trend >= 0 ? '+' : ''}
            {trend}%
          </span>
        )}
      </div>
      <div className="metric-label">{label}</div>
      {sub && <div className="font-mono text-[10px] text-ink-muted mt-1">{sub}</div>}
    </div>
  )
}

function DistributionCard({
  title,
  data,
  color,
}: {
  title: string
  data: Record<string, number>
  color: string
}) {
  const entries = Object.entries(data).sort(([, a], [, b]) => b - a)
  const total = entries.reduce((s, [, v]) => s + v, 0)

  return (
    <div className="card-tufte">
      <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">{title}</h3>
      {entries.length > 0 ? (
        <div className="space-y-2">
          {entries.map(([key, count]) => {
            const pct = total > 0 ? (count / total) * 100 : 0
            return (
              <div key={key}>
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-xs text-ink-secondary">{key}</span>
                  <span className="font-mono text-xs text-ink-primary">
                    {count} ({Math.round(pct)}%)
                  </span>
                </div>
                <div className="h-1.5 bg-cream-100 rounded-sm overflow-hidden">
                  <div
                    className="h-full rounded-sm"
                    style={{ width: `${pct}%`, backgroundColor: color }}
                  />
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <p className="font-serif text-sm text-ink-secondary">No data.</p>
      )}
    </div>
  )
}

function EmptyState() {
  return (
    <div className="card-tufte text-center py-12">
      <p className="font-serif text-ink-secondary">No data available for this period.</p>
    </div>
  )
}
