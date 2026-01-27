import { apiClient } from './client'

export interface Question {
  id: string
  original_text: string
  category: string | null
  tags: string[]
  status: QuestionStatus
  priority: QuestionPriority
  asked_by_id: string
  assigned_to_id: string | null
  created_at: string
  first_response_at: string | null
  resolved_at: string | null
  satisfaction_rating: number | null
  gap_analysis?: GapAnalysis | null
}

export type QuestionStatus =
  | 'submitted'
  | 'processing'
  | 'auto_answered'
  | 'human_requested'
  | 'expert_queue'
  | 'in_progress'
  | 'needs_clarification'
  | 'answered'
  | 'resolved'
  | 'closed'

export type QuestionPriority = 'low' | 'normal' | 'high' | 'urgent'

export interface GapAnalysis {
  relevant_knowledge: string[]
  coverage_percentage: number
  identified_gaps: string[]
  proposed_answer: string
  confidence_score: number
  suggested_clarifications: string[]
}

export interface QuestionCreate {
  text: string
  category?: string
  tags?: string[]
  priority?: QuestionPriority
}

export interface Answer {
  id: string
  question_id: string
  content: string
  source: 'expert' | 'ai_approved' | 'ai_edited' | 'automation'
  created_by_id: string
  created_at: string
  delivered_at: string | null
}

export interface PaginatedList<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export const questionsApi = {
  // Business user endpoints
  submit: (data: QuestionCreate) =>
    apiClient.post<Question>('/api/v1/questions/', data),

  list: (params?: { status?: QuestionStatus; page?: number; page_size?: number }) =>
    apiClient.get<PaginatedList<Question>>('/api/v1/questions/', { params: params as Record<string, string> }),

  get: (id: string) =>
    apiClient.get<Question>(`/api/v1/questions/${id}`),

  submitFeedback: (id: string, rating: number, comment?: string) =>
    apiClient.post(`/api/v1/questions/${id}/feedback`, { rating, comment }),

  requestHumanReview: (id: string, message: string) =>
    apiClient.post(`/api/v1/questions/${id}/request-human`, { message }),

  // Expert endpoints
  getQueue: (params?: { category?: string; priority?: QuestionPriority; page?: number }) =>
    apiClient.get<PaginatedList<Question>>('/api/v1/questions/queue/pending', { params: params as Record<string, string> }),

  assign: (id: string) =>
    apiClient.post(`/api/v1/questions/${id}/assign`),

  submitAnswer: (id: string, content: string, source: Answer['source'] = 'expert') =>
    apiClient.post<Answer>(`/api/v1/questions/${id}/answer`, { content, source }),

  requestClarification: (id: string, message: string) =>
    apiClient.post(`/api/v1/questions/${id}/request-clarification`, { message }),
}
