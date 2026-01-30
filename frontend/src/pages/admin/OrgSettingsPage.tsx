import { useState, useEffect } from 'react'
import { orgApi, OrgSettings } from '../../lib/api/org'
import AIProviderSettingsPanel from '../../components/settings/AIProviderSettings'
import GDriveSettingsPanel from '../../components/settings/GDriveSettings'
import MoltenLorisSettingsPanel from '../../components/settings/MoltenLorisSettings'

export default function OrgSettingsPage() {
  const [settings, setSettings] = useState<OrgSettings | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Department editing
  const [newDepartment, setNewDepartment] = useState('')
  const [requireDepartment, setRequireDepartment] = useState(false)
  const [departments, setDepartments] = useState<string[]>([])
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  const loadSettings = async () => {
    try {
      setIsLoading(true)
      const result = await orgApi.getSettings()
      setSettings(result)
      setDepartments(result.departments)
      setRequireDepartment(result.require_department)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }

  const handleAddDepartment = () => {
    const name = newDepartment.trim()
    if (!name) return
    if (departments.includes(name)) {
      setError('Department already exists.')
      setTimeout(() => setError(''), 3000)
      return
    }
    setDepartments([...departments, name])
    setNewDepartment('')
  }

  const handleRemoveDepartment = (dept: string) => {
    setDepartments(departments.filter(d => d !== dept))
  }

  const handleSave = async () => {
    setIsSaving(true)
    setError('')
    try {
      const result = await orgApi.updateSettings({
        departments,
        require_department: requireDepartment,
      })
      setSettings(result)
      setSuccess('Settings saved.')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges =
    settings &&
    (JSON.stringify(departments) !== JSON.stringify(settings.departments) ||
      requireDepartment !== settings.require_department)

  if (isLoading) {
    return (
      <div className="card-tufte text-center py-12">
        <p className="font-serif text-ink-secondary">Loading settings...</p>
      </div>
    )
  }

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl text-ink-primary mb-2">Organization Settings</h1>
        <p className="font-serif text-ink-secondary">
          Configure departments, AI providers, and integrations.
        </p>
      </div>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-6">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}
      {success && (
        <div className="p-3 bg-cream-200 border border-status-success rounded-sm mb-6">
          <p className="font-serif text-sm text-status-success">{success}</p>
        </div>
      )}

      {/* Two-column layout */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left Column */}
        <div className="space-y-6">
          {/* AI Provider Settings */}
          <div className="card-tufte">
            <AIProviderSettingsPanel />
          </div>

          {/* Departments & Question Requirements */}
          <div className="card-tufte">
            <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
              Departments
            </h3>
            <p className="font-serif text-sm text-ink-secondary mb-4">
              Define departments for question routing.
            </p>

            {/* Department list */}
            {departments.length > 0 ? (
              <div className="space-y-2 mb-4">
                {departments.map(dept => (
                  <div key={dept} className="flex items-center justify-between py-2 px-3 bg-cream-200 rounded-sm">
                    <span className="font-serif text-sm text-ink-primary">{dept}</span>
                    <button
                      onClick={() => handleRemoveDepartment(dept)}
                      className="font-mono text-xs text-status-error hover:text-ink-primary"
                    >
                      Remove
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <p className="font-serif text-sm text-ink-muted mb-4 italic">
                No departments configured.
              </p>
            )}

            {/* Add department */}
            <div className="flex gap-2 mb-6">
              <input
                type="text"
                value={newDepartment}
                onChange={(e) => setNewDepartment(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') { e.preventDefault(); handleAddDepartment() } }}
                className="input-tufte flex-1"
                placeholder="Department name..."
              />
              <button
                onClick={handleAddDepartment}
                disabled={!newDepartment.trim()}
                className="btn-secondary disabled:opacity-50"
              >
                Add
              </button>
            </div>

            {/* Require department toggle */}
            <div className="pt-4 border-t border-rule">
              <label className="flex items-start gap-3 cursor-pointer">
                <input
                  type="checkbox"
                  checked={requireDepartment}
                  onChange={(e) => setRequireDepartment(e.target.checked)}
                  className="w-4 h-4 mt-0.5 accent-loris-brown"
                />
                <div>
                  <span className="font-serif text-sm text-ink-primary">
                    Require department on questions
                  </span>
                  <p className="font-mono text-[10px] text-ink-tertiary mt-1">
                    Users must select a department before submitting.
                  </p>
                </div>
              </label>
            </div>

            {/* Save */}
            <div className="flex items-center gap-4 mt-4">
              <button
                onClick={handleSave}
                disabled={isSaving || !hasChanges}
                className="btn-primary disabled:opacity-50"
              >
                {isSaving ? 'Saving...' : 'Save Changes'}
              </button>
              {hasChanges && (
                <span className="font-mono text-xs text-status-warning">Unsaved</span>
              )}
            </div>
          </div>
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* GDrive Integration Settings */}
          <div className="card-tufte">
            <GDriveSettingsPanel />
          </div>

          {/* MoltenLoris Sync Settings */}
          <div className="card-tufte">
            <MoltenLorisSettingsPanel />
          </div>
        </div>
      </div>
    </div>
  )
}
