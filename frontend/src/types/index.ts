// Re-export types from API modules
export * from '../lib/api/questions'

// User types
export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  organization_id: string
  department?: string
  title?: string
  is_active: boolean
  is_verified: boolean
  notification_preferences: NotificationPreferences
}

export type UserRole = 'business_user' | 'domain_expert' | 'admin'

export interface NotificationPreferences {
  email: boolean
  in_app: boolean
}

// Organization types
export interface Organization {
  id: string
  name: string
  slug: string
  domain?: string
  logo_url?: string
  primary_color?: string
}
