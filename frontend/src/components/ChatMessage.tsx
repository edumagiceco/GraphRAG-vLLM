/**
 * Chat message bubble component.
 */
import SourceCitation from './SourceCitation'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  sources?: Array<{
    source: string
    filename?: string
    page?: number
    entity?: string
    entity_type?: string
    score?: number
    chunk_text?: string
  }>
  isStreaming?: boolean
  personaName?: string
}

export default function ChatMessage({
  role,
  content,
  sources,
  isStreaming = false,
  personaName = 'Assistant',
}: ChatMessageProps) {
  const isUser = role === 'user'

  return (
    <div className={`flex gap-3 ${isUser ? 'flex-row-reverse' : ''}`}>
      {/* Avatar */}
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
          isUser
            ? 'bg-primary-100 text-primary-700'
            : 'bg-gray-100 text-gray-700'
        }`}
      >
        {isUser ? 'U' : personaName[0].toUpperCase()}
      </div>

      {/* Message content */}
      <div className={`flex flex-col max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div
          className={`rounded-2xl px-4 py-2 ${
            isUser
              ? 'bg-primary-600 text-white rounded-tr-none'
              : 'bg-gray-100 text-gray-900 rounded-tl-none'
          }`}
        >
          <div className="whitespace-pre-wrap break-words">
            {content}
            {isStreaming && (
              <span className="inline-block w-2 h-4 ml-1 bg-current animate-pulse" />
            )}
          </div>
        </div>

        {/* Sources */}
        {!isUser && sources && sources.length > 0 && (
          <div className="mt-2">
            <SourceCitation sources={sources} />
          </div>
        )}
      </div>
    </div>
  )
}

/**
 * Loading message placeholder.
 */
export function LoadingMessage({ personaName = 'Assistant' }: { personaName?: string }) {
  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium bg-gray-100 text-gray-700">
        {personaName[0].toUpperCase()}
      </div>

      {/* Loading indicator */}
      <div className="bg-gray-100 rounded-2xl rounded-tl-none px-4 py-3">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
      </div>
    </div>
  )
}

/**
 * Thinking/Reasoning message component.
 * Shows the current stage of processing.
 */
interface ThinkingMessageProps {
  personaName?: string
  stage: string
  message: string
  sourceCount?: number
}

export function ThinkingMessage({
  personaName = 'Assistant',
  stage,
  message,
  sourceCount,
}: ThinkingMessageProps) {
  const getStageIcon = () => {
    switch (stage) {
      case 'history':
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'retrieval':
        return (
          <svg className="w-4 h-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        )
      case 'context_found':
        return (
          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        )
      case 'generating':
        return (
          <svg className="w-4 h-4 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
        )
      default:
        return (
          <svg className="w-4 h-4 animate-spin" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
          </svg>
        )
    }
  }

  return (
    <div className="flex gap-3">
      {/* Avatar */}
      <div className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium bg-gray-100 text-gray-700">
        {personaName[0].toUpperCase()}
      </div>

      {/* Thinking indicator */}
      <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-100 rounded-2xl rounded-tl-none px-4 py-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          {getStageIcon()}
          <span className="font-medium text-blue-700">추론 중</span>
          <span className="text-gray-500">|</span>
          <span>{message}</span>
          {sourceCount !== undefined && sourceCount > 0 && (
            <span className="ml-2 px-2 py-0.5 bg-green-100 text-green-700 rounded-full text-xs">
              {sourceCount}개 출처
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
