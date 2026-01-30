/**
 * MoltenLoris Sync Settings Panel.
 * Admin UI for viewing sync status and triggering manual operations.
 */

import { useState, useEffect } from 'react'
import { moltenSyncApi, SyncStatus, ExportStatus, SlackScanResult, KnowledgeExportResult } from '../../lib/api/moltenSync'
import LorisAvatar from '../LorisAvatar'

export default function MoltenLorisSettingsPanel() {
  // State
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null)
  const [exportStatus, setExportStatus] = useState<ExportStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [scanning, setScanning] = useState(false)
  const [exporting, setExporting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Last operation results
  const [lastScanResult, setLastScanResult] = useState<SlackScanResult | null>(null)
  const [lastExportResult, setLastExportResult] = useState<KnowledgeExportResult | null>(null)

  // Load status on mount
  useEffect(() => {
    loadStatus()
  }, [])

  const loadStatus = async () => {
    try {
      setLoading(true)
      setError(null)

      const [status, expStatus] = await Promise.all([
        moltenSyncApi.getStatus(),
        moltenSyncApi.getExportStatus(),
      ])

      setSyncStatus(status)
      setExportStatus(expStatus)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status')
    } finally {
      setLoading(false)
    }
  }

  const handleScanSlack = async () => {
    try {
      setScanning(true)
      setError(null)
      setSuccessMessage(null)

      const result = await moltenSyncApi.scanSlack(24)
      setLastScanResult(result)
      setSuccessMessage(`Scan complete: ${result.qa_pairs_found} Q&A pairs found, ${result.captures_created} new captures created`)

      // Reload status
      await loadStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Slack scan failed')
    } finally {
      setScanning(false)
    }
  }

  const handleExportKnowledge = async () => {
    try {
      setExporting(true)
      setError(null)
      setSuccessMessage(null)

      const result = await moltenSyncApi.exportKnowledge()
      setLastExportResult(result)

      if (result.total_errors > 0) {
        setError(`Export completed with ${result.total_errors} error(s)`)
      } else {
        setSuccessMessage(`Export complete: ${result.total_exported} files exported to Google Drive`)
      }

      // Reload status
      await loadStatus()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Knowledge export failed')
    } finally {
      setExporting(false)
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'text-status-success'
      case 'partially_configured':
        return 'text-status-warning'
      default:
        return 'text-status-error'
    }
  }

  const getStatusText = (status: string) => {
    switch (status) {
      case 'ready':
        return '✓ Ready'
      case 'partially_configured':
        return '⚠ Partially Configured'
      default:
        return '✗ Not Configured'
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-8">
        <LorisAvatar mood="thinking" size="md" animate />
        <span className="ml-3 font-serif text-ink-secondary">Loading MoltenLoris status...</span>
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
            Slack monitoring + Google Drive knowledge sync
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

      {/* Configuration Status */}
      <div className="space-y-3">
        <h4 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
          Configuration Status
        </h4>

        <div className="grid grid-cols-2 gap-4">
          <div className="flex justify-between items-center">
            <span className="font-serif text-sm text-ink-secondary">Overall Status</span>
            <span className={`font-mono text-sm ${getStatusColor(syncStatus?.status || '')}`}>
              {getStatusText(syncStatus?.status || '')}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="font-serif text-sm text-ink-secondary">MCP Server</span>
            <span className={`font-mono text-sm ${syncStatus?.mcp_configured ? 'text-status-success' : 'text-status-error'}`}>
              {syncStatus?.mcp_configured ? '✓ Connected' : '✗ Not set'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="font-serif text-sm text-ink-secondary">GDrive Folder</span>
            <span className="font-mono text-xs text-ink-muted">
              {syncStatus?.gdrive_folder || 'Not set'}
            </span>
          </div>

          <div className="flex justify-between items-center">
            <span className="font-serif text-sm text-ink-secondary">Slack Channels</span>
            <span className="font-mono text-xs text-ink-muted">
              {syncStatus?.slack_channels?.length
                ? syncStatus.slack_channels.join(', ')
                : 'None configured'}
            </span>
          </div>
        </div>
      </div>

      {/* Export Statistics */}
      {exportStatus && (
        <div className="space-y-3 pt-4 border-t border-rule-light">
          <h4 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase">
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

          {/* Category breakdown */}
          {Object.keys(exportStatus.categories).length > 0 && (
            <div className="mt-3">
              <p className="font-mono text-xs text-ink-tertiary mb-2">Facts by Category:</p>
              <div className="flex flex-wrap gap-2">
                {Object.entries(exportStatus.categories).map(([cat, count]) => (
                  <span
                    key={cat}
                    className="px-2 py-1 bg-cream-200 rounded-sm font-mono text-xs text-ink-secondary"
                  >
                    {cat}: {count}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-4 border-t border-rule-light">
        <button
          onClick={handleScanSlack}
          disabled={scanning || syncStatus?.status === 'not_configured'}
          className="btn-secondary disabled:opacity-50"
        >
          {scanning ? 'Scanning...' : 'Scan Slack Now'}
        </button>

        <button
          onClick={handleExportKnowledge}
          disabled={exporting || !exportStatus?.mcp_configured}
          className="btn-secondary disabled:opacity-50"
        >
          {exporting ? 'Exporting...' : 'Export to Drive'}
        </button>

        <button
          onClick={loadStatus}
          disabled={loading}
          className="btn-secondary disabled:opacity-50"
        >
          Refresh
        </button>
      </div>

      {/* Last Operation Results */}
      {lastScanResult && (
        <div className="p-3 bg-cream-100 rounded-sm border border-rule-light">
          <p className="font-mono text-xs text-ink-tertiary mb-1">Last Slack Scan:</p>
          <p className="font-serif text-sm text-ink-secondary">
            Found {lastScanResult.qa_pairs_found} Q&A pairs,
            created {lastScanResult.captures_created} new captures
            from {lastScanResult.channels_scanned.join(', ')}
          </p>
        </div>
      )}

      {lastExportResult && (
        <div className="p-3 bg-cream-100 rounded-sm border border-rule-light">
          <p className="font-mono text-xs text-ink-tertiary mb-1">Last Export:</p>
          <p className="font-serif text-sm text-ink-secondary">
            Exported {lastExportResult.total_exported} files
            {lastExportResult.total_errors > 0 && ` (${lastExportResult.total_errors} errors)`}
          </p>
          {lastExportResult.exports
            .filter(e => e.status === 'exported')
            .slice(0, 5)
            .map((exp, i) => (
              <p key={i} className="font-mono text-xs text-ink-muted ml-2">
                • {exp.filename}: {exp.fact_count || exp.rule_count || 0} items
              </p>
            ))}
        </div>
      )}

      {/* Help Text */}
      <div className="text-xs text-ink-muted border-t border-rule-light pt-4 mt-4">
        <p className="font-mono uppercase tracking-wide mb-2">How MoltenLoris Sync Works</p>
        <ul className="space-y-1 font-serif">
          <li>• MoltenLoris answers questions in Slack autonomously</li>
          <li>• When it escalates, experts answer in the Slack thread</li>
          <li>• Loris scans Slack and captures these expert answers</li>
          <li>• Approved answers become knowledge facts</li>
          <li>• Knowledge is exported to Google Drive as markdown files</li>
          <li>• MoltenLoris reads from Google Drive to improve its answers</li>
        </ul>
      </div>
    </div>
  )
}
