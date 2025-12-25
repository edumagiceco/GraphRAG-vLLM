/**
 * Chatbot statistics page with performance metrics and charts.
 */
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import Button from '@/components/Button'
import { MetricCard, ResponseTimeChart, TokenUsageChart } from '@/components/charts'
import {
  getChatbotStats,
  getPerformanceStats,
  recalculateStats,
} from '@/services/stats'

function formatTokens(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

function formatTime(ms: number | null): string {
  if (ms === null) return 'N/A'
  return `${(ms / 1000).toFixed(2)}s`
}

export default function ChatbotStats() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [days, setDays] = useState(30)

  const {
    data: statsData,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery({
    queryKey: ['chatbot-stats', id, days],
    queryFn: () => getChatbotStats(id!, days),
    enabled: !!id,
  })

  const {
    data: perfData,
    isLoading: perfLoading,
  } = useQuery({
    queryKey: ['chatbot-performance', id, days],
    queryFn: () => getPerformanceStats(id!, Math.min(days, 90)),
    enabled: !!id,
  })

  const recalculateMutation = useMutation({
    mutationFn: () => recalculateStats(id!, days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatbot-stats', id] })
      queryClient.invalidateQueries({ queryKey: ['chatbot-performance', id] })
    },
  })

  if (statsLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Layout>
    )
  }

  if (statsError || !statsData) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold text-gray-900">통계를 불러오는데 실패했습니다</h2>
          <p className="text-gray-600 mt-2">나중에 다시 시도해주세요.</p>
          <Link to={`/admin/chatbots/${id}`} className="btn-primary mt-4 inline-block">
            챗봇으로 돌아가기
          </Link>
        </div>
      </Layout>
    )
  }

  const { stats, chatbot_name } = statsData
  const metrics = perfData?.metrics
  const maxMessages = Math.max(...stats.daily_stats.map((d) => d.messages), 1)
  const maxSessions = Math.max(...stats.daily_stats.map((d) => d.sessions), 1)

  // Prepare token usage data for chart
  const tokenData = stats.daily_stats.map((d) => ({
    date: d.date,
    input_tokens: d.input_tokens || 0,
    output_tokens: d.output_tokens || 0,
  }))

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2 text-sm text-gray-500 mb-1">
              <Link to="/admin/chatbots" className="hover:text-gray-700">
                Chatbots
              </Link>
              <span>/</span>
              <Link to={`/admin/chatbots/${id}`} className="hover:text-gray-700">
                {chatbot_name}
              </Link>
              <span>/</span>
              <span>통계</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">통계</h1>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border-gray-300 text-sm"
            >
              <option value={7}>최근 7일</option>
              <option value={30}>최근 30일</option>
              <option value={90}>최근 90일</option>
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => recalculateMutation.mutate()}
              isLoading={recalculateMutation.isPending}
            >
              재계산
            </Button>
          </div>
        </div>

        {/* Summary Cards - Row 1 */}
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <MetricCard
            title="총 세션"
            value={stats.total_sessions.toLocaleString()}
            subtitle={`${stats.start_date} - ${stats.end_date}`}
          />
          <MetricCard
            title="총 메시지"
            value={stats.total_messages.toLocaleString()}
            subtitle={`일 평균 ~${Math.round(stats.total_messages / stats.period_days)}개`}
          />
          <MetricCard
            title="평균 응답"
            value={formatTime(stats.avg_response_time_ms)}
            subtitle={stats.avg_response_time_ms ? `${stats.avg_response_time_ms.toFixed(0)}ms` : '-'}
          />
          <MetricCard
            title="P95 응답"
            value={formatTime(metrics?.p95_response_time_ms ?? null)}
            subtitle={perfLoading ? '로딩 중...' : (metrics?.p95_response_time_ms ? `${metrics.p95_response_time_ms.toFixed(0)}ms` : '-')}
          />
          <MetricCard
            title="입력 토큰"
            value={formatTokens(stats.total_input_tokens || 0)}
            subtitle={`총 ${(stats.total_input_tokens || 0).toLocaleString()}개`}
          />
          <MetricCard
            title="출력 토큰"
            value={formatTokens(stats.total_output_tokens || 0)}
            subtitle={`총 ${(stats.total_output_tokens || 0).toLocaleString()}개`}
          />
        </div>

        {/* Performance Metrics Row */}
        {metrics && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricCard
              title="P50 응답 시간"
              value={formatTime(metrics.p50_response_time_ms)}
              subtitle="중앙값"
            />
            <MetricCard
              title="P99 응답 시간"
              value={formatTime(metrics.p99_response_time_ms)}
              subtitle="최상위 1%"
            />
            <MetricCard
              title="평균 검색 청크"
              value={metrics.avg_retrieval_count?.toFixed(1) ?? 'N/A'}
              subtitle="응답당 검색된 문서 수"
            />
            <MetricCard
              title="평균 검색 시간"
              value={formatTime(metrics.avg_retrieval_time_ms ?? null)}
              subtitle="컨텍스트 검색 시간"
            />
          </div>
        )}

        {/* Charts Row */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Response Time Trend Chart */}
          {perfData?.response_time_trend && (
            <ResponseTimeChart
              data={perfData.response_time_trend}
              title="응답 시간 추이"
            />
          )}

          {/* Token Usage Chart */}
          <TokenUsageChart
            data={tokenData}
            title="토큰 사용량"
          />
        </div>

        {/* Daily Stats Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">일별 활동</h2>

          {stats.daily_stats.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              이 기간에 대한 데이터가 없습니다.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Messages Chart */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">메시지</span>
                  <span className="text-sm text-gray-500">
                    총 {stats.total_messages}개
                  </span>
                </div>
                <div className="flex items-end gap-1 h-24">
                  {stats.daily_stats.map((day) => (
                    <div
                      key={day.date}
                      className="flex-1 bg-primary-100 hover:bg-primary-200 rounded-t transition-colors group relative"
                      style={{
                        height: `${(day.messages / maxMessages) * 100}%`,
                        minHeight: day.messages > 0 ? '4px' : '0',
                      }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 whitespace-nowrap z-10 pointer-events-none">
                        {day.date}: {day.messages}개 메시지
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sessions Chart */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">세션</span>
                  <span className="text-sm text-gray-500">
                    총 {stats.total_sessions}개
                  </span>
                </div>
                <div className="flex items-end gap-1 h-24">
                  {stats.daily_stats.map((day) => (
                    <div
                      key={day.date}
                      className="flex-1 bg-green-100 hover:bg-green-200 rounded-t transition-colors group relative"
                      style={{
                        height: `${(day.sessions / maxSessions) * 100}%`,
                        minHeight: day.sessions > 0 ? '4px' : '0',
                      }}
                    >
                      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-gray-900 text-white text-xs rounded opacity-0 group-hover:opacity-100 whitespace-nowrap z-10 pointer-events-none">
                        {day.date}: {day.sessions}개 세션
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Daily Stats Table */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">일별 상세</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    날짜
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    세션
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    메시지
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    평균 응답
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    입력 토큰
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    출력 토큰
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    검색 수
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {[...stats.daily_stats].reverse().map((day) => (
                  <tr key={day.date} className="hover:bg-gray-50">
                    <td className="px-4 py-3 text-sm text-gray-900">{day.date}</td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">
                      {day.sessions}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-900 text-right">
                      {day.messages}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">
                      {day.avg_response_time_ms
                        ? `${(day.avg_response_time_ms / 1000).toFixed(2)}s`
                        : '-'}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">
                      {(day.input_tokens || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">
                      {(day.output_tokens || 0).toLocaleString()}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 text-right">
                      {day.retrieval_count || 0}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </Layout>
  )
}
