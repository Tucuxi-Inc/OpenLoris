import { apiClient } from './client'

export type WisdomTier = 'tier_0a' | 'tier_0b' | 'tier_0c' | 'pending' | 'archived'

export interface WisdomFact {
  id: string
  organization_id: string
  content: string
  category: string | null
  domain: string | null
  tier: WisdomTier
  confidence_score: number
  importance: number
  good_until_date: string | null
  is_perpetual: boolean
  source_answer_id: string | null
  source_document_id: string | null
  tags: string[]
  jurisdiction: string | null
  contact_person_id: string | null
  usage_count: number
  last_used_at: string | null
  validated_at: string | null
  validated_by_id: string | null
  created_at: string
  updated_at: string | null
}

export interface FactCreate {
  content: string
  category?: string
  domain?: string
  tier?: WisdomTier
  importance?: number
  good_until_date?: string
  is_perpetual?: boolean
  tags?: string[]
  jurisdiction?: string
}

export interface FactUpdate {
  content?: string
  category?: string
  domain?: string
  tier?: WisdomTier
  importance?: number
  good_until_date?: string
  is_perpetual?: boolean
  tags?: string[]
  jurisdiction?: string
}

export interface FactFromAnswer {
  question_id: string
  category?: string
  domain?: string
  tier?: WisdomTier
  importance?: number
}

// Backend response shapes
interface FactListApiResponse {
  facts: WisdomFact[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface FactListResponse {
  items: WisdomFact[]
  total: number
  page: number
  page_size: number
}

interface SearchApiResponse {
  results: SearchResult[]
  total: number
}

export interface SearchResult {
  fact: WisdomFact
  similarity: number
}

interface StatsApiResponse {
  total_facts: number
  tier_counts: Record<string, number>
  domains_covered: string[]
  facts_expiring_soon: number
  average_confidence: number
}

export interface KnowledgeStats {
  total_facts: number
  by_tier: Record<string, number>
  by_domain: Record<string, number>
  expiring_soon: number
  recently_added: number
}

interface ExpiringApiResponse {
  facts: WisdomFact[]
  total: number
}

export interface GapAnalysisResult {
  relevant_knowledge: string[]
  coverage_percentage: number
  identified_gaps: string[]
  proposed_answer: string
  confidence_score: number
  suggested_clarifications: string[]
}

export const knowledgeApi = {
  // Facts CRUD
  listFacts: async (params?: { category?: string; domain?: string; tier?: string; page?: number; page_size?: number }): Promise<FactListResponse> => {
    const raw = await apiClient.get<FactListApiResponse>('/api/v1/knowledge/facts', { params: params as Record<string, string> })
    return { items: raw.facts, total: raw.total, page: raw.page, page_size: raw.page_size }
  },

  getFact: (id: string) =>
    apiClient.get<WisdomFact>(`/api/v1/knowledge/facts/${id}`),

  createFact: (data: FactCreate) =>
    apiClient.post<WisdomFact>('/api/v1/knowledge/facts', data),

  createFromAnswer: (data: FactFromAnswer) =>
    apiClient.post<WisdomFact>('/api/v1/knowledge/facts/from-answer', data),

  updateFact: (id: string, data: FactUpdate) =>
    apiClient.put<WisdomFact>(`/api/v1/knowledge/facts/${id}`, data),

  deleteFact: (id: string) =>
    apiClient.delete(`/api/v1/knowledge/facts/${id}`),

  // Search
  search: async (q: string, limit?: number): Promise<SearchResult[]> => {
    const raw = await apiClient.get<SearchApiResponse>('/api/v1/knowledge/search', {
      params: { q, ...(limit ? { limit: String(limit) } : {}) },
    })
    return raw.results
  },

  // Gap analysis
  analyzeGaps: (text: string) =>
    apiClient.post<GapAnalysisResult>('/api/v1/knowledge/analyze-gaps', { text }),

  // Stats — normalize backend shape to frontend shape
  getStats: async (): Promise<KnowledgeStats> => {
    const raw = await apiClient.get<StatsApiResponse>('/api/v1/knowledge/stats')
    // Convert domains_covered (string[]) to by_domain (Record<string, number>)
    const by_domain: Record<string, number> = {}
    if (raw.domains_covered) {
      for (const d of raw.domains_covered) {
        by_domain[d] = (by_domain[d] || 0) + 1
      }
    }
    return {
      total_facts: raw.total_facts,
      by_tier: raw.tier_counts || {},
      by_domain,
      expiring_soon: raw.facts_expiring_soon || 0,
      recently_added: 0, // backend doesn't track this yet
    }
  },

  // Expiring
  getExpiring: async (days?: number): Promise<WisdomFact[]> => {
    const raw = await apiClient.get<ExpiringApiResponse>('/api/v1/knowledge/expiring', {
      params: days ? { days: String(days) } : undefined,
    })
    return raw.facts
  },
}
