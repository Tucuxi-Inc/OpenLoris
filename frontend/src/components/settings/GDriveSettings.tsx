/**
 * GDrive Settings Panel.
 * Admin UI for configuring Google Drive integration via Zapier MCP.
 */

import { useState, useEffect } from 'react'
import { gdriveApi, GDriveSettings, GDriveFolder } from '../../lib/api/gdrive'
import LorisAvatar from '../LorisAvatar'

interface GDriveSettingsPanelProps {
  onSave?: () => void
}

export default function GDriveSettingsPanel({ onSave }: GDriveSettingsPanelProps) {
  // State
  const [settings, setSettings] = useState<GDriveSettings | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form state
  const [enabled, setEnabled] = useState(false)
  const [mcpUrl, setMcpUrl] = useState('')
  const [folderId, setFolderId] = useState('')
  const [folderName, setFolderName] = useState('')
  const [syncDirection, setSyncDirection] = useState<'export' | 'import' | 'bidirectional'>('export')

  // Connection test state
  const [connectionStatus, setConnectionStatus] = useState<{
    tested: boolean
    connected: boolean
    message: string
  } | null>(null)

  // Folders list for selection
  const [folders, setFolders] = useState<GDriveFolder[]>([])
  const [loadingFolders, setLoadingFolders] = useState(false)

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)
      const data = await gdriveApi.getSettings()
      setSettings(data)

      // Populate form
      setEnabled(data.enabled)
      setFolderId(data.folder_id || '')
      setFolderName(data.folder_name || '')
      setSyncDirection(data.sync_direction)
      // Don't populate mcpUrl - it's not returned for security
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setLoading(false)
    }
  }

  const handleSave = async () => {
    try {
      setSaving(true)
      setError(null)
      setSuccessMessage(null)

      const updateData: Parameters<typeof gdriveApi.updateSettings>[0] = {
        enabled,
        sync_direction: syncDirection,
      }

      // Only include mcpUrl if it was changed (non-empty)
      if (mcpUrl.trim()) {
        updateData.zapier_mcp_url = mcpUrl.trim()
      }

      if (folderId) {
        updateData.folder_id = folderId
        updateData.folder_name = folderName
      }

      const updated = await gdriveApi.updateSettings(updateData)
      setSettings(updated)
      setSuccessMessage('Settings saved successfully')
      setMcpUrl('') // Clear the URL field after save

      onSave?.()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  const handleTestConnection = async () => {
    try {
      setTesting(true)
      setConnectionStatus(null)
      setError(null)

      // If URL was entered, save it first
      if (mcpUrl.trim()) {
        await gdriveApi.updateSettings({ zapier_mcp_url: mcpUrl.trim() })
        setMcpUrl('')
      }

      const result = await gdriveApi.testConnection()
      setConnectionStatus({
        tested: true,
        connected: result.connected,
        message: result.message,
      })

      // If connected, load folders
      if (result.connected) {
        loadFolders()
      }
    } catch (err) {
      setConnectionStatus({
        tested: true,
        connected: false,
        message: err instanceof Error ? err.message : 'Connection test failed',
      })
    } finally {
      setTesting(false)
    }
  }

  const loadFolders = async () => {
    try {
      setLoadingFolders(true)
      const folderList = await gdriveApi.listFolders()
      setFolders(folderList)
    } catch (err) {
      console.error('Failed to load folders:', err)
    } finally {
      setLoadingFolders(false)
    }
  }

  const handleSync = async () => {
    try {
      setSyncing(true)
      setError(null)
      setSuccessMessage(null)

      const result = await gdriveApi.triggerSync(syncDirection)

      if (result.success) {
        const parts = []
        if (result.exported !== null) parts.push(`${result.exported} exported`)
        if (result.imported !== null) parts.push(`${result.imported} imported`)
        if (result.skipped !== null) parts.push(`${result.skipped} skipped`)
        setSuccessMessage(`Sync completed: ${parts.join(', ')}`)
      } else {
        setError(`Sync completed with ${result.errors.length} error(s)`)
      }

      // Reload settings to get updated last_sync info
      await loadSettings()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sync failed')
    } finally {
      setSyncing(false)
    }
  }

  const formatDate = (isoString: string | null) => {
    if (!isoString) return 'Never'
    return new Date(isoString).toLocaleString()
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LorisAvatar mood="thinking" size="md" animate />
        <span className="ml-3 font-serif text-ink-secondary">Loading GDrive settings...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-rule-light pb-4">
        <img
          src="/loris-images/Scholar_Loris.png"
          alt="GDrive"
          className="h-12 w-auto"
        />
        <div>
          <h3 className="font-serif text-lg text-ink-primary">Google Drive Integration</h3>
          <p className="font-mono text-xs text-ink-tertiary">
            Sync knowledge with GDrive via Zapier MCP
          </p>
        </div>
      </div>

      {/* Error/Success Messages */}
      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}
      {successMessage && (
        <div className="p-3 bg-cream-200 border border-status-success rounded-sm">
          <p className="font-serif text-sm text-status-success">{successMessage}</p>
        </div>
      )}

      {/* Enable Toggle */}
      <div className="flex items-center justify-between">
        <div>
          <label className="font-serif text-ink-primary">Enable GDrive Integration</label>
          <p className="font-mono text-xs text-ink-tertiary">
            Sync knowledge facts with Google Drive
          </p>
        </div>
        <button
          onClick={() => setEnabled(!enabled)}
          className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
            enabled ? 'bg-status-success' : 'bg-rule-light'
          }`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
              enabled ? 'translate-x-6' : 'translate-x-1'
            }`}
          />
        </button>
      </div>

      {/* Zapier MCP URL */}
      <div>
        <label className="label-tufte">Zapier MCP URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={mcpUrl}
            onChange={(e) => setMcpUrl(e.target.value)}
            placeholder={settings?.zapier_mcp_url_set ? '••••••••••••••••' : 'https://hooks.zapier.com/...'}
            className="input-tufte flex-1"
          />
          <button
            onClick={handleTestConnection}
            disabled={testing || (!mcpUrl.trim() && !settings?.zapier_mcp_url_set)}
            className="btn-secondary disabled:opacity-50"
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>
        {settings?.zapier_mcp_url_set && !mcpUrl && (
          <p className="font-mono text-xs text-ink-muted mt-1">
            URL is configured. Enter a new URL to update it.
          </p>
        )}
      </div>

      {/* Connection Status */}
      {connectionStatus && (
        <div className={`p-3 rounded-sm border ${
          connectionStatus.connected
            ? 'bg-cream-100 border-status-success'
            : 'bg-cream-200 border-status-error'
        }`}>
          <div className="flex items-center gap-2">
            <span className={`font-mono text-sm ${
              connectionStatus.connected ? 'text-status-success' : 'text-status-error'
            }`}>
              {connectionStatus.connected ? '✓ Connected' : '✗ Not Connected'}
            </span>
          </div>
          <p className="font-serif text-sm text-ink-secondary mt-1">
            {connectionStatus.message}
          </p>
        </div>
      )}

      {/* Folder Selection */}
      <div>
        <label className="label-tufte">Sync Folder</label>
        {loadingFolders ? (
          <p className="font-mono text-xs text-ink-muted">Loading folders...</p>
        ) : folders.length > 0 ? (
          <select
            value={folderId}
            onChange={(e) => {
              const folder = folders.find(f => f.id === e.target.value)
              setFolderId(e.target.value)
              setFolderName(folder?.name || '')
            }}
            className="input-tufte w-full"
          >
            <option value="">Select a folder...</option>
            {folders.map((folder) => (
              <option key={folder.id} value={folder.id}>
                {folder.name}
              </option>
            ))}
          </select>
        ) : (
          <div className="flex gap-2">
            <input
              type="text"
              value={folderId}
              onChange={(e) => setFolderId(e.target.value)}
              placeholder="Folder ID"
              className="input-tufte flex-1"
            />
            <input
              type="text"
              value={folderName}
              onChange={(e) => setFolderName(e.target.value)}
              placeholder="Folder Name (optional)"
              className="input-tufte flex-1"
            />
          </div>
        )}
        {folderName && (
          <p className="font-mono text-xs text-ink-muted mt-1">
            Selected: {folderName}
          </p>
        )}
      </div>

      {/* Sync Direction */}
      <div>
        <label className="label-tufte">Sync Direction</label>
        <div className="flex gap-4 mt-2">
          {(['export', 'import', 'bidirectional'] as const).map((dir) => (
            <label key={dir} className="flex items-center gap-2 cursor-pointer">
              <input
                type="radio"
                name="syncDirection"
                value={dir}
                checked={syncDirection === dir}
                onChange={() => setSyncDirection(dir)}
                className="accent-loris-brown"
              />
              <span className="font-serif text-sm text-ink-primary capitalize">{dir}</span>
            </label>
          ))}
        </div>
        <p className="font-mono text-xs text-ink-tertiary mt-1">
          {syncDirection === 'export' && 'Export knowledge facts from Open Loris to GDrive'}
          {syncDirection === 'import' && 'Import knowledge from GDrive to Open Loris'}
          {syncDirection === 'bidirectional' && 'Sync in both directions'}
        </p>
      </div>

      {/* Last Sync Info */}
      {settings?.last_sync_at && (
        <div className="p-3 bg-cream-100 rounded-sm border border-rule-light">
          <p className="font-mono text-xs text-ink-tertiary">
            Last sync: {formatDate(settings.last_sync_at)}
          </p>
          {settings.last_sync_result && (
            <p className="font-mono text-xs text-ink-secondary mt-1">
              {settings.last_sync_result.direction}:
              {settings.last_sync_result.exported !== undefined && ` ${settings.last_sync_result.exported} exported`}
              {settings.last_sync_result.imported !== undefined && ` ${settings.last_sync_result.imported} imported`}
              {settings.last_sync_result.errors_count ? ` (${settings.last_sync_result.errors_count} errors)` : ''}
            </p>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t border-rule-light">
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-primary disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>

        {enabled && folderId && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="btn-secondary disabled:opacity-50"
          >
            {syncing ? 'Syncing...' : 'Sync Now'}
          </button>
        )}
      </div>

      {/* Help Text */}
      <div className="text-xs text-ink-muted border-t border-rule-light pt-4 mt-4">
        <p className="font-mono uppercase tracking-wide mb-2">How it works</p>
        <ul className="space-y-1 font-serif">
          <li>• Zapier handles Google authentication — no OAuth setup needed</li>
          <li>• Knowledge facts are exported as markdown files with YAML frontmatter</li>
          <li>• MoltenLoris reads these files (read-only) to answer questions</li>
          <li>• Only Loris Web App can write to GDrive — MoltenLoris is read-only</li>
        </ul>
      </div>
    </div>
  )
}
