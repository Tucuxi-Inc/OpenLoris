import { apiClient } from './client'

export type ParsingStatus = 'pending' | 'processing' | 'completed' | 'failed'
export type ExtractionStatus = 'pending' | 'extracting' | 'completed' | 'failed' | 'partial'
export type ValidationStatus = 'pending' | 'approved' | 'rejected' | 'needs_review'

export interface KnowledgeDocument {
  id: string
  organization_id: string
  uploaded_by_id: string
  original_filename: string
  title: string | null
  description: string | null
  file_size_bytes: number | null
  file_type: string | null
  domain: string | null
  topics: string[]
  tags: string[]
  document_type: string | null
  parsing_status: ParsingStatus
  extraction_status: ExtractionStatus
  extracted_facts_count: number
  validated_facts_count: number
  good_until_date: string | null
  is_perpetual: boolean
  auto_delete_on_expiry: boolean
  department: string | null
  responsible_person: string | null
  responsible_email: string | null
  content_quality_score: number | null
  is_active: boolean
  created_at: string
  updated_at: string | null
}

// Backend response shapes
interface DocumentListApiResponse {
  documents: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface DocumentListResponse {
  items: KnowledgeDocument[]
  total: number
  page: number
  page_size: number
}

interface CandidatesApiResponse {
  candidates: ExtractedFactCandidate[]
  total: number
}

export interface ExtractedFactCandidate {
  id: string
  document_id: string
  fact_text: string
  suggested_domain: string | null
  extraction_confidence: number
  validation_status: ValidationStatus
  validated_by: string | null
  created_at: string
}

export interface Department {
  id: string
  name: string
  contact_email: string | null
  is_active: boolean
}

export const documentsApi = {
  // Upload — uses FormData, not JSON
  upload: async (file: File, metadata: {
    domain?: string
    department?: string
    responsible_person?: string
    responsible_email?: string
    good_until_date?: string
    is_perpetual?: boolean
    auto_delete_on_expiry?: boolean
  }) => {
    const formData = new FormData()
    formData.append('file', file)
    if (metadata.domain) formData.append('domain', metadata.domain)
    if (metadata.department) formData.append('department', metadata.department)
    if (metadata.responsible_person) formData.append('responsible_person', metadata.responsible_person)
    if (metadata.responsible_email) formData.append('responsible_email', metadata.responsible_email)
    if (metadata.good_until_date) formData.append('good_until_date', metadata.good_until_date)
    if (metadata.is_perpetual !== undefined) formData.append('is_perpetual', String(metadata.is_perpetual))
    if (metadata.auto_delete_on_expiry !== undefined) formData.append('auto_delete_on_expiry', String(metadata.auto_delete_on_expiry))

    const token = localStorage.getItem('access_token')
    const response = await fetch('/api/v1/documents/upload', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!response.ok) {
      const err = await response.json().catch(() => ({ detail: 'Upload failed' }))
      throw new Error(err.detail || `HTTP error ${response.status}`)
    }
    return response.json() as Promise<KnowledgeDocument>
  },

  // CRUD
  list: async (params?: { parsing_status?: string; domain?: string; page?: number; page_size?: number }): Promise<DocumentListResponse> => {
    const raw = await apiClient.get<DocumentListApiResponse>('/api/v1/documents/', { params: params as Record<string, string> })
    return { items: raw.documents, total: raw.total, page: raw.page, page_size: raw.page_size }
  },

  get: (id: string) =>
    apiClient.get<KnowledgeDocument>(`/api/v1/documents/${id}`),

  update: (id: string, data: Partial<Pick<KnowledgeDocument, 'domain' | 'department' | 'responsible_person' | 'responsible_email' | 'good_until_date' | 'is_perpetual' | 'auto_delete_on_expiry' | 'tags'>>) =>
    apiClient.put<KnowledgeDocument>(`/api/v1/documents/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/api/v1/documents/${id}`),

  // Extraction
  extractFacts: (id: string) =>
    apiClient.post(`/api/v1/documents/${id}/extract`),

  getCandidates: async (id: string): Promise<ExtractedFactCandidate[]> => {
    const raw = await apiClient.get<CandidatesApiResponse>(`/api/v1/documents/${id}/facts`)
    return raw.candidates
  },

  approveCandidate: (candidateId: string, data?: { modified_text?: string; domain?: string; importance?: number }) =>
    apiClient.post(`/api/v1/documents/facts/${candidateId}/approve`, data),

  rejectCandidate: (candidateId: string, reason?: string) =>
    apiClient.post(`/api/v1/documents/facts/${candidateId}/reject`, { reason: reason || 'Rejected by expert' }),

  bulkApprove: (documentId: string, options?: { min_confidence?: number; max_count?: number }) =>
    apiClient.post<{ approved: number; errors: number; error_messages: string[] }>(
      `/api/v1/documents/${documentId}/approve-all`,
      options || {}
    ),

  // GUD
  extendGud: (id: string, data: { new_good_until_date?: string; is_perpetual?: boolean }) =>
    apiClient.post(`/api/v1/documents/${id}/extend`, data),

  getExpiring: async (days?: number): Promise<KnowledgeDocument[]> => {
    const raw = await apiClient.get<{ documents: KnowledgeDocument[]; total: number }>('/api/v1/documents/expiring/list', {
      params: days ? { days: String(days) } : undefined,
    })
    return raw.documents
  },

  // Departments
  getDepartments: async (): Promise<Department[]> => {
    const raw = await apiClient.get<{ departments: Department[] }>('/api/v1/documents/departments/list')
    return raw.departments
  },

  createDepartment: (data: { name: string; contact_email?: string }) =>
    apiClient.post<Department>('/api/v1/documents/departments', data),
}
