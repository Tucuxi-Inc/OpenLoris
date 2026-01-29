import { useState, useEffect } from 'react'
import { knowledgeApi, WisdomFact, WisdomTier, FactCreate, SearchResult, KnowledgeStats } from '../../lib/api/knowledge'
import LorisAvatar from '../../components/LorisAvatar'

export default function KnowledgeManagementPage() {
  const [facts, setFacts] = useState<WisdomFact[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [stats, setStats] = useState<KnowledgeStats | null>(null)

  // Filters
  const [tierFilter, setTierFilter] = useState('')
  const [categoryFilter, setCategoryFilter] = useState('')
  const [domainFilter, setDomainFilter] = useState('')

  // Search
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[] | null>(null)
  const [isSearching, setIsSearching] = useState(false)

  // Create form
  const [showCreate, setShowCreate] = useState(false)
  const [newFact, setNewFact] = useState<FactCreate>({
    content: '',
    category: '',
    domain: '',
    tier: 'pending',
    importance: 5,
    is_perpetual: false,
  })

  // Edit
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')

  const [error, setError] = useState('')

  useEffect(() => {
    loadFacts()
    loadStats()
  }, [page, tierFilter, categoryFilter, domainFilter])

  const loadFacts = async () => {
    try {
      setIsLoading(true)
      const params: Record<string, string> = { page: String(page), page_size: '20' }
      if (tierFilter) params.tier = tierFilter
      if (categoryFilter) params.category = categoryFilter
      if (domainFilter) params.domain = domainFilter
      const result = await knowledgeApi.listFacts(params)
      setFacts(result.items)
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load facts:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const loadStats = async () => {
    try {
      const s = await knowledgeApi.getStats()
      setStats(s)
    } catch {
      // non-critical
    }
  }

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }
    try {
      setIsSearching(true)
      const results = await knowledgeApi.search(searchQuery)
      setSearchResults(results)
    } catch (err) {
      console.error('Search failed:', err)
    } finally {
      setIsSearching(false)
    }
  }

  const handleCreate = async () => {
    if (!newFact.content.trim()) return
    try {
      await knowledgeApi.createFact(newFact)
      setShowCreate(false)
      setNewFact({ content: '', category: '', domain: '', tier: 'pending', importance: 5, is_perpetual: false })
      await loadFacts()
      await loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create fact')
    }
  }

  const handleUpdate = async (id: string) => {
    if (!editContent.trim()) return
    try {
      await knowledgeApi.updateFact(id, { content: editContent })
      setEditingId(null)
      await loadFacts()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update')
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Archive this fact?')) return
    try {
      await knowledgeApi.deleteFact(id)
      await loadFacts()
      await loadStats()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to archive')
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl text-ink-primary mb-2">Knowledge Base</h1>
          <p className="font-serif text-ink-secondary">
            Manage wisdom facts that power automated answers and gap analysis.
          </p>
        </div>
        <button onClick={() => setShowCreate(!showCreate)} className="btn-primary">
          {showCreate ? 'Cancel' : 'New Fact'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-6">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-4 gap-6 mb-8">
          <div className="card-tufte text-center">
            <div className="metric-value">{stats.total_facts}</div>
            <div className="metric-label">Total Facts</div>
          </div>
          <div className="card-tufte text-center">
            <div className="metric-value">{stats.by_tier['tier_0a'] || 0}</div>
            <div className="metric-label">Tier 0a (High)</div>
          </div>
          <div className="card-tufte text-center">
            <div className="metric-value">{stats.expiring_soon}</div>
            <div className="metric-label">Expiring Soon</div>
          </div>
          <div className="card-tufte text-center">
            <div className="metric-value">{stats.recently_added}</div>
            <div className="metric-label">Added Recently</div>
          </div>
        </div>
      )}

      {/* Search */}
      <div className="flex gap-3 mb-6">
        <input
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSearch()}
          className="input-tufte flex-1"
          placeholder="Semantic search across knowledge base..."
        />
        <button onClick={handleSearch} disabled={isSearching} className="btn-secondary">
          {isSearching ? 'Searching...' : 'Search'}
        </button>
        {searchResults && (
          <button onClick={() => setSearchResults(null)} className="btn-secondary">
            Clear
          </button>
        )}
      </div>

      {/* Create form */}
      {showCreate && (
        <div className="card-tufte card-elevated mb-6">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Create New Fact
          </h3>
          <div className="space-y-4">
            <div>
              <label className="label-tufte">Content</label>
              <textarea
                value={newFact.content}
                onChange={(e) => setNewFact({ ...newFact, content: e.target.value })}
                className="input-tufte w-full h-32 resize-none"
                placeholder="Enter the knowledge fact..."
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="label-tufte">Category</label>
                <input
                  value={newFact.category}
                  onChange={(e) => setNewFact({ ...newFact, category: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="e.g., Contracts"
                />
              </div>
              <div>
                <label className="label-tufte">Domain</label>
                <input
                  value={newFact.domain}
                  onChange={(e) => setNewFact({ ...newFact, domain: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="e.g., Corporate Law"
                />
              </div>
              <div>
                <label className="label-tufte">Tier</label>
                <select
                  value={newFact.tier}
                  onChange={(e) => setNewFact({ ...newFact, tier: e.target.value as WisdomTier })}
                  className="input-tufte w-full"
                >
                  <option value="pending">Pending</option>
                  <option value="tier_0a">Tier 0a (High Confidence)</option>
                  <option value="tier_0b">Tier 0b (Medium)</option>
                  <option value="tier_0c">Tier 0c (Low)</option>
                </select>
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="label-tufte">Importance (1-10)</label>
                <input
                  type="number"
                  min="1"
                  max="10"
                  value={newFact.importance}
                  onChange={(e) => setNewFact({ ...newFact, importance: parseInt(e.target.value) || 5 })}
                  className="input-tufte w-full"
                />
              </div>
              <div>
                <label className="label-tufte">Good Until Date</label>
                <input
                  type="date"
                  value={newFact.good_until_date || ''}
                  onChange={(e) => setNewFact({ ...newFact, good_until_date: e.target.value || undefined })}
                  className="input-tufte w-full"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={newFact.is_perpetual}
                    onChange={(e) => setNewFact({ ...newFact, is_perpetual: e.target.checked })}
                  />
                  <span className="font-serif text-sm text-ink-secondary">Perpetual (no expiry)</span>
                </label>
              </div>
            </div>
            <button
              onClick={handleCreate}
              disabled={!newFact.content.trim()}
              className="btn-primary disabled:opacity-50"
            >
              Create Fact
            </button>
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="flex items-center gap-4 mb-6">
        <select
          value={tierFilter}
          onChange={(e) => { setTierFilter(e.target.value); setPage(1) }}
          className="input-tufte text-sm"
        >
          <option value="">All tiers</option>
          <option value="tier_0a">Tier 0a</option>
          <option value="tier_0b">Tier 0b</option>
          <option value="tier_0c">Tier 0c</option>
          <option value="pending">Pending</option>
          <option value="archived">Archived</option>
        </select>
        <input
          value={categoryFilter}
          onChange={(e) => { setCategoryFilter(e.target.value); setPage(1) }}
          className="input-tufte text-sm"
          placeholder="Filter by category..."
        />
        <input
          value={domainFilter}
          onChange={(e) => { setDomainFilter(e.target.value); setPage(1) }}
          className="input-tufte text-sm"
          placeholder="Filter by domain..."
        />
      </div>

      {/* Search results */}
      {searchResults && (
        <div className="mb-8">
          <h2 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Search Results ({searchResults.length})
          </h2>
          {searchResults.length > 0 ? (
            <div className="space-y-3">
              {searchResults.map((result) => (
                <div key={result.fact.id} className="card-tufte">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs text-ink-secondary uppercase">{result.fact.tier}</span>
                      {result.fact.category && (
                        <>
                          <span className="text-ink-muted">·</span>
                          <span className="font-mono text-xs text-ink-secondary">{result.fact.category}</span>
                        </>
                      )}
                    </div>
                    <span className="font-mono text-xs text-status-success">
                      {Math.round(result.similarity * 100)}% match
                    </span>
                  </div>
                  <p className="font-serif text-sm text-ink-primary leading-relaxed">
                    {result.fact.content}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <div className="card-tufte text-center py-6">
              <p className="font-serif text-ink-secondary">No matching facts found.</p>
            </div>
          )}
        </div>
      )}

      {/* Facts list */}
      {!searchResults && (
        isLoading ? (
          <div className="card-tufte text-center py-12">
            <LorisAvatar mood="studying" size="lg" animate className="mx-auto mb-4" />
            <p className="font-serif text-ink-secondary">Loading facts...</p>
          </div>
        ) : (
          <>
            <div className="space-y-3">
              {facts.map((fact) => (
                <div key={fact.id} className="card-tufte">
                  {editingId === fact.id ? (
                    <div>
                      <textarea
                        value={editContent}
                        onChange={(e) => setEditContent(e.target.value)}
                        className="input-tufte w-full h-24 resize-none mb-3"
                      />
                      <div className="flex gap-2">
                        <button onClick={() => handleUpdate(fact.id)} className="btn-primary text-sm">Save</button>
                        <button onClick={() => setEditingId(null)} className="btn-secondary text-sm">Cancel</button>
                      </div>
                    </div>
                  ) : (
                    <>
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <span className="font-mono text-xs text-ink-secondary uppercase">{fact.tier}</span>
                          {fact.category && (
                            <>
                              <span className="text-ink-muted">·</span>
                              <span className="font-mono text-xs text-ink-secondary">{fact.category}</span>
                            </>
                          )}
                          {fact.domain && (
                            <>
                              <span className="text-ink-muted">·</span>
                              <span className="font-mono text-xs text-ink-tertiary">{fact.domain}</span>
                            </>
                          )}
                        </div>
                        <div className="flex items-center gap-3">
                          {fact.good_until_date && (
                            <span className="font-mono text-xs text-ink-muted">
                              GUD: {new Date(fact.good_until_date).toLocaleDateString()}
                            </span>
                          )}
                          {fact.is_perpetual && (
                            <span className="font-mono text-xs text-status-success">Perpetual</span>
                          )}
                          <span className="font-mono text-xs text-ink-muted">
                            Used {fact.usage_count}x
                          </span>
                        </div>
                      </div>
                      <p className="font-serif text-sm text-ink-primary leading-relaxed mb-3">
                        {fact.content}
                      </p>
                      <div className="flex gap-3">
                        <button
                          onClick={() => { setEditingId(fact.id); setEditContent(fact.content) }}
                          className="font-serif text-xs text-ink-secondary hover:text-ink-primary"
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleDelete(fact.id)}
                          className="font-serif text-xs text-status-error hover:text-ink-primary"
                        >
                          Archive
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
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

            {facts.length === 0 && (
              <div className="card-tufte text-center py-12">
                <LorisAvatar mood="scholar" size="lg" className="mx-auto mb-4" />
                <p className="font-serif text-ink-secondary mb-4">
                  No knowledge facts yet.
                </p>
                <button onClick={() => setShowCreate(true)} className="btn-secondary">
                  Create Your First Fact
                </button>
              </div>
            )}
          </>
        )
      )}
    </div>
  )
}
