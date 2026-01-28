import { apiClient } from './client'

export interface OrgSettings {
  departments: string[]
  require_department: boolean
}

export interface OrgSettingsUpdate {
  departments?: string[]
  require_department?: boolean
}

export const orgApi = {
  getSettings: () =>
    apiClient.get<OrgSettings>('/api/v1/org/settings'),

  updateSettings: (data: OrgSettingsUpdate) =>
    apiClient.put<OrgSettings>('/api/v1/org/settings', data),
}
