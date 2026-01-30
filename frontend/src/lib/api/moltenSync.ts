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

// ── API Client ──────────────────────────────────────────────────────

export const moltenSyncApi = {
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
}
