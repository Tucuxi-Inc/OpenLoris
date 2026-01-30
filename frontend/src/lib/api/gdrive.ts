/**
 * Google Drive API client.
 * Handles GDrive settings, connection testing, and sync operations.
 */

import { apiClient } from './client'

// ── Types ───────────────────────────────────────────────────────────

export interface GDriveSettings {
  enabled: boolean
  zapier_mcp_url_set: boolean
  folder_id: string | null
  folder_name: string | null
  sync_direction: 'export' | 'import' | 'bidirectional'
  last_sync_at: string | null
  last_sync_result: {
    direction: string
    exported?: number
    imported?: number
    skipped?: number
    errors_count?: number
  } | null
}

export interface GDriveSettingsUpdate {
  enabled?: boolean
  zapier_mcp_url?: string
  folder_id?: string
  folder_name?: string
  sync_direction?: 'export' | 'import' | 'bidirectional'
}

export interface GDriveConnectionTest {
  connected: boolean
  message: string
  details?: Record<string, unknown>
}

export interface GDriveFolder {
  id: string
  name: string
  parent_id: string | null
}

export interface GDriveFile {
  id: string
  name: string
  mime_type: string | null
  size: number | null
  modified_at: string | null
}

export interface GDriveSyncResult {
  success: boolean
  direction: string
  exported: number | null
  imported: number | null
  skipped: number | null
  total: number | null
  errors: Array<{ file?: string; fact_id?: string; error: string }>
  timestamp: string
}

export interface GDriveStatus {
  enabled: boolean
  configured: boolean
  folder_configured: boolean
  folder_name: string | null
  sync_direction: string
  last_sync_at: string | null
  last_sync_result: Record<string, unknown> | null
}

// ── API Client ──────────────────────────────────────────────────────

export const gdriveApi = {
  /**
   * Get GDrive settings.
   */
  getSettings: async (): Promise<GDriveSettings> => {
    return apiClient.get<GDriveSettings>('/api/v1/gdrive/settings')
  },

  /**
   * Update GDrive settings.
   */
  updateSettings: async (data: GDriveSettingsUpdate): Promise<GDriveSettings> => {
    return apiClient.put<GDriveSettings>('/api/v1/gdrive/settings', data)
  },

  /**
   * Test GDrive connection via Zapier MCP.
   */
  testConnection: async (): Promise<GDriveConnectionTest> => {
    return apiClient.post<GDriveConnectionTest>('/api/v1/gdrive/test')
  },

  /**
   * List available GDrive folders.
   */
  listFolders: async (parentId?: string): Promise<GDriveFolder[]> => {
    const params = parentId ? { parent_id: parentId } : undefined
    return apiClient.get<GDriveFolder[]>('/api/v1/gdrive/folders', { params })
  },

  /**
   * List files in a GDrive folder.
   */
  listFiles: async (folderId?: string): Promise<GDriveFile[]> => {
    const params = folderId ? { folder_id: folderId } : undefined
    return apiClient.get<GDriveFile[]>('/api/v1/gdrive/files', { params })
  },

  /**
   * Trigger knowledge sync with GDrive.
   */
  triggerSync: async (direction?: 'export' | 'import' | 'bidirectional'): Promise<GDriveSyncResult> => {
    const params = direction ? { direction } : undefined
    return apiClient.post<GDriveSyncResult>('/api/v1/gdrive/sync', undefined, { params })
  },

  /**
   * Get current sync status.
   */
  getStatus: async (): Promise<GDriveStatus> => {
    return apiClient.get<GDriveStatus>('/api/v1/gdrive/status')
  },
}
