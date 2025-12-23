/**
 * Statistics API service.
 */
import api from '@/services/api'

export interface DailyStats {
  date: string
  sessions: number
  messages: number
  avg_response_time_ms: number | null
}

export interface StatsSummary {
  period_days: number
  start_date: string
  end_date: string
  total_sessions: number
  total_messages: number
  avg_response_time_ms: number | null
  daily_stats: DailyStats[]
}

export interface StatsResponse {
  chatbot_id: string
  chatbot_name: string
  stats: StatsSummary
}

/**
 * Get statistics for a chatbot.
 */
export async function getChatbotStats(
  chatbotId: string,
  days: number = 30
): Promise<StatsResponse> {
  const response = await api.get<StatsResponse>(
    `/admin/chatbots/${chatbotId}/stats`,
    { params: { days } }
  )
  return response.data
}

/**
 * Trigger recalculation of statistics.
 */
export async function recalculateStats(
  chatbotId: string,
  days: number = 30
): Promise<{ message: string; days_processed: number }> {
  const response = await api.post(
    `/admin/chatbots/${chatbotId}/stats/recalculate`,
    null,
    { params: { days } }
  )
  return response.data
}
