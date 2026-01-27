import { apiClient } from './client'

export type UserRole = 'business_user' | 'domain_expert' | 'admin'

export interface UserListItem {
  id: string
  email: string
  name: string
  role: UserRole
  department: string | null
  title: string | null
  is_active: boolean
  is_verified: boolean
}

export interface UserListResponse {
  users: UserListItem[]
  total: number
  page: number
  page_size: number
}

export interface UserCreateData {
  email: string
  name: string
  password: string
  role?: UserRole
  department?: string
  title?: string
}

export interface UserEditData {
  name?: string
  email?: string
  department?: string
  title?: string
}

export const usersApi = {
  list: (params?: { role?: UserRole; page?: number; page_size?: number }) =>
    apiClient.get<UserListResponse>('/api/v1/users/', { params: params as Record<string, string> }),

  get: (id: string) =>
    apiClient.get<UserListItem>(`/api/v1/users/${id}`),

  create: (data: UserCreateData) =>
    apiClient.post<UserListItem>('/api/v1/users/', data),

  edit: (id: string, data: UserEditData) =>
    apiClient.put<UserListItem>(`/api/v1/users/${id}`, data),

  delete: (id: string) =>
    apiClient.delete(`/api/v1/users/${id}`),

  updateRole: (id: string, role: UserRole) =>
    apiClient.put(`/api/v1/users/${id}/role`, { role }),

  updateStatus: (id: string, is_active: boolean) =>
    apiClient.put(`/api/v1/users/${id}/status`, { is_active }),
}
