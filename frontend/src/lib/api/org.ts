import { apiClient } from './client'

// ── Turbo Loris Settings ────────────────────────────────────────────

export interface TurboLorisSettings {
  enabled: boolean
  min_threshold: number
  default_threshold: number
  threshold_options: number[]
}

export interface TurboLorisSettingsUpdate {
  enabled?: boolean
  min_threshold?: number
  default_threshold?: number
  threshold_options?: number[]
}

// ── Organization Settings ───────────────────────────────────────────

export interface OrgSettings {
  departments: string[]
  require_department: boolean
  turbo_loris: TurboLorisSettings
}

export interface OrgSettingsUpdate {
  departments?: string[]
  require_department?: boolean
  turbo_loris?: TurboLorisSettingsUpdate
}

// ── AI Provider Settings ────────────────────────────────────────────

export type AIProviderType =
  | 'local_ollama'
  | 'cloud_anthropic'
  | 'cloud_bedrock'
  | 'cloud_azure'

export interface AIProviderSettings {
  provider: AIProviderType
  model: string

  // Ollama settings
  ollama_url: string | null
  ollama_fallback_model: string | null

  // Cloud provider settings (keys are masked)
  anthropic_api_key_set: boolean
  anthropic_api_key_masked: string

  azure_endpoint: string | null
  azure_api_key_set: boolean
  azure_api_key_masked: string
  azure_deployment: string | null

  aws_region: string | null

  // Advanced settings
  max_tokens: number
  temperature: number

  // Computed info
  data_locality: string
  privacy_level: string
}

export interface AIProviderUpdate {
  provider?: AIProviderType
  model?: string

  // Ollama settings
  ollama_url?: string
  ollama_fallback_model?: string

  // Cloud provider settings (plaintext, will be encrypted on server)
  anthropic_api_key?: string

  azure_endpoint?: string
  azure_api_key?: string
  azure_deployment?: string

  aws_region?: string

  // Advanced settings
  max_tokens?: number
  temperature?: number
}

export interface AIProviderTestResult {
  success: boolean
  message: string
  provider: string
  model: string
  response_preview: string | null
}

export interface AIModelInfo {
  name: string
  size: number | null
  modified_at: string | null
}

// ── API Functions ───────────────────────────────────────────────────

export const orgApi = {
  // Organization settings
  getSettings: () =>
    apiClient.get<OrgSettings>('/api/v1/org/settings'),

  updateSettings: (data: OrgSettingsUpdate) =>
    apiClient.put<OrgSettings>('/api/v1/org/settings', data),

  // AI Provider settings
  getAIProvider: () =>
    apiClient.get<AIProviderSettings>('/api/v1/org/ai-provider'),

  updateAIProvider: (data: AIProviderUpdate) =>
    apiClient.put<AIProviderSettings>('/api/v1/org/ai-provider', data),

  testAIProvider: () =>
    apiClient.post<AIProviderTestResult>('/api/v1/org/ai-provider/test'),

  listAIModels: () =>
    apiClient.get<AIModelInfo[]>('/api/v1/org/ai-provider/models'),
}
