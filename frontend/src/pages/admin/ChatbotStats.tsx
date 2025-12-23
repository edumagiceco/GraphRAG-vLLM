/**
 * Chatbot statistics page.
 */
import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import Button from '@/components/Button'
import { getChatbotStats, recalculateStats } from '@/services/stats'

export default function ChatbotStats() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [days, setDays] = useState(30)

  const {
    data: statsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['chatbot-stats', id, days],
    queryFn: () => getChatbotStats(id!, days),
    enabled: !!id,
  })

  const recalculateMutation = useMutation({
    mutationFn: () => recalculateStats(id!, days),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatbot-stats', id] })
    },
  })

  if (isLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Layout>
    )
  }

  if (error || !statsData) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold text-gray-900">Failed to load statistics</h2>
          <p className="text-gray-600 mt-2">Please try again later.</p>
          <Link to={`/admin/chatbots/${id}`} className="btn-primary mt-4 inline-block">
            Back to Chatbot
          </Link>
        </div>
      </Layout>
    )
  }

  const { stats, chatbot_name } = statsData
  const maxMessages = Math.max(...stats.daily_stats.map((d) => d.messages), 1)
  const maxSessions = Math.max(...stats.daily_stats.map((d) => d.sessions), 1)

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
              <span>Statistics</span>
            </div>
            <h1 className="text-2xl font-bold text-gray-900">Statistics</h1>
          </div>
          <div className="flex items-center gap-3">
            <select
              value={days}
              onChange={(e) => setDays(Number(e.target.value))}
              className="rounded-lg border-gray-300 text-sm"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => recalculateMutation.mutate()}
              isLoading={recalculateMutation.isPending}
            >
              Recalculate
            </Button>
          </div>
        </div>

        {/* Summary Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="card">
            <div className="text-sm text-gray-500">Total Sessions</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {stats.total_sessions.toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {stats.start_date} - {stats.end_date}
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-gray-500">Total Messages</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {stats.total_messages.toLocaleString()}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              ~{Math.round(stats.total_messages / stats.period_days)} per day
            </div>
          </div>
          <div className="card">
            <div className="text-sm text-gray-500">Avg Response Time</div>
            <div className="text-3xl font-bold text-gray-900 mt-1">
              {stats.avg_response_time_ms
                ? `${(stats.avg_response_time_ms / 1000).toFixed(2)}s`
                : 'N/A'}
            </div>
            <div className="text-sm text-gray-500 mt-1">
              {stats.avg_response_time_ms ? `${stats.avg_response_time_ms.toFixed(0)}ms` : '-'}
            </div>
          </div>
        </div>

        {/* Daily Stats Chart */}
        <div className="card">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Daily Activity</h2>

          {stats.daily_stats.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No data available for this period.
            </div>
          ) : (
            <div className="space-y-4">
              {/* Messages Chart */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Messages</span>
                  <span className="text-sm text-gray-500">
                    {stats.total_messages} total
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
                        {day.date}: {day.messages} messages
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Sessions Chart */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium text-gray-700">Sessions</span>
                  <span className="text-sm text-gray-500">
                    {stats.total_sessions} total
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
                        {day.date}: {day.sessions} sessions
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
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Daily Breakdown</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead>
                <tr>
                  <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Date
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Sessions
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Messages
                  </th>
                  <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Response
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
