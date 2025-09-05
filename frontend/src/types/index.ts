// Common TypeScript types for the application

export interface User {
  id: number;
  public_id?: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  tier: string;
  email_verified: boolean;
}

export interface Content {
  id: number;
  public_id?: string;
  user_id: number;
  platform: string;
  content: string;
  content_type: string;
  status: string;
  title?: string;
  scheduled_at?: string;
  created_at: string;
  updated_at?: string;
  image_url?: string;
  performance?: {
    views?: number;
    likes?: number;
    shares?: number;
    comments?: number;
  };
}

export interface Goal {
  id: string;
  user_id: number;
  title: string;
  description?: string;
  goal_type: string;
  target_value: number;
  current_value: number;
  target_date: string;
  status: string;
  platform?: string;
  goal_metadata?: Record<string, any>;
  created_at: string;
  updated_at?: string;
}

export interface Notification {
  id: string;
  user_id: number;
  goal_id?: string;
  title: string;
  message: string;
  notification_type: string;
  priority: string;
  is_read: boolean;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  status?: string;
  error?: string;
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
}

// Component Props Types
export interface ComponentWithChildren {
  children: React.ReactNode;
}

export interface ComponentWithClassName {
  className?: string;
}

// API Service Types
export type Platform = 'twitter' | 'linkedin' | 'instagram' | 'facebook' | 'tiktok' | 'all';
export type ContentType = 'text' | 'image' | 'video';
export type ContentStatus = 'draft' | 'scheduled' | 'published' | 'failed';
export type GoalStatus = 'active' | 'paused' | 'completed' | 'failed';
export type NotificationPriority = 'low' | 'medium' | 'high' | 'critical';

// Form Types
export interface LoginForm {
  email: string;
  password: string;
}

export interface RegisterForm {
  email: string;
  username: string;
  password: string;
  full_name?: string;
  accept_terms: boolean;
}

export interface ContentForm {
  platform: Platform;
  content: string;
  content_type: ContentType;
  title?: string;
  scheduled_at?: string;
}

export interface GoalForm {
  title: string;
  description?: string;
  goal_type: string;
  target_value: number;
  target_date: string;
  platform?: string;
}