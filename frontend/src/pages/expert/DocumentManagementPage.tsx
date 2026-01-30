import { useState, useEffect } from 'react'
import { documentsApi, KnowledgeDocument, ExtractedFactCandidate } from '../../lib/api/documents'
import LorisAvatar from '../../components/LorisAvatar'

export default function DocumentManagementPage() {
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState('')

  // Upload form
  const [showUpload, setShowUpload] = useState(false)
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploadMeta, setUploadMeta] = useState({
    domain: '',
    department: '',
    responsible_person: '',
    responsible_email: '',
    good_until_date: '',
    is_perpetual: false,
    auto_delete_on_expiry: false,
  })
  const [isUploading, setIsUploading] = useState(false)

  // Detail view
  const [selectedDoc, setSelectedDoc] = useState<KnowledgeDocument | null>(null)
  const [candidates, setCandidates] = useState<ExtractedFactCandidate[]>([])
  const [loadingCandidates, setLoadingCandidates] = useState(false)

  useEffect(() => {
    loadDocuments()
  }, [page])

  const loadDocuments = async () => {
    try {
      setIsLoading(true)
      const result = await documentsApi.list({ page, page_size: 20 })
      setDocuments(result.items)
      setTotal(result.total)
    } catch (err) {
      console.error('Failed to load documents:', err)
    } finally {
      setIsLoading(false)
    }
  }

  const handleUpload = async () => {
    if (!uploadFile) return
    try {
      setIsUploading(true)
      setError('')
      await documentsApi.upload(uploadFile, uploadMeta)
      setShowUpload(false)
      setUploadFile(null)
      setUploadMeta({ domain: '', department: '', responsible_person: '', responsible_email: '', good_until_date: '', is_perpetual: false, auto_delete_on_expiry: false })
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setIsUploading(false)
    }
  }

  const handleExtract = async (docId: string) => {
    try {
      await documentsApi.extractFacts(docId)
      await loadDocuments()
      if (selectedDoc?.id === docId) {
        await loadCandidates(docId)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Extraction failed')
    }
  }

  const loadCandidates = async (docId: string) => {
    try {
      setLoadingCandidates(true)
      const result = await documentsApi.getCandidates(docId)
      setCandidates(result)
    } catch (err) {
      console.error('Failed to load candidates:', err)
    } finally {
      setLoadingCandidates(false)
    }
  }

  const handleSelectDoc = async (doc: KnowledgeDocument) => {
    setSelectedDoc(doc)
    await loadCandidates(doc.id)
  }

  const handleApprove = async (candidateId: string) => {
    try {
      await documentsApi.approveCandidate(candidateId)
      if (selectedDoc) await loadCandidates(selectedDoc.id)
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Approval failed')
    }
  }

  const handleReject = async (candidateId: string) => {
    const reason = prompt('Rejection reason (optional):')
    try {
      await documentsApi.rejectCandidate(candidateId, reason || undefined)
      if (selectedDoc) await loadCandidates(selectedDoc.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Rejection failed')
    }
  }

  const handleBulkApprove = async (docId: string, minConfidence: number = 0.5) => {
    const pendingCount = candidates.filter(c => c.validation_status === 'pending' && c.extraction_confidence >= minConfidence).length
    if (!confirm(`Approve ${pendingCount} facts with confidence >= ${Math.round(minConfidence * 100)}%?`)) return
    try {
      const result = await documentsApi.bulkApprove(docId, { min_confidence: minConfidence })
      await loadDocuments()
      if (selectedDoc) await loadCandidates(selectedDoc.id)
      alert(`Approved ${result.approved} facts${result.errors > 0 ? `, ${result.errors} errors` : ''}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Bulk approval failed')
    }
  }

  const handleExtendGud = async (docId: string) => {
    const newDate = prompt('New good-until date (YYYY-MM-DD):')
    if (!newDate) return
    try {
      await documentsApi.extendGud(docId, { new_good_until_date: newDate })
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to extend')
    }
  }

  const handleDelete = async (docId: string) => {
    if (!confirm('Delete this document?')) return
    try {
      await documentsApi.delete(docId)
      if (selectedDoc?.id === docId) {
        setSelectedDoc(null)
        setCandidates([])
      }
      await loadDocuments()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const getStatusStyle = (status: string) => {
    switch (status) {
      case 'completed': return 'text-status-success'
      case 'failed': return 'text-status-error'
      case 'processing': case 'extracting': return 'text-status-warning'
      default: return 'text-ink-tertiary'
    }
  }

  const totalPages = Math.ceil(total / 20)

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl text-ink-primary mb-2">Documents</h1>
          <p className="font-serif text-ink-secondary">
            Upload, parse, and extract knowledge from documents.
          </p>
        </div>
        <button onClick={() => setShowUpload(!showUpload)} className="btn-primary">
          {showUpload ? 'Cancel' : 'Upload Document'}
        </button>
      </div>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-6">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}

      {/* Upload form */}
      {showUpload && (
        <div className="card-tufte card-elevated mb-6">
          <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
            Upload Document
          </h3>
          <div className="space-y-4">
            <div>
              <label className="label-tufte">File (PDF, DOCX, or TXT)</label>
              <input
                type="file"
                accept=".pdf,.docx,.txt"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="input-tufte w-full"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-tufte">Domain</label>
                <input
                  value={uploadMeta.domain}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, domain: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="e.g., Corporate Law"
                />
              </div>
              <div>
                <label className="label-tufte">Department</label>
                <input
                  value={uploadMeta.department}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, department: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="e.g., Legal"
                />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="label-tufte">Responsible Person</label>
                <input
                  value={uploadMeta.responsible_person}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, responsible_person: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="Name"
                />
              </div>
              <div>
                <label className="label-tufte">Responsible Email</label>
                <input
                  type="email"
                  value={uploadMeta.responsible_email}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, responsible_email: e.target.value })}
                  className="input-tufte w-full"
                  placeholder="email@company.com"
                />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div>
                <label className="label-tufte">Good Until Date</label>
                <input
                  type="date"
                  value={uploadMeta.good_until_date}
                  onChange={(e) => setUploadMeta({ ...uploadMeta, good_until_date: e.target.value })}
                  className="input-tufte w-full"
                />
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={uploadMeta.is_perpetual}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, is_perpetual: e.target.checked })}
                  />
                  <span className="font-serif text-sm text-ink-secondary">Perpetual</span>
                </label>
              </div>
              <div className="flex items-end">
                <label className="flex items-center gap-2">
                  <input
                    type="checkbox"
                    checked={uploadMeta.auto_delete_on_expiry}
                    onChange={(e) => setUploadMeta({ ...uploadMeta, auto_delete_on_expiry: e.target.checked })}
                  />
                  <span className="font-serif text-sm text-ink-secondary">Auto-delete on expiry</span>
                </label>
              </div>
            </div>
            <button
              onClick={handleUpload}
              disabled={!uploadFile || isUploading}
              className="btn-primary disabled:opacity-50"
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </button>
          </div>
        </div>
      )}

      {/* Two-column layout: documents list + detail */}
      <div className="grid grid-cols-2 gap-8">
        {/* Documents list */}
        <div>
          {isLoading ? (
            <div className="card-tufte text-center py-12">
              <LorisAvatar mood="detective" size="lg" animate className="mx-auto mb-4" />
              <p className="font-serif text-ink-secondary">Loading documents...</p>
            </div>
          ) : documents.length > 0 ? (
            <div className="space-y-3">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  onClick={() => handleSelectDoc(doc)}
                  className={`card-tufte cursor-pointer hover:border-rule-medium transition-colors ${
                    selectedDoc?.id === doc.id ? 'border-loris-brown' : ''
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="font-serif text-sm text-ink-primary font-medium truncate">
                      {doc.original_filename}
                    </span>
                    <span className={`font-mono text-xs ${getStatusStyle(doc.parsing_status)}`}>
                      {doc.parsing_status}
                    </span>
                  </div>
                  <div className="flex items-center gap-3">
                    {doc.domain && (
                      <span className="font-mono text-xs text-ink-secondary">{doc.domain}</span>
                    )}
                    <span className="font-mono text-xs text-ink-muted">
                      {doc.extracted_facts_count} facts
                    </span>
                    {doc.good_until_date && (
                      <span className="font-mono text-xs text-ink-muted">
                        GUD: {new Date(doc.good_until_date).toLocaleDateString()}
                      </span>
                    )}
                  </div>
                </div>
              ))}

              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-4 mt-4">
                  <button
                    onClick={() => setPage(p => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="btn-secondary text-sm disabled:opacity-50"
                  >
                    Prev
                  </button>
                  <span className="font-mono text-xs text-ink-tertiary">{page}/{totalPages}</span>
                  <button
                    onClick={() => setPage(p => Math.min(totalPages, p + 1))}
                    disabled={page === totalPages}
                    className="btn-secondary text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              )}
            </div>
          ) : (
            <div className="card-tufte text-center py-12">
              <LorisAvatar mood="studying" size="lg" className="mx-auto mb-4" />
              <p className="font-serif text-ink-secondary mb-4">No documents uploaded yet.</p>
              <button onClick={() => setShowUpload(true)} className="btn-secondary">
                Upload First Document
              </button>
            </div>
          )}
        </div>

        {/* Document detail */}
        <div>
          {selectedDoc ? (
            <div>
              <div className="card-tufte mb-4">
                <h3 className="font-serif text-lg text-ink-primary mb-3">{selectedDoc.original_filename}</h3>
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="font-mono text-xs text-ink-tertiary">Parsing</span>
                    <span className={`font-mono text-xs ${getStatusStyle(selectedDoc.parsing_status)}`}>
                      {selectedDoc.parsing_status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono text-xs text-ink-tertiary">Extraction</span>
                    <span className={`font-mono text-xs ${getStatusStyle(selectedDoc.extraction_status)}`}>
                      {selectedDoc.extraction_status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="font-mono text-xs text-ink-tertiary">Facts</span>
                    <span className="font-mono text-xs text-ink-primary">
                      {selectedDoc.validated_facts_count} / {selectedDoc.extracted_facts_count}
                    </span>
                  </div>
                  {selectedDoc.domain && (
                    <div className="flex justify-between">
                      <span className="font-mono text-xs text-ink-tertiary">Domain</span>
                      <span className="font-mono text-xs text-ink-primary">{selectedDoc.domain}</span>
                    </div>
                  )}
                  {selectedDoc.good_until_date && (
                    <div className="flex justify-between">
                      <span className="font-mono text-xs text-ink-tertiary">Good Until</span>
                      <span className="font-mono text-xs text-ink-primary">
                        {new Date(selectedDoc.good_until_date).toLocaleDateString()}
                      </span>
                    </div>
                  )}
                  {selectedDoc.is_perpetual && (
                    <div className="flex justify-between">
                      <span className="font-mono text-xs text-ink-tertiary">Expiry</span>
                      <span className="font-mono text-xs text-status-success">Perpetual</span>
                    </div>
                  )}
                </div>

                <hr className="my-4" />
                <div className="flex flex-wrap gap-3">
                  {selectedDoc.parsing_status === 'completed' && selectedDoc.extraction_status !== 'completed' && (
                    <button
                      onClick={() => handleExtract(selectedDoc.id)}
                      className="btn-secondary text-sm"
                    >
                      Extract Facts
                    </button>
                  )}
                  {selectedDoc.extraction_status === 'completed' && candidates.some(c => c.validation_status === 'pending') && (
                    <>
                      <button
                        onClick={() => handleBulkApprove(selectedDoc.id, 0.7)}
                        className="btn-primary text-sm"
                      >
                        Approve All (≥70%)
                      </button>
                      <button
                        onClick={() => handleBulkApprove(selectedDoc.id, 0.5)}
                        className="btn-secondary text-sm"
                      >
                        Approve All (≥50%)
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => handleExtendGud(selectedDoc.id)}
                    className="btn-secondary text-sm"
                  >
                    Extend GUD
                  </button>
                  <button
                    onClick={() => handleDelete(selectedDoc.id)}
                    className="font-serif text-xs text-status-error hover:text-ink-primary"
                  >
                    Delete
                  </button>
                </div>
              </div>

              {/* Extracted fact candidates */}
              <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-3">
                Extracted Facts
              </h3>
              {loadingCandidates ? (
                <p className="font-serif text-sm text-ink-secondary">Loading...</p>
              ) : candidates.length > 0 ? (
                <div className="space-y-3">
                  {candidates.map((c) => (
                    <div key={c.id} className="card-tufte">
                      <div className="flex items-center justify-between mb-2">
                        <span className={`font-mono text-xs ${
                          c.validation_status === 'approved' ? 'text-status-success' :
                          c.validation_status === 'rejected' ? 'text-status-error' :
                          'text-ink-tertiary'
                        }`}>
                          {c.validation_status}
                        </span>
                        <span className="font-mono text-xs text-ink-muted">
                          {Math.round(c.extraction_confidence * 100)}% confidence
                        </span>
                      </div>
                      <p className="font-serif text-sm text-ink-primary leading-relaxed mb-3">
                        {c.fact_text}
                      </p>
                      {c.validation_status === 'pending' && (
                        <div className="flex gap-3">
                          <button
                            onClick={() => handleApprove(c.id)}
                            className="font-serif text-xs text-status-success hover:text-ink-primary"
                          >
                            Approve
                          </button>
                          <button
                            onClick={() => handleReject(c.id)}
                            className="font-serif text-xs text-status-error hover:text-ink-primary"
                          >
                            Reject
                          </button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="card-tufte text-center py-6">
                  <p className="font-serif text-sm text-ink-secondary">
                    {selectedDoc.extraction_status === 'completed'
                      ? 'No facts extracted from this document.'
                      : 'Facts not yet extracted. Click "Extract Facts" above.'}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <div className="card-tufte text-center py-12">
              <LorisAvatar mood="architect" size="lg" className="mx-auto mb-4" />
              <p className="font-serif text-ink-secondary">
                Select a document to view details and manage extracted facts.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
