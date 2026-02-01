/**
 * MoltenLoris Settings Panel.
 * Admin UI for configuring MoltenLoris integration - MCP server and Slack channels.
 */

import { useState, useEffect } from 'react'
import {
  moltenSyncApi,
  MoltenLorisSettings,
  SyncStatus,
  ExportStatus,
  ConnectionTestResult,
} from '../../lib/api/moltenSync'
import LorisAvatar from '../LorisAvatar'

export default function MoltenLorisSettingsPanel() {
  // Settings state
  const [settings, setSettings] = useState<MoltenLorisSettings | null>(null)
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Form state
  const [enabled, setEnabled] = useState(false)
  const [mcpUrl, setMcpUrl] = useState('')
  const [channels, setChannels] = useState<string[]>([])
  const [newChannel, setNewChannel] = useState('')

  // Connection test state
  const [connectionStatus, setConnectionStatus] = useState<ConnectionTestResult | null>(null)

  // Load settings on mount
  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setLoading(true)
      setError(null)

      const [settingsData, statusData, expStatusData] = await Promise.all([
        moltenSyncApi.getSettings(),
        moltenSyncApi.getStatus(),
        moltenSyncApi.getExportStatus(),
      ])

      setSettings(settingsData)
      setSyncStatus(statusData)
      setExportStatus(expStatusData)

      // Populate form
      setEnabled(settingsData.enabled)
      setChannels(settingsData.slack_channels)

      // If there was a previous test result, show it
      if (settingsData.last_test_result) {
        setConnectionStatus({
          connected: settingsData.last_test_result.connected,
          message: settingsData.last_test_result.message,
          tested_at: settingsData.last_test_at || '',
        })
      }
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

      const updateData: Parameters<typeof moltenSyncApi.updateSettings>[0] = {
        enabled,
        slack_channels: channels,
      }

      // Only include mcpUrl if it was changed (non-empty)
      if (mcpUrl.trim()) {
        updateData.mcp_server_url = mcpUrl.trim()
      }

      const updated = await moltenSyncApi.updateSettings(updateData)
      setSettings(updated)
      setMcpUrl('') // Clear the URL field after save
      setSuccessMessage('Settings saved successfully')

      // Reload status to reflect changes
      const statusData = await moltenSyncApi.getStatus()
      setSyncStatus(statusData)
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
        await moltenSyncApi.updateSettings({ mcp_server_url: mcpUrl.trim() })
        setMcpUrl('')
      }

      const result = await moltenSyncApi.testConnection()
      setConnectionStatus(result)

      // Reload settings to get updated last_test info
      const updated = await moltenSyncApi.getSettings()
      setSettings(updated)
    } catch (err) {
      setConnectionStatus({
        connected: false,
        message: err instanceof Error ? err.message : 'Connection test failed',
        tested_at: new Date().toISOString(),
      })
    } finally {
      setTesting(false)
    }
  }

  const handleAddChannel = () => {
    const channel = newChannel.trim().replace(/^#/, '') // Remove # prefix
    if (!channel) return
    if (channels.includes(channel)) {
      setError('Channel already added')
      setTimeout(() => setError(null), 3000)
      return
    }
    setChannels([...channels, channel])
    setNewChannel('')
  }

  const handleRemoveChannel = (channel: string) => {
    setChannels(channels.filter(c => c !== channel))
  }

  const hasChanges = settings && (
    enabled !== settings.enabled ||
    JSON.stringify(channels) !== JSON.stringify(settings.slack_channels) ||
    mcpUrl.trim() !== ''
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LorisAvatar mood="thinking" size="md" animate />
        <span className="ml-3 font-serif text-ink-secondary">Loading MoltenLoris settings...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3 border-b border-rule-light pb-4">
        <img
          src="/loris-images/Molten_Loris.png"
          alt="MoltenLoris"
          className="h-12 w-auto"
        />
        <div>
          <h3 className="font-serif text-lg text-ink-primary">MoltenLoris Integration</h3>
          <p className="font-mono text-xs text-ink-tertiary">
            Configure MCP server and Slack channel monitoring
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
          <label className="font-serif text-ink-primary">Enable MoltenLoris Integration</label>
          <p className="font-mono text-xs text-ink-tertiary">
            Allow MoltenLoris to sync with your knowledge base
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

      {/* MCP Server URL */}
      <div>
        <label className="label-tufte">MCP Server URL</label>
        <div className="flex gap-2">
          <input
            type="url"
            value={mcpUrl}
            onChange={(e) => setMcpUrl(e.target.value)}
            placeholder={settings?.mcp_server_url_set ? '••••••••••••••••' : 'https://hooks.zapier.com/...'}
            className="input-tufte flex-1"
          />
          <button
            onClick={handleTestConnection}
            disabled={testing || (!mcpUrl.trim() && !settings?.mcp_server_url_set)}
            className="btn-secondary disabled:opacity-50"
          >
            {testing ? 'Testing...' : 'Test Connection'}
          </button>
        </div>
        {settings?.mcp_server_url_set && !mcpUrl && (
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

      {/* Slack Channels */}
      <div>
        <label className="label-tufte">Slack Channels to Monitor</label>
        <p className="font-mono text-xs text-ink-tertiary mb-2">
          Channels where MoltenLoris will watch for questions
        </p>

        {/* Channel list */}
        {channels.length > 0 ? (
          <div className="flex flex-wrap gap-2 mb-3">
            {channels.map(channel => (
              <div
                key={channel}
                className="flex items-center gap-2 px-3 py-1 bg-cream-200 rounded-sm"
              >
                <span className="font-mono text-sm text-ink-primary">#{channel}</span>
                <button
                  onClick={() => handleRemoveChannel(channel)}
                  className="text-ink-tertiary hover:text-status-error transition-colors"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="font-serif text-sm text-ink-muted mb-3 italic">
            No channels configured
          </p>
        )}

        {/* Add channel input */}
        <div className="flex gap-2">
          <input
            type="text"
            value={newChannel}
            onChange={(e) => setNewChannel(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                e.preventDefault()
                handleAddChannel()
              }
            }}
            placeholder="#channel-name"
            className="input-tufte flex-1"
          />
          <button
            onClick={handleAddChannel}
            disabled={!newChannel.trim()}
            className="btn-secondary disabled:opacity-50"
          >
            Add
          </button>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center gap-4 pt-4 border-t border-rule-light">
        <button
          onClick={handleSave}
          disabled={saving || !hasChanges}
          className="btn-primary disabled:opacity-50"
        >
          {saving ? 'Saving...' : 'Save Settings'}
        </button>

        {hasChanges && (
          <span className="font-mono text-xs text-status-warning">Unsaved changes</span>
        )}

        <button
          onClick={loadSettings}
          disabled={loading}
          className="btn-secondary disabled:opacity-50 ml-auto"
        >
          Refresh
        </button>
      </div>

      {/* Current Status Summary */}
      {syncStatus && (
        <div className="pt-4 border-t border-rule-light">
          <h4 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-3">
            Current Status
          </h4>

          <div className="grid grid-cols-2 gap-3">
            <div className="flex justify-between items-center">
              <span className="font-serif text-sm text-ink-secondary">Overall</span>
              <span className={`font-mono text-sm ${
                syncStatus.status === 'ready' ? 'text-status-success' :
                syncStatus.status === 'partially_configured' ? 'text-status-warning' :
                'text-status-error'
              }`}>
                {syncStatus.status === 'ready' ? '✓ Ready' :
                 syncStatus.status === 'partially_configured' ? '⚠ Partial' :
                 '✗ Not Configured'}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="font-serif text-sm text-ink-secondary">MCP Server</span>
              <span className={`font-mono text-sm ${
                syncStatus.mcp_configured ? 'text-status-success' : 'text-status-error'
              }`}>
                {syncStatus.mcp_configured ? '✓ Set' : '✗ Not set'}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="font-serif text-sm text-ink-secondary">Channels</span>
              <span className="font-mono text-sm text-ink-primary">
                {syncStatus.slack_channels.length || 0}
              </span>
            </div>

            <div className="flex justify-between items-center">
              <span className="font-serif text-sm text-ink-secondary">GDrive</span>
              <span className="font-mono text-xs text-ink-muted">
                {syncStatus.gdrive_folder || 'Not set'}
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Knowledge Statistics */}
      {exportStatus && (
        <div className="pt-4 border-t border-rule-light">
          <h4 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-3">
            Knowledge Statistics
          </h4>

          <div className="grid grid-cols-3 gap-4">
            <div className="text-center p-3 bg-cream-100 rounded-sm">
              <p className="font-mono text-2xl text-ink-primary">{exportStatus.total_facts}</p>
              <p className="font-mono text-xs text-ink-tertiary">Total Facts</p>
            </div>
            <div className="text-center p-3 bg-cream-100 rounded-sm">
              <p className="font-mono text-2xl text-ink-primary">
                {Object.keys(exportStatus.categories).length}
              </p>
              <p className="font-mono text-xs text-ink-tertiary">Categories</p>
            </div>
            <div className="text-center p-3 bg-cream-100 rounded-sm">
              <p className="font-mono text-2xl text-ink-primary">{exportStatus.automation_rules}</p>
              <p className="font-mono text-xs text-ink-tertiary">FAQ Rules</p>
            </div>
          </div>
        </div>
      )}

      {/* Help Text */}
      <div className="text-xs text-ink-muted border-t border-rule-light pt-4 mt-4">
        <p className="font-mono uppercase tracking-wide mb-2">Setup Instructions</p>
        <ol className="space-y-1 font-serif list-decimal list-inside">
          <li>Enter your MCP server URL (Zapier webhook or custom endpoint)</li>
          <li>Click "Test Connection" to verify connectivity</li>
          <li>Add Slack channels for MoltenLoris to monitor</li>
          <li>Enable the integration and save settings</li>
          <li>Generate a SOUL file from the MoltenLoris page to configure your bot</li>
        </ol>
      </div>
    </div>
  )
}
