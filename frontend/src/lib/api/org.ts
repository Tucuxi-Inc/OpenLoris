import { apiClient } from './client'

export interface TurboLorisSettings {
  enabled: boolean
  min_threshold: number
  default_threshold: number
  threshold_options: number[]
}

export interface OrgSettings {
  departments: string[]
  require_department: boolean
  turbo_loris: TurboLorisSettings
}

export interface TurboLorisSettingsUpdate {
  enabled?: boolean
  min_threshold?: number
  default_threshold?: number
  threshold_options?: number[]
}

export interface OrgSettingsUpdate {
  departments?: string[]
  require_department?: boolean
  turbo_loris?: TurboLorisSettingsUpdate
}

export const orgApi = {
  getSettings: () =>
    apiClient.get<OrgSettings>('/api/v1/org/settings'),

  updateSettings: (data: OrgSettingsUpdate) =>
    apiClient.put<OrgSettings>('/api/v1/org/settings', data),
}
