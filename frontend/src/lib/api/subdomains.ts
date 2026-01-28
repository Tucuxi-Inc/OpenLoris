import { apiClient } from './client'

// ── Types ──────────────────────────────────────────────────────────

export interface SubDomainItem {
  id: string
  name: string
  description: string | null
  sla_hours: number
  is_active: boolean
  created_at: string
  expert_count: number
}

export interface ExpertBrief {
  id: string
  name: string
  email: string
}

export interface SubDomainDetail extends SubDomainItem {
  experts: ExpertBrief[]
}

export interface SubDomainListResponse {
  items: SubDomainItem[]
  total: number
}

export interface SubDomainCreateData {
  name: string
  description?: string
  sla_hours?: number
}

export interface SubDomainUpdateData {
  name?: string
  description?: string
  sla_hours?: number
  is_active?: boolean
}

export interface ReassignmentRequest {
  id: string
  question_id: string
  requested_by_id: string
  requested_by_name: string | null
  current_subdomain_id: string | null
  current_subdomain_name: string | null
  suggested_subdomain_id: string
  suggested_subdomain_name: string | null
  reason: string
  status: 'pending' | 'approved' | 'rejected'
  reviewed_by_id: string | null
  admin_notes: string | null
  created_at: string
}

// ── API methods ────────────────────────────────────────────────────

export const subdomainsApi = {
  list: (activeOnly = false) =>
    apiClient.get<SubDomainListResponse>(
      `/api/v1/subdomains/`,
      { params: activeOnly ? { active_only: 'true' } : undefined }
    ),

  get: (id: string) =>
    apiClient.get<SubDomainDetail>(`/api/v1/subdomains/${id}`),

  create: (data: SubDomainCreateData) =>
    apiClient.post<SubDomainItem>(`/api/v1/subdomains/`, data),

  update: (id: string, data: SubDomainUpdateData) =>
    apiClient.put<SubDomainItem>(`/api/v1/subdomains/${id}`, data),

  deactivate: (id: string) =>
    apiClient.delete(`/api/v1/subdomains/${id}`),

  assignExperts: (id: string, expertIds: string[]) =>
    apiClient.post<SubDomainDetail>(
      `/api/v1/subdomains/${id}/experts`,
      { expert_ids: expertIds }
    ),

  removeExpert: (subdomainId: string, expertId: string) =>
    apiClient.delete(`/api/v1/subdomains/${subdomainId}/experts/${expertId}`),

  listExperts: (id: string) =>
    apiClient.get<ExpertBrief[]>(`/api/v1/subdomains/${id}/experts`),

  // Reassignment
  listReassignments: (statusFilter?: string) => {
    const params: Record<string, string> = {}
    if (statusFilter) params.status_filter = statusFilter
    return apiClient.get<ReassignmentRequest[]>(
      `/api/v1/questions/reassignment-requests`,
      { params: Object.keys(params).length ? params : undefined }
    )
  },

  reviewReassignment: (requestId: string, approved: boolean, adminNotes?: string) =>
    apiClient.put(`/api/v1/questions/reassignment-requests/${requestId}/review`, {
      approved,
      admin_notes: adminNotes || null,
    }),

  requestReassignment: (questionId: string, suggestedSubdomainId: string, reason: string) =>
    apiClient.post(`/api/v1/questions/${questionId}/request-reassignment`, {
      suggested_subdomain_id: suggestedSubdomainId,
      reason,
    }),
}
