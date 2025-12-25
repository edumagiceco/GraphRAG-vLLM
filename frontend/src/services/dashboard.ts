/**
 * Dashboard API service.
 */
import api from './api'

export interface ChatbotSummary {
  id: string
  name: string
  status: string
  today_sessions: number
  today_messages: number
  total_documents: number
}

export interface SystemStatus {
  database: string
  neo4j: string
  redis: string
  qdrant: string
  llm: string
}

export interface DashboardStats {
  total_chatbots: number
  active_chatbots: number
  today_sessions: number
  today_messages: number
  week_sessions: number
  week_messages: number
  avg_response_time_ms: number | null
  total_tokens_today: number
}

export interface DashboardResponse {
  stats: DashboardStats
  recent_chatbots: ChatbotSummary[]
  system_status: SystemStatus
}

/**
 * Get dashboard overview data.
 */
export async function getDashboard(): Promise<DashboardResponse> {
  const response = await api.get<DashboardResponse>('/admin/dashboard')
  return response.data
}
