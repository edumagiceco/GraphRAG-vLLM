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
