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

const ITEMS_PER_PAGE = 10

export default function ChatbotStats() {
  const { id } = useParams<{ id: string }>()
  const queryClient = useQueryClient()
  const [days, setDays] = useState(30)
  const [currentPage, setCurrentPage] = useState(1)
  const [showActiveOnly, setShowActiveOnly] = useState(false)

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
              onChange={(e) => {
                setDays(Number(e.target.value))
                setCurrentPage(1)
              }}
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
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-900">일별 상세</h2>
            <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer">
              <input
                type="checkbox"
                checked={showActiveOnly}
                onChange={(e) => {
                  setShowActiveOnly(e.target.checked)
                  setCurrentPage(1)
                }}
                className="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
              />
              활동 있는 날짜만 보기
            </label>
          </div>
          {(() => {
            const reversedStats = [...stats.daily_stats].reverse()
            const filteredStats = showActiveOnly
              ? reversedStats.filter((day) => day.sessions > 0 || day.messages > 0)
              : reversedStats
            const totalPages = Math.ceil(filteredStats.length / ITEMS_PER_PAGE)
            const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
            const endIndex = startIndex + ITEMS_PER_PAGE
            const paginatedStats = filteredStats.slice(startIndex, endIndex)

            return (
              <>
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
                      {paginatedStats.map((day) => (
                        <tr key={day.date} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm">
                            {day.sessions > 0 || day.messages > 0 ? (
                              <Link
                                to={`/admin/chatbots/${id}/conversations?date=${day.date}`}
                                className="text-primary-600 hover:text-primary-700 hover:underline font-medium"
                              >
                                {day.date}
                              </Link>
                            ) : (
                              <span className="text-gray-900">{day.date}</span>
                            )}
                          </td>
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

                {/* Empty State */}
                {filteredStats.length === 0 && (
                  <div className="text-center py-8 text-gray-500">
                    {showActiveOnly
                      ? '이 기간에 활동이 있는 날짜가 없습니다.'
                      : '이 기간에 대한 데이터가 없습니다.'}
                  </div>
                )}

                {/* Pagination Controls */}
                {totalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                    <div className="text-sm text-gray-500">
                      {showActiveOnly && (
                        <span className="text-primary-600 mr-1">(필터 적용)</span>
                      )}
                      총 {filteredStats.length}개 중 {startIndex + 1}-{Math.min(endIndex, filteredStats.length)}개 표시
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => setCurrentPage(1)}
                        disabled={currentPage === 1}
                        className="px-2 py-1 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        처음
                      </button>
                      <button
                        onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        이전
                      </button>
                      <div className="flex items-center gap-1">
                        {Array.from({ length: totalPages }, (_, i) => i + 1)
                          .filter((page) => {
                            // Show first, last, current, and pages around current
                            if (page === 1 || page === totalPages) return true
                            if (Math.abs(page - currentPage) <= 1) return true
                            return false
                          })
                          .reduce<(number | string)[]>((acc, page, idx, arr) => {
                            // Add ellipsis between non-consecutive pages
                            if (idx > 0 && page - (arr[idx - 1] as number) > 1) {
                              acc.push('...')
                            }
                            acc.push(page)
                            return acc
                          }, [])
                          .map((item, idx) =>
                            typeof item === 'string' ? (
                              <span key={`ellipsis-${idx}`} className="px-2 text-gray-400">
                                {item}
                              </span>
                            ) : (
                              <button
                                key={item}
                                onClick={() => setCurrentPage(item)}
                                className={`px-3 py-1 text-sm rounded border ${
                                  currentPage === item
                                    ? 'bg-primary-600 text-white border-primary-600'
                                    : 'border-gray-300 hover:bg-gray-50'
                                }`}
                              >
                                {item}
                              </button>
                            )
                          )}
                      </div>
                      <button
                        onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-3 py-1 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        다음
                      </button>
                      <button
                        onClick={() => setCurrentPage(totalPages)}
                        disabled={currentPage === totalPages}
                        className="px-2 py-1 text-sm rounded border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                      >
                        마지막
                      </button>
                    </div>
                  </div>
                )}
              </>
            )
          })()}
        </div>

        {/* Metrics Glossary */}
        <div className="card bg-gray-50">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">용어 설명</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Performance Metrics */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-primary-500 rounded-full"></span>
                성능 지표
              </h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="font-medium text-gray-700">P50 (중앙값)</dt>
                  <dd className="text-gray-500">전체 응답의 50%가 이 시간 이내에 완료됨. 일반적인 사용자 경험을 나타냅니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">P95</dt>
                  <dd className="text-gray-500">전체 응답의 95%가 이 시간 이내에 완료됨. 대부분의 사용자 경험을 나타내며, SLA 기준으로 자주 사용됩니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">P99</dt>
                  <dd className="text-gray-500">전체 응답의 99%가 이 시간 이내에 완료됨. 최악의 경우 성능을 나타내며, 시스템 안정성 지표로 활용됩니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">평균 응답 시간</dt>
                  <dd className="text-gray-500">모든 응답 시간의 산술 평균. 극단적인 값에 영향을 받을 수 있어 퍼센타일과 함께 참고합니다.</dd>
                </div>
              </dl>
            </div>

            {/* Token Metrics */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-indigo-500 rounded-full"></span>
                토큰 지표
              </h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="font-medium text-gray-700">입력 토큰</dt>
                  <dd className="text-gray-500">LLM에 전달된 텍스트의 토큰 수. 시스템 프롬프트, 검색된 컨텍스트, 사용자 질문이 포함됩니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">출력 토큰</dt>
                  <dd className="text-gray-500">LLM이 생성한 응답의 토큰 수. 토큰 수가 많을수록 비용과 응답 시간이 증가합니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">토큰이란?</dt>
                  <dd className="text-gray-500">텍스트를 처리하는 단위. 한국어는 약 2자당 1토큰, 영어는 약 4자당 1토큰으로 계산됩니다.</dd>
                </div>
              </dl>
            </div>

            {/* Retrieval Metrics */}
            <div>
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <span className="w-2 h-2 bg-green-500 rounded-full"></span>
                검색 지표
              </h3>
              <dl className="space-y-2 text-sm">
                <div>
                  <dt className="font-medium text-gray-700">검색 청크 수</dt>
                  <dd className="text-gray-500">질문에 답변하기 위해 검색된 문서 조각의 수. 관련성 높은 컨텍스트를 찾은 횟수입니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">검색 시간</dt>
                  <dd className="text-gray-500">벡터 DB와 그래프 DB에서 관련 문서를 검색하는 데 소요된 시간입니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">세션</dt>
                  <dd className="text-gray-500">사용자와 챗봇 간의 대화 단위. 하나의 세션에 여러 메시지가 포함될 수 있습니다.</dd>
                </div>
                <div>
                  <dt className="font-medium text-gray-700">메시지</dt>
                  <dd className="text-gray-500">사용자 질문과 챗봇 응답을 합한 총 메시지 수입니다.</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
