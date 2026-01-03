/**
 * Chatbot Conversations page - View conversation details for a specific date.
 */
import { useState } from 'react'
import { useParams, useSearchParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import {
  getConversationsByDate,
  getSessionDetail,
  SessionSummary,
  MessageDetail,
} from '@/services/stats'
import { formatDateTime, formatTime } from '@/utils/timezone'

function formatTokens(value: number | null): string {
  if (value === null || value === 0) return '-'
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`
  return value.toString()
}

function formatResponseTime(ms: number | null): string {
  if (ms === null) return '-'
  return `${(ms / 1000).toFixed(2)}s`
}

function MessageBubble({ message }: { message: MessageDetail }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-[80%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-primary-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <div className="text-sm whitespace-pre-wrap break-words">{message.content}</div>
        <div
          className={`mt-2 text-xs ${
            isUser ? 'text-primary-200' : 'text-gray-500'
          }`}
        >
          <span>{formatTime(message.created_at)}</span>
          {!isUser && message.response_time_ms && (
            <span className="ml-2">
              {formatResponseTime(message.response_time_ms)}
            </span>
          )}
          {!isUser && message.input_tokens && (
            <span className="ml-2">
              {formatTokens(message.input_tokens)} / {formatTokens(message.output_tokens)} 토큰
            </span>
          )}
        </div>
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 pt-2 border-t border-gray-200">
            <p className="text-xs text-gray-500 mb-1">참조 문서:</p>
            <div className="flex flex-wrap gap-1">
              {message.sources.slice(0, 3).map((source, idx) => (
                <span
                  key={idx}
                  className="inline-block px-2 py-0.5 bg-gray-200 text-gray-700 text-xs rounded"
                >
                  {source.filename || `청크 ${source.chunk_index}`}
                </span>
              ))}
              {message.sources.length > 3 && (
                <span className="text-xs text-gray-500">
                  +{message.sources.length - 3}개
                </span>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function SessionCard({
  session,
  isSelected,
  onClick,
}: {
  session: SessionSummary
  isSelected: boolean
  onClick: () => void
}) {
  return (
    <div
      className={`p-4 border rounded-lg cursor-pointer transition-colors ${
        isSelected
          ? 'border-primary-500 bg-primary-50'
          : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-900 truncate">
            {session.first_message || '(메시지 없음)'}
          </p>
          <p className="text-xs text-gray-500 mt-1">
            {formatTime(session.created_at)}
          </p>
        </div>
        <div className="ml-2 text-right">
          <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
            {session.message_count}개 메시지
          </span>
        </div>
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
        {session.total_response_time_ms && (
          <span>응답: {formatResponseTime(session.total_response_time_ms)}</span>
        )}
        {session.total_input_tokens && (
          <span>
            토큰: {formatTokens(session.total_input_tokens)} / {formatTokens(session.total_output_tokens)}
          </span>
        )}
      </div>
    </div>
  )
}

export default function ChatbotConversations() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const dateParam = searchParams.get('date') || new Date().toISOString().split('T')[0]

  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchInput, setSearchInput] = useState('')

  // Fetch conversations for the date
  const {
    data: conversationsData,
    isLoading: isLoadingConversations,
    error: conversationsError,
  } = useQuery({
    queryKey: ['conversations', id, dateParam, searchQuery],
    queryFn: () => getConversationsByDate(id!, dateParam, searchQuery || undefined),
    enabled: !!id,
  })

  // Fetch session detail when selected
  const {
    data: sessionDetail,
    isLoading: isLoadingSession,
  } = useQuery({
    queryKey: ['session', id, selectedSessionId],
    queryFn: () => getSessionDetail(id!, selectedSessionId!),
    enabled: !!id && !!selectedSessionId,
  })

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault()
    setSearchQuery(searchInput)
    setSelectedSessionId(null)
  }

  if (isLoadingConversations) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Layout>
    )
  }

  if (conversationsError || !conversationsData) {
    return (
      <Layout>
        <div className="text-center py-12">
          <h2 className="text-lg font-semibold text-gray-900">
            대화 내역을 불러오는데 실패했습니다
          </h2>
          <p className="text-gray-600 mt-2">잠시 후 다시 시도해주세요.</p>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <nav className="text-sm text-gray-500 mb-2">
              <Link to="/admin/chatbots" className="hover:text-gray-700">
                챗봇
              </Link>
              {' > '}
              <Link
                to={`/admin/chatbots/${id}`}
                className="hover:text-gray-700"
              >
                {conversationsData.chatbot_name}
              </Link>
              {' > '}
              <Link
                to={`/admin/chatbots/${id}/stats`}
                className="hover:text-gray-700"
              >
                통계
              </Link>
              {' > '}
              <span className="text-gray-900">대화 내역</span>
            </nav>
            <h1 className="text-2xl font-bold text-gray-900">
              대화 내역 - {dateParam}
            </h1>
            <p className="text-gray-600 mt-1">
              {conversationsData.total_sessions}개 세션, {conversationsData.total_messages}개 메시지
            </p>
          </div>
          <Link
            to={`/admin/chatbots/${id}/stats`}
            className="btn btn-secondary"
          >
            통계로 돌아가기
          </Link>
        </div>

        {/* Search */}
        <div className="card">
          <form onSubmit={handleSearch} className="flex gap-2">
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="대화 내용 검색..."
              className="input flex-1"
            />
            <button type="submit" className="btn btn-primary">
              검색
            </button>
            {searchQuery && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  setSearchInput('')
                  setSearchQuery('')
                }}
              >
                초기화
              </button>
            )}
          </form>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Session List */}
          <div className="lg:col-span-1">
            <div className="card h-[600px] overflow-hidden flex flex-col">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex-shrink-0">
                세션 목록
              </h2>
              <div className="flex-1 overflow-y-auto space-y-3">
                {conversationsData.sessions.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    {searchQuery
                      ? '검색 결과가 없습니다.'
                      : '이 날짜에 대화 내역이 없습니다.'}
                  </div>
                ) : (
                  conversationsData.sessions.map((session) => (
                    <SessionCard
                      key={session.id}
                      session={session}
                      isSelected={selectedSessionId === session.id}
                      onClick={() => setSelectedSessionId(session.id)}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Conversation Detail */}
          <div className="lg:col-span-2">
            <div className="card h-[600px] overflow-hidden flex flex-col">
              <h2 className="text-lg font-semibold text-gray-900 mb-4 flex-shrink-0">
                대화 내용
              </h2>
              <div className="flex-1 overflow-y-auto">
                {!selectedSessionId ? (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    세션을 선택하면 대화 내용이 표시됩니다.
                  </div>
                ) : isLoadingSession ? (
                  <div className="flex items-center justify-center h-full">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
                  </div>
                ) : sessionDetail ? (
                  <div className="space-y-2">
                    {/* Session Info */}
                    <div className="bg-gray-50 rounded-lg p-3 mb-4">
                      <div className="text-sm text-gray-600">
                        <span>세션 시작: {formatDateTime(sessionDetail.created_at)}</span>
                        <span className="mx-2">|</span>
                        <span>{sessionDetail.message_count}개 메시지</span>
                      </div>
                    </div>
                    {/* Messages */}
                    {sessionDetail.messages.map((message) => (
                      <MessageBubble key={message.id} message={message} />
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-gray-500">
                    대화 내용을 불러올 수 없습니다.
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}
