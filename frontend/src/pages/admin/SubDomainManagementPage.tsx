import { useState, useEffect } from 'react'
import { subdomainsApi, SubDomainItem, SubDomainDetail, ExpertBrief } from '../../lib/api/subdomains'
import { usersApi, UserListItem } from '../../lib/api/users'

type ModalMode = 'closed' | 'create' | 'edit' | 'experts'

export default function SubDomainManagementPage() {
  const [subdomains, setSubdomains] = useState<SubDomainItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Create/Edit modal
  const [modalMode, setModalMode] = useState<ModalMode>('closed')
  const [editingSD, setEditingSD] = useState<SubDomainItem | null>(null)
  const [formData, setFormData] = useState({ name: '', description: '', sla_hours: '24' })
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Expert assignment modal
  const [assignSD, setAssignSD] = useState<SubDomainDetail | null>(null)
  const [allExperts, setAllExperts] = useState<UserListItem[]>([])
  const [selectedExpertIds, setSelectedExpertIds] = useState<Set<string>>(new Set())

  useEffect(() => { loadSubdomains() }, [])

  const loadSubdomains = async () => {
    try {
      setIsLoading(true)
      const result = await subdomainsApi.list()
      setSubdomains(result.items)
    } catch (err) {
      console.error('Failed to load sub-domains:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const openCreate = () => {
    setFormData({ name: '', description: '', sla_hours: '24' })
    setFormError('')
    setEditingSD(null)
    setModalMode('create')
  }

  const openEdit = (sd: SubDomainItem) => {
    setFormData({
      name: sd.name,
      description: sd.description || '',
      sla_hours: String(sd.sla_hours),
    })
    setFormError('')
    setEditingSD(sd)
    setModalMode('edit')
  }

  const openExperts = async (sd: SubDomainItem) => {
    try {
      const [detail, usersResult] = await Promise.all([
        subdomainsApi.get(sd.id),
        usersApi.list({ role: 'domain_expert' as any, page_size: 100 }),
      ])
      // Also get admins
      const adminsResult = await usersApi.list({ role: 'admin' as any, page_size: 100 })
      setAssignSD(detail)
      setAllExperts([...usersResult.users, ...adminsResult.users])
      setSelectedExpertIds(new Set(detail.experts.map((e: ExpertBrief) => e.id)))
      setModalMode('experts')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load data')
    }
  }

  const closeModal = () => {
    setModalMode('closed')
    setEditingSD(null)
    setAssignSD(null)
    setFormError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setIsSaving(true)

    try {
      if (modalMode === 'create') {
        if (!formData.name.trim()) {
          setFormError('Name is required.')
          setIsSaving(false)
          return
        }
        await subdomainsApi.create({
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
          sla_hours: parseInt(formData.sla_hours) || 24,
        })
        setSuccess('Sub-domain created.')
      } else if (modalMode === 'edit' && editingSD) {
        await subdomainsApi.update(editingSD.id, {
          name: formData.name.trim(),
          description: formData.description.trim() || undefined,
          sla_hours: parseInt(formData.sla_hours) || 24,
        })
        setSuccess('Sub-domain updated.')
      }
      closeModal()
      await loadSubdomains()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setIsSaving(false)
    }
  }

  const handleSaveExperts = async () => {
    if (!assignSD) return
    setIsSaving(true)
    try {
      await subdomainsApi.assignExperts(assignSD.id, Array.from(selectedExpertIds))
      setSuccess('Expert assignments updated.')
      closeModal()
      await loadSubdomains()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save assignments')
    } finally {
      setIsSaving(false)
    }
  }

  const toggleExpert = (id: string) => {
    setSelectedExpertIds(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const handleDeactivate = async (sd: SubDomainItem) => {
    try {
      await subdomainsApi.update(sd.id, { is_active: !sd.is_active })
      await loadSubdomains()
      setSuccess(sd.is_active ? 'Sub-domain deactivated.' : 'Sub-domain activated.')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update')
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl text-ink-primary mb-2">Sub-Domain Management</h1>
          <p className="font-serif text-ink-secondary">
            Create sub-domains and assign domain experts to handle specific question types.
          </p>
        </div>
        <button onClick={openCreate} className="btn-primary">
          + Create Sub-Domain
        </button>
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

      {isLoading ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">Loading sub-domains...</p>
        </div>
      ) : subdomains.length === 0 ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary mb-4">No sub-domains created yet.</p>
          <p className="font-serif text-sm text-ink-tertiary">
            Create sub-domains to route questions to the right experts.
          </p>
        </div>
      ) : (
        <div className="card-tufte overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-rule-light">
                <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Name</th>
                <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Description</th>
                <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">SLA</th>
                <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Experts</th>
                <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Status</th>
                <th className="text-right py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Actions</th>
              </tr>
            </thead>
            <tbody>
              {subdomains.map(sd => (
                <tr key={sd.id} className="border-b border-rule-light last:border-0">
                  <td className="py-3 px-4 font-serif text-sm text-ink-primary">{sd.name}</td>
                  <td className="py-3 px-4 font-serif text-sm text-ink-secondary">
                    {sd.description || '—'}
                  </td>
                  <td className="py-3 px-4 font-mono text-xs text-ink-secondary">
                    {sd.sla_hours}h
                  </td>
                  <td className="py-3 px-4">
                    <button
                      onClick={() => openExperts(sd)}
                      className="font-mono text-xs text-loris-brown hover:text-ink-primary underline"
                    >
                      {sd.expert_count} expert{sd.expert_count !== 1 ? 's' : ''}
                    </button>
                  </td>
                  <td className="py-3 px-4">
                    <span className={`font-mono text-xs ${sd.is_active ? 'text-status-success' : 'text-status-error'}`}>
                      {sd.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </td>
                  <td className="py-3 px-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => openEdit(sd)}
                        className="font-mono text-xs text-ink-secondary hover:text-ink-primary underline"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeactivate(sd)}
                        className={`font-mono text-xs ${sd.is_active ? 'text-status-warning' : 'text-status-success'} hover:text-ink-primary underline`}
                      >
                        {sd.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit Modal */}
      {(modalMode === 'create' || modalMode === 'edit') && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-md border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-6">
              {modalMode === 'create' ? 'Create Sub-Domain' : 'Edit Sub-Domain'}
            </h2>

            {formError && (
              <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-4">
                <p className="font-serif text-sm text-status-error">{formError}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Name</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={(e) => setFormData(d => ({ ...d, name: e.target.value }))}
                  className="input-tufte w-full"
                  placeholder="e.g., Contracts"
                  required
                />
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Description</label>
                <textarea
                  value={formData.description}
                  onChange={(e) => setFormData(d => ({ ...d, description: e.target.value }))}
                  className="input-tufte w-full"
                  rows={3}
                  placeholder="What types of questions does this cover?"
                />
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">
                  SLA (hours)
                </label>
                <input
                  type="number"
                  value={formData.sla_hours}
                  onChange={(e) => setFormData(d => ({ ...d, sla_hours: e.target.value }))}
                  className="input-tufte w-full"
                  min="1"
                />
                <p className="font-mono text-[10px] text-ink-tertiary mt-1">
                  Admin is notified if no expert responds within this time.
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-rule-light">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={isSaving} className="btn-primary disabled:opacity-50">
                  {isSaving ? 'Saving...' : modalMode === 'create' ? 'Create' : 'Save'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Expert Assignment Modal */}
      {modalMode === 'experts' && assignSD && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-lg border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-2">
              Assign Experts to "{assignSD.name}"
            </h2>
            <p className="font-serif text-sm text-ink-secondary mb-6">
              Select experts who should receive questions in this sub-domain.
            </p>

            <div className="max-h-80 overflow-y-auto space-y-2 mb-6">
              {allExperts.length === 0 ? (
                <p className="font-serif text-sm text-ink-tertiary">No experts found.</p>
              ) : (
                allExperts.map(expert => (
                  <label
                    key={expert.id}
                    className="flex items-center gap-3 p-2 hover:bg-cream-100 rounded-sm cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={selectedExpertIds.has(expert.id)}
                      onChange={() => toggleExpert(expert.id)}
                      className="rounded-sm"
                    />
                    <div>
                      <span className="font-serif text-sm text-ink-primary">{expert.name}</span>
                      <span className="font-mono text-xs text-ink-tertiary ml-2">{expert.email}</span>
                      {expert.role === 'admin' && (
                        <span className="font-mono text-[10px] text-status-error ml-2">ADMIN</span>
                      )}
                    </div>
                  </label>
                ))
              )}
            </div>

            <div className="flex justify-between items-center pt-4 border-t border-rule-light">
              <span className="font-mono text-xs text-ink-tertiary">
                {selectedExpertIds.size} selected
              </span>
              <div className="flex gap-3">
                <button onClick={closeModal} className="btn-secondary">
                  Cancel
                </button>
                <button
                  onClick={handleSaveExperts}
                  disabled={isSaving}
                  className="btn-primary disabled:opacity-50"
                >
                  {isSaving ? 'Saving...' : 'Save Assignments'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
