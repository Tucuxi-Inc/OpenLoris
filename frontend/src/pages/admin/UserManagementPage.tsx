import { useState, useEffect } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { usersApi, UserListItem, UserRole, UserCreateData, UserEditData } from '../../lib/api/users'

type ModalMode = 'closed' | 'create' | 'edit'

export default function UserManagementPage() {
  const { isAdmin } = useAuth()
  const [users, setUsers] = useState<UserListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [roleFilter, setRoleFilter] = useState<UserRole | ''>('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Modal state
  const [modalMode, setModalMode] = useState<ModalMode>('closed')
  const [editingUser, setEditingUser] = useState<UserListItem | null>(null)
  const [formData, setFormData] = useState({ email: '', name: '', password: '', role: 'business_user' as UserRole, department: '', title: '' })
  const [formError, setFormError] = useState('')
  const [isSaving, setIsSaving] = useState(false)

  // Delete confirmation
  const [deletingUser, setDeletingUser] = useState<UserListItem | null>(null)

  useEffect(() => {
    loadUsers()
  }, [page, roleFilter])

  const loadUsers = async () => {
    try {
      setIsLoading(true)
      const params: Record<string, string> = { page: String(page), page_size: '20' }
      if (roleFilter) params.role = roleFilter
      const result = await usersApi.list(params as { role?: UserRole; page?: number; page_size?: number })
      setUsers(result.users)
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load users:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRoleChange = async (userId: string, newRole: UserRole) => {
    try {
      setError('')
      await usersApi.updateRole(userId, newRole)
      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update role')
    }
  }

  const handleStatusChange = async (userId: string, isActive: boolean) => {
    try {
      setError('')
      await usersApi.updateStatus(userId, isActive)
      await loadUsers()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update status')
    }
  }

  const openCreate = () => {
    setFormData({ email: '', name: '', password: '', role: 'business_user', department: '', title: '' })
    setFormError('')
    setEditingUser(null)
    setModalMode('create')
  }

  const openEdit = (user: UserListItem) => {
    setFormData({ email: user.email, name: user.name, password: '', role: user.role, department: user.department || '', title: user.title || '' })
    setFormError('')
    setEditingUser(user)
    setModalMode('edit')
  }

  const closeModal = () => {
    setModalMode('closed')
    setEditingUser(null)
    setFormError('')
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    setIsSaving(true)

    try {
      if (modalMode === 'create') {
        if (!formData.email || !formData.name || !formData.password) {
          setFormError('Email, name, and password are required.')
          setIsSaving(false)
          return
        }
        const createData: UserCreateData = {
          email: formData.email,
          name: formData.name,
          password: formData.password,
          role: formData.role,
          department: formData.department || undefined,
          title: formData.title || undefined,
        }
        await usersApi.create(createData)
        setSuccess('User created successfully.')
      } else if (modalMode === 'edit' && editingUser) {
        const editData: UserEditData = {}
        if (formData.name !== editingUser.name) editData.name = formData.name
        if (formData.email !== editingUser.email) editData.email = formData.email
        if (formData.department !== (editingUser.department || '')) editData.department = formData.department
        if (formData.title !== (editingUser.title || '')) editData.title = formData.title
        await usersApi.edit(editingUser.id, editData)
        setSuccess('User updated successfully.')
      }
      closeModal()
      await loadUsers()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setFormError(err instanceof Error ? err.message : 'Operation failed')
    } finally {
      setIsSaving(false)
    }
  }

  const handleDelete = async () => {
    if (!deletingUser) return
    try {
      setError('')
      await usersApi.delete(deletingUser.id)
      setDeletingUser(null)
      setSuccess('User deleted.')
      await loadUsers()
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete user')
      setDeletingUser(null)
    }
  }

  const getRoleStyle = (role: UserRole) => {
    switch (role) {
      case 'admin': return 'text-status-error'
      case 'domain_expert': return 'text-status-warning'
      default: return 'text-ink-tertiary'
    }
  }

  const getRoleLabel = (role: UserRole) => {
    switch (role) {
      case 'admin': return 'Admin'
      case 'domain_expert': return 'Expert'
      case 'business_user': return 'User'
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      {/* Header */}
      <div className="flex items-start justify-between mb-8">
        <div>
          <h1 className="text-3xl text-ink-primary mb-2">User Management</h1>
          <p className="font-serif text-ink-secondary">
            Manage users, roles, and access in your organization.
          </p>
        </div>
        {isAdmin && (
          <button onClick={openCreate} className="btn-primary">
            + Create User
          </button>
        )}
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

      {/* Filter */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={roleFilter}
          onChange={(e) => { setRoleFilter(e.target.value as UserRole | ''); setPage(1) }}
          className="input-tufte text-sm"
        >
          <option value="">All roles</option>
          <option value="business_user">Business Users</option>
          <option value="domain_expert">Experts</option>
          <option value="admin">Admins</option>
        </select>
        <span className="font-mono text-xs text-ink-tertiary">{total} users</span>
      </div>

      {isLoading ? (
        <div className="card-tufte text-center py-12">
          <p className="font-serif text-ink-secondary">Loading users...</p>
        </div>
      ) : (
        <>
          {/* Users table */}
          <div className="card-tufte overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-rule-light">
                  <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Name</th>
                  <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Email</th>
                  <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Role</th>
                  <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Department</th>
                  <th className="text-left py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Status</th>
                  {isAdmin && (
                    <th className="text-right py-3 px-4 font-mono text-xs text-ink-tertiary uppercase">Actions</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} className="border-b border-rule-light last:border-0">
                    <td className="py-3 px-4 font-serif text-sm text-ink-primary">{u.name}</td>
                    <td className="py-3 px-4 font-mono text-xs text-ink-secondary">{u.email}</td>
                    <td className="py-3 px-4">
                      <span className={`font-mono text-xs uppercase ${getRoleStyle(u.role)}`}>
                        {getRoleLabel(u.role)}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-serif text-sm text-ink-secondary">
                      {u.department || '—'}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`font-mono text-xs ${u.is_active ? 'text-status-success' : 'text-status-error'}`}>
                        {u.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                    {isAdmin && (
                      <td className="py-3 px-4 text-right">
                        <div className="flex items-center justify-end gap-2 flex-wrap">
                          <select
                            value={u.role}
                            onChange={(e) => handleRoleChange(u.id, e.target.value as UserRole)}
                            className="input-tufte text-xs py-1"
                          >
                            <option value="business_user">User</option>
                            <option value="domain_expert">Expert</option>
                            <option value="admin">Admin</option>
                          </select>
                          <span className="text-rule-light">|</span>
                          <button
                            onClick={() => openEdit(u)}
                            className="font-mono text-xs text-ink-secondary hover:text-ink-primary underline"
                          >
                            Edit
                          </button>
                          <button
                            onClick={() => handleStatusChange(u.id, !u.is_active)}
                            className={`font-mono text-xs ${
                              u.is_active ? 'text-status-warning' : 'text-status-success'
                            } hover:text-ink-primary underline`}
                          >
                            {u.is_active ? 'Deactivate' : 'Activate'}
                          </button>
                          <button
                            onClick={() => setDeletingUser(u)}
                            className="font-mono text-xs text-status-error hover:text-ink-primary underline"
                          >
                            Delete
                          </button>
                        </div>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-center gap-4 mt-8">
              <button
                onClick={() => setPage(p => Math.max(1, p - 1))}
                disabled={page === 1}
                className="btn-secondary disabled:opacity-50"
              >
                Previous
              </button>
              <span className="font-mono text-xs text-ink-tertiary">
                Page {page} of {totalPages}
              </span>
              <button
                onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                disabled={page === totalPages}
                className="btn-secondary disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}

          {users.length === 0 && (
            <div className="card-tufte text-center py-12">
              <p className="font-serif text-ink-secondary">No users found.</p>
            </div>
          )}
        </>
      )}

      {/* Create / Edit Modal */}
      {modalMode !== 'closed' && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-md border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-6">
              {modalMode === 'create' ? 'Create User' : 'Edit User'}
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
                  required
                />
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData(d => ({ ...d, email: e.target.value }))}
                  className="input-tufte w-full"
                  required
                />
              </div>

              {modalMode === 'create' && (
                <>
                  <div>
                    <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Password</label>
                    <input
                      type="password"
                      value={formData.password}
                      onChange={(e) => setFormData(d => ({ ...d, password: e.target.value }))}
                      className="input-tufte w-full"
                      required
                    />
                  </div>

                  <div>
                    <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Role</label>
                    <select
                      value={formData.role}
                      onChange={(e) => setFormData(d => ({ ...d, role: e.target.value as UserRole }))}
                      className="input-tufte w-full"
                    >
                      <option value="business_user">Business User</option>
                      <option value="domain_expert">Domain Expert</option>
                      <option value="admin">Admin</option>
                    </select>
                  </div>
                </>
              )}

              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Department</label>
                <input
                  type="text"
                  value={formData.department}
                  onChange={(e) => setFormData(d => ({ ...d, department: e.target.value }))}
                  className="input-tufte w-full"
                  placeholder="Optional"
                />
              </div>

              <div>
                <label className="block font-mono text-xs text-ink-tertiary uppercase mb-1">Title</label>
                <input
                  type="text"
                  value={formData.title}
                  onChange={(e) => setFormData(d => ({ ...d, title: e.target.value }))}
                  className="input-tufte w-full"
                  placeholder="Optional"
                />
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-rule-light">
                <button type="button" onClick={closeModal} className="btn-secondary">
                  Cancel
                </button>
                <button type="submit" disabled={isSaving} className="btn-primary disabled:opacity-50">
                  {isSaving ? 'Saving...' : modalMode === 'create' ? 'Create User' : 'Save Changes'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deletingUser && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="bg-cream-50 rounded-sm shadow-lg p-8 w-full max-w-sm border border-rule-light">
            <h2 className="text-xl text-ink-primary mb-4">Delete User</h2>
            <p className="font-serif text-sm text-ink-secondary mb-6">
              Are you sure you want to delete <strong>{deletingUser.name}</strong> ({deletingUser.email})?
              This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button onClick={() => setDeletingUser(null)} className="btn-secondary">
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-status-error text-cream-50 rounded-sm font-mono text-sm hover:opacity-90"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
