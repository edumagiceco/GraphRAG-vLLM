/**
 * Dashboard page with system overview and statistics.
 */
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import { getDashboard, SystemStatus } from '@/services/dashboard'

function formatTime(ms: number | null): string {
  if (ms === null) return 'N/A'
  return `${(ms / 1000).toFixed(2)}s`
}

function formatTokens(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    healthy: 'bg-green-100 text-green-800',
    error: 'bg-red-100 text-red-800',
    disconnected: 'bg-yellow-100 text-yellow-800',
  }
  const labels: Record<string, string> = {
    healthy: '정상',
    error: '오류',
    disconnected: '연결 안됨',
  }
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {labels[status] || status}
    </span>
  )
}

function ChatbotStatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    active: 'bg-green-100 text-green-800',
    inactive: 'bg-gray-100 text-gray-800',
    indexing: 'bg-blue-100 text-blue-800',
  }
  const labels: Record<string, string> = {
    active: '활성',
    inactive: '비활성',
    indexing: '인덱싱 중',
  }
  return (
    <span className={`px-2 py-1 text-xs font-medium rounded-full ${colors[status] || 'bg-gray-100 text-gray-800'}`}>
      {labels[status] || status}
    </span>
  )
}

function SystemStatusCard({ status }: { status: SystemStatus }) {
  const components = [
    { name: 'Database', key: 'database' as keyof SystemStatus, icon: '🗄️' },
    { name: 'Neo4j', key: 'neo4j' as keyof SystemStatus, icon: '🔗' },
    { name: 'Redis', key: 'redis' as keyof SystemStatus, icon: '⚡' },
    { name: 'Qdrant', key: 'qdrant' as keyof SystemStatus, icon: '🔍' },
    { name: 'LLM', key: 'llm' as keyof SystemStatus, icon: '🤖' },
  ]

  return (
    <div className="card">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">시스템 상태</h2>
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {components.map((component) => (
          <div key={component.key} className="flex items-center gap-2">
            <span className="text-lg">{component.icon}</span>
            <div>
              <p className="text-sm text-gray-600">{component.name}</p>
              <StatusBadge status={status[component.key]} />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function Dashboard() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
    refetchInterval: 60000, // Refresh every minute
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

  if (error || !data) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold text-gray-900">대시보드를 불러오는데 실패했습니다</h2>
          <p className="text-gray-600 mt-2">잠시 후 다시 시도해주세요.</p>
        </div>
      </Layout>
    )
  }

  const { stats, recent_chatbots, system_status } = data

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div>
          <h1 className="text-2xl font-bold text-gray-900">대시보드</h1>
          <p className="text-gray-600 mt-1">시스템 현황 및 통계 요약</p>
        </div>

        {/* Stats Cards - Row 1 */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="card bg-gradient-to-br from-blue-50 to-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">전체 챗봇</p>
                <p className="text-3xl font-bold text-gray-900">{stats.total_chatbots}</p>
                <p className="text-xs text-gray-500 mt-1">활성: {stats.active_chatbots}개</p>
              </div>
              <div className="text-4xl opacity-50">🤖</div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-green-50 to-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">오늘 세션</p>
                <p className="text-3xl font-bold text-gray-900">{stats.today_sessions}</p>
                <p className="text-xs text-gray-500 mt-1">이번 주: {stats.week_sessions}개</p>
              </div>
              <div className="text-4xl opacity-50">💬</div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-purple-50 to-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">오늘 메시지</p>
                <p className="text-3xl font-bold text-gray-900">{stats.today_messages}</p>
                <p className="text-xs text-gray-500 mt-1">이번 주: {stats.week_messages}개</p>
              </div>
              <div className="text-4xl opacity-50">📝</div>
            </div>
          </div>

          <div className="card bg-gradient-to-br from-orange-50 to-white">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">평균 응답 시간</p>
                <p className="text-3xl font-bold text-gray-900">{formatTime(stats.avg_response_time_ms)}</p>
                <p className="text-xs text-gray-500 mt-1">최근 7일 기준</p>
              </div>
              <div className="text-4xl opacity-50">⚡</div>
            </div>
          </div>
        </div>

        {/* Token Usage Card */}
        <div className="card">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-gray-900">오늘 토큰 사용량</h2>
              <p className="text-sm text-gray-600 mt-1">입력 + 출력 토큰 합계</p>
            </div>
            <div className="text-right">
              <p className="text-3xl font-bold text-primary-600">{formatTokens(stats.total_tokens_today)}</p>
              <p className="text-sm text-gray-500">{stats.total_tokens_today.toLocaleString()} 토큰</p>
            </div>
          </div>
        </div>

        {/* System Status */}
        <SystemStatusCard status={system_status} />

        {/* Recent Chatbots */}
        <div className="card">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">최근 챗봇</h2>
            <Link to="/admin/chatbots" className="text-sm text-primary-600 hover:text-primary-700">
              전체 보기 →
            </Link>
          </div>
          {recent_chatbots.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <p>등록된 챗봇이 없습니다.</p>
              <Link to="/admin/chatbots/new" className="text-primary-600 hover:text-primary-700 mt-2 inline-block">
                새 챗봇 만들기
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      챗봇
                    </th>
                    <th className="px-4 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">
                      상태
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      오늘 세션
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      오늘 메시지
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      문서 수
                    </th>
                    <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                      작업
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {recent_chatbots.map((chatbot) => (
                    <tr key={chatbot.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <Link
                          to={`/admin/chatbots/${chatbot.id}`}
                          className="font-medium text-gray-900 hover:text-primary-600"
                        >
                          {chatbot.name}
                        </Link>
                      </td>
                      <td className="px-4 py-3 text-center">
                        <ChatbotStatusBadge status={chatbot.status} />
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-900">
                        {chatbot.today_sessions}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-900">
                        {chatbot.today_messages}
                      </td>
                      <td className="px-4 py-3 text-right text-sm text-gray-500">
                        {chatbot.total_documents}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          to={`/admin/chatbots/${chatbot.id}/stats`}
                          className="text-sm text-primary-600 hover:text-primary-700"
                        >
                          통계
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
