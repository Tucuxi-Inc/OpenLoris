import { apiClient } from './client'

// ── Response types ──────────────────────────────────────────────────

export interface OverviewData {
  total_questions: number
  total_resolved: number
  automation_rate: number
  avg_response_time_seconds: number | null
  avg_resolution_time_seconds: number | null
  avg_satisfaction: number | null
  period_question_count: number
  prev_period_question_count: number
  period: string
}

export interface DailyVolume {
  date: string
  total: number
  auto_answered: number
  expert_answered: number
}

export interface QuestionTrendsData {
  daily_volumes: DailyVolume[]
  status_distribution: Record<string, number>
  priority_distribution: Record<string, number>
}

export interface RulePerformance {
  rule_id: string
  name: string
  times_triggered: number
  times_accepted: number
  times_rejected: number
  acceptance_rate: number | null
  is_enabled: boolean
}

export interface DailyAutomationTrend {
  date: string
  delivered: number
  accepted: number
  rejected: number
}

export interface AutomationPerformanceData {
  total_triggers: number
  total_accepted: number
  total_rejected: number
  overall_acceptance_rate: number | null
  rules: RulePerformance[]
  daily_trend: DailyAutomationTrend[]
}

export interface KnowledgeCoverageData {
  total_facts: number
  by_tier: Record<string, number>
  expiring_soon: number
  recently_added: number
  avg_confidence: number | null
}

export interface ExpertStats {
  expert_name: string
  questions_answered: number
  avg_response_time_seconds: number | null
  avg_satisfaction: number | null
}

export interface ExpertPerformanceData {
  experts: ExpertStats[]
}

// ── API methods ─────────────────────────────────────────────────────

export const analyticsApi = {
  getOverview: (period = '30d') =>
    apiClient.get<OverviewData>('/api/v1/analytics/overview', { params: { period } }),

  getQuestionTrends: (period = '30d') =>
    apiClient.get<QuestionTrendsData>('/api/v1/analytics/questions', { params: { period } }),

  getAutomationPerformance: (period = '30d') =>
    apiClient.get<AutomationPerformanceData>('/api/v1/analytics/automation', { params: { period } }),

  getKnowledgeCoverage: () =>
    apiClient.get<KnowledgeCoverageData>('/api/v1/analytics/knowledge'),

  getExpertPerformance: (period = '30d') =>
    apiClient.get<ExpertPerformanceData>('/api/v1/analytics/experts', { params: { period } }),
}
