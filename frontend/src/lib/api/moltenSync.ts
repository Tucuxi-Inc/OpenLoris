/**
 * MoltenLoris Sync API client.
 * Handles Slack scanning and knowledge export operations.
 */

import { apiClient } from './client'

// ── Types ───────────────────────────────────────────────────────────

export interface SyncStatus {
  mcp_configured: boolean
  gdrive_folder: string
  slack_channels: string[]
  status: 'ready' | 'partially_configured' | 'not_configured'
}

export interface SlackScanResult {
  status: string
  qa_pairs_found: number
  captures_created: number
  channels_scanned: string[]
}

export interface KnowledgeExportResult {
  status: string
  exports: Array<{
    status: string
    category: string
    fact_count?: number
    rule_count?: number
    filename?: string
    gdrive_url?: string
    message?: string
  }>
  total_exported: number
  total_errors: number
}

export interface ExportStatus {
  total_facts: number
  categories: Record<string, number>
  automation_rules: number
  gdrive_folder: string
  mcp_configured: boolean
}

export interface SlackCapture {
  id: string
  channel: string
  thread_ts: string
  original_question: string
  expert_answer: string
  expert_name: string
  confidence_score: number
  status: 'pending' | 'approved' | 'rejected' | 'duplicate'
  suggested_category: string | null
  created_at: string
}

// ── MoltenLoris Settings Types ─────────────────────────────────────

export interface MoltenLorisSettings {
  enabled: boolean
  mcp_server_url_set: boolean
  slack_channels: string[]
  last_test_at: string | null
  last_test_result: {
    connected: boolean
    message: string
  } | null
}

export interface MoltenLorisSettingsUpdate {
  enabled?: boolean
  mcp_server_url?: string
  slack_channels?: string[]
}

export interface ConnectionTestResult {
  connected: boolean
  message: string
  tested_at: string
}

// ── MoltenLoris Activity Types ─────────────────────────────────────

export interface MoltenActivity {
  id: string
  channel_id: string
  channel_name: string
  thread_ts: string | null
  user_slack_id: string | null
  user_name: string | null
  question_text: string
  answer_text: string
  confidence_score: number
  source_facts: string[]
  was_corrected: boolean
  corrected_by: {
    id: string
    name: string
    email: string
  } | null
  corrected_at: string | null
  correction_text: string | null
  correction_reason: string | null
  created_question_id: string | null
  created_fact_id: string | null
  created_at: string
}

export interface ActivityListResponse {
  activities: MoltenActivity[]
  total: number
  limit: number
  offset: number
}

export interface ActivityStats {
  total_answers: number
  high_confidence_count: number
  low_confidence_count: number
  corrected_count: number
  correction_rate: number
  avg_confidence: number
  top_channels: Array<{ channel: string; count: number }>
  confidence_distribution: Array<{ range: string; count: number }>
  daily_trend: Array<{ date: string; count: number }>
}

export interface SoulFileResponse {
  soul_content: string
  generated_at: string
  organization_name: string
  stats: {
    total_facts: number
    tier_0a: number
    tier_0b: number
    tier_0c: number
    active_rules: number
    active_subdomains: number
  }
}

// ── API Client ──────────────────────────────────────────────────────

