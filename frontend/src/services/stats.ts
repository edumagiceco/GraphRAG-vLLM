/**
 * Statistics API service.
 */
import api from '@/services/api'

export interface DailyStats {
  date: string
  sessions: number
  messages: number
  avg_response_time_ms: number | null
  input_tokens: number
  output_tokens: number
  retrieval_count: number
}

export interface StatsSummary {
  period_days: number
  start_date: string
  end_date: string
  total_sessions: number
  total_messages: number
  avg_response_time_ms: number | null
  total_input_tokens: number
  total_output_tokens: number
  total_retrieval_count: number
  avg_retrieval_time_ms: number | null
  daily_stats: DailyStats[]
}

export interface StatsResponse {
  chatbot_id: string
  chatbot_name: string
  stats: StatsSummary
}

export interface PerformanceMetrics {
  avg_response_time_ms: number | null
  p50_response_time_ms: number | null
  p95_response_time_ms: number | null
  p99_response_time_ms: number | null
  total_input_tokens: number
  total_output_tokens: number
  avg_tokens_per_response: number | null
  avg_retrieval_count: number | null
  avg_retrieval_time_ms: number | null
}

export interface ResponseTimeTrend {
  date: string
  avg_ms: number
}

export interface PerformanceStatsResponse {
  chatbot_id: string
  period_days: number
  metrics: PerformanceMetrics
  response_time_trend: ResponseTimeTrend[]
}

/**
 * Get statistics for a chatbot.
 */
export async function getChatbotStats(
  chatbotId: string,
  days: number = 30
): Promise<StatsResponse> {
  const response = await api.get<StatsResponse>(
    `/chatbots/${chatbotId}/stats`,
    { params: { days } }
  )
  return response.data
}

/**
 * Get performance statistics for a chatbot.
 */
export async function getPerformanceStats(
  chatbotId: string,
  days: number = 7
): Promise<PerformanceStatsResponse> {
  const response = await api.get<PerformanceStatsResponse>(
    `/chatbots/${chatbotId}/stats/performance`,
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
    `/chatbots/${chatbotId}/stats/recalculate`,
    null,
    { params: { days } }
  )
  return response.data
}
