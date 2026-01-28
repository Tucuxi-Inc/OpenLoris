import { apiClient } from './client'

export interface Notification {
  id: string
  type: string
  title: string
  message: string
  link_url: string | null
  extra_data: Record<string, unknown>
  is_read: boolean
  read_at: string | null
  created_at: string
}

export interface NotificationListResponse {
  items: Notification[]
  total: number
  page: number
  page_size: number
  unread_count: number
}

export interface UnreadCountResponse {
  unread_count: number
}

export const notificationsApi = {
  getUnreadCount: () =>
    apiClient.get<UnreadCountResponse>('/api/v1/notifications/unread-count'),

  list: (params?: { unread_only?: boolean; page?: number; page_size?: number }) => {
    const p: Record<string, string> = {}
    if (params?.unread_only) p.unread_only = 'true'
    if (params?.page) p.page = String(params.page)
    if (params?.page_size) p.page_size = String(params.page_size)
    return apiClient.get<NotificationListResponse>('/api/v1/notifications', { params: p })
  },

  markRead: (notificationId: string) =>
    apiClient.post(`/api/v1/notifications/${notificationId}/read`),

  markAllRead: () =>
    apiClient.post('/api/v1/notifications/read-all'),

  delete: (notificationId: string) =>
    apiClient.delete(`/api/v1/notifications/${notificationId}`),
}