export const moltenSyncApi = {
  // ── Settings Management ────────────────────────────────────────────

  /**
   * Get MoltenLoris configuration settings.
   */
  getSettings: async (): Promise<MoltenLorisSettings> => {
    return apiClient.get<MoltenLorisSettings>('/api/v1/molten-sync/settings')
  },

  /**
   * Update MoltenLoris configuration settings.
   */
  updateSettings: async (data: MoltenLorisSettingsUpdate): Promise<MoltenLorisSettings> => {
    return apiClient.put<MoltenLorisSettings>('/api/v1/molten-sync/settings', data)
  },

  /**
   * Test MCP server connection.
   */
  testConnection: async (): Promise<ConnectionTestResult> => {
    return apiClient.post<ConnectionTestResult>('/api/v1/molten-sync/test-connection')
  },

  // ── Status & Operations ────────────────────────────────────────────

  /**
   * Get MoltenLoris sync configuration status.
   */
  getStatus: async (): Promise<SyncStatus> => {
    return apiClient.get<SyncStatus>('/api/v1/molten-sync/status')
  },

  /**
   * Trigger manual Slack scan for expert answers.
   */
  scanSlack: async (hoursBack: number = 24): Promise<SlackScanResult> => {
    return apiClient.post<SlackScanResult>(
      `/api/v1/molten-sync/scan-slack?hours_back=${hoursBack}`
    )
  },

  /**
   * Trigger manual knowledge export to Google Drive.
   */
  exportKnowledge: async (category?: string): Promise<KnowledgeExportResult> => {
    const url = category
      ? `/api/v1/molten-sync/export-knowledge?category=${encodeURIComponent(category)}`
      : '/api/v1/molten-sync/export-knowledge'
    return apiClient.post<KnowledgeExportResult>(url)
  },

  /**
   * Get current export status and statistics.
   */
  getExportStatus: async (): Promise<ExportStatus> => {
    return apiClient.get<ExportStatus>('/api/v1/molten-sync/export-status')
  },

  /**
   * List Slack captures for review.
   */
  listCaptures: async (status: string = 'pending', limit: number = 50): Promise<SlackCapture[]> => {
    return apiClient.get<SlackCapture[]>(
      `/api/v1/molten-sync/captures?status=${status}&limit=${limit}`
    )
  },

  /**
   * Get a specific Slack capture.
   */
  getCapture: async (captureId: string): Promise<SlackCapture> => {
    return apiClient.get<SlackCapture>(`/api/v1/molten-sync/captures/${captureId}`)
  },

  /**
   * Approve a Slack capture.
   */
  approveCapture: async (
    captureId: string,
    notes?: string,
    category?: string
  ): Promise<{ status: string; capture_id: string; message: string }> => {
    return apiClient.post(`/api/v1/molten-sync/captures/${captureId}/approve`, {
      notes,
      category,
    })
  },

  /**
   * Reject a Slack capture.
   */
  rejectCapture: async (
    captureId: string,
    reason: string
  ): Promise<{ status: string; capture_id: string }> => {
    return apiClient.post(`/api/v1/molten-sync/captures/${captureId}/reject`, {
      notes: reason,
    })
  },

  // ── SOUL File Generation ─────────────────────────────────────────

  /**
   * Generate SOUL configuration file for MoltenLoris.
   */
  generateSoulFile: async (): Promise<SoulFileResponse> => {
    return apiClient.post<SoulFileResponse>('/api/v1/molten-sync/soul')
  },

  // ── MoltenLoris Activity Tracking ────────────────────────────────

  /**
   * List MoltenLoris activity log.
   */
  listActivities: async (params?: {
    limit?: number
    offset?: number
    channel_id?: string
    corrected_only?: boolean
    needs_review?: boolean
  }): Promise<ActivityListResponse> => {
    const searchParams = new URLSearchParams()
    if (params?.limit) searchParams.set('limit', params.limit.toString())
    if (params?.offset) searchParams.set('offset', params.offset.toString())
    if (params?.channel_id) searchParams.set('channel_id', params.channel_id)
    if (params?.corrected_only) searchParams.set('corrected_only', 'true')
    if (params?.needs_review) searchParams.set('needs_review', 'true')

    const query = searchParams.toString()
    return apiClient.get<ActivityListResponse>(
      `/api/v1/molten-sync/activities${query ? `?${query}` : ''}`
    )
  },

  /**
   * Get a specific MoltenLoris activity.
   */
  getActivity: async (activityId: string): Promise<MoltenActivity> => {
    return apiClient.get<MoltenActivity>(`/api/v1/molten-sync/activities/${activityId}`)
  },

  /**
   * Record expert correction to a MoltenLoris answer.
   */
  correctActivity: async (
    activityId: string,
    data: {
      correction_text: string
      correction_reason: string
      create_fact?: boolean
    }
  ): Promise<{
    status: string
    activity_id: string
    corrected_at: string
    created_fact_id: string | null
  }> => {
    return apiClient.post(`/api/v1/molten-sync/activities/${activityId}/correct`, data)
  },

  /**
   * Get MoltenLoris activity statistics.
   */
  getActivityStats: async (period: string = '30d'): Promise<ActivityStats> => {
    return apiClient.get<ActivityStats>(
      `/api/v1/molten-sync/activities/stats?period=${period}`
    )
  },
}
