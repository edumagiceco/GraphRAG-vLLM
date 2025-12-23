/**
 * Public chat interface page.
 */
import { useState, useEffect, useRef } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'

import ChatMessage, { LoadingMessage } from '@/components/ChatMessage'
import ChatInput from '@/components/ChatInput'
import { useSSE } from '@/hooks/useSSE'
import {
  getChatbotInfo,
  createSession,
  getStreamUrl,
  createStreamBody,
  stopGeneration,
  ChatMessage as ChatMessageType,
} from '@/services/chat'

export default function ChatPage() {
  const { accessUrl } = useParams<{ accessUrl: string }>()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessageType[]>([])
  const [pendingUserMessage, setPendingUserMessage] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // SSE hook for streaming
  const {
    isStreaming,
    streamedContent,
    sources,
    error: streamError,
    startStream,
    stopStream,
  } = useSSE({
    onDone: (messageId, content, doneSources) => {
      // Add completed assistant message
      if (content && messageId) {
        setMessages((prev) => [
          ...prev,
          {
            id: messageId,
            session_id: sessionId || '',
            role: 'assistant',
            content: content,
            sources: doneSources,
            created_at: new Date().toISOString(),
          },
        ])
      }
      setPendingUserMessage(null)
    },
  })

  // Fetch chatbot info
  const { data: chatbotInfo, isLoading: chatbotLoading, error: chatbotError } = useQuery({
    queryKey: ['chatbot-info', accessUrl],
    queryFn: () => getChatbotInfo(accessUrl!),
    enabled: !!accessUrl,
    retry: false,
  })

  // Create session mutation
  const createSessionMutation = useMutation({
    mutationFn: () => createSession(accessUrl!),
    onSuccess: (session) => {
      setSessionId(session.id)
    },
  })

  // Initialize session
  useEffect(() => {
    if (chatbotInfo && !sessionId) {
      createSessionMutation.mutate()
    }
  }, [chatbotInfo, sessionId])

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, streamedContent, pendingUserMessage])

  const handleSend = async (content: string) => {
    if (!sessionId || !accessUrl) return

    // Add user message immediately
    const userMessage: ChatMessageType = {
      id: `temp-${Date.now()}`,
      session_id: sessionId,
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setPendingUserMessage(content)

    // Start streaming response
    const url = getStreamUrl(accessUrl, sessionId)
    const body = createStreamBody(content)
    await startStream(url, body)
  }

  const handleStop = () => {
    stopStream()
    if (accessUrl && sessionId) {
      stopGeneration(accessUrl, sessionId).catch(() => {})
    }
  }

  // Loading state
  if (chatbotLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
      </div>
    )
  }

  // Error state
  if (chatbotError || !chatbotInfo) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="card max-w-md text-center">
          <h1 className="text-2xl font-bold text-gray-900 mb-4">
            Chatbot Not Found
          </h1>
          <p className="text-gray-600">
            The chatbot you're looking for doesn't exist or is not available.
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-4 py-3 flex-shrink-0">
        <div className="max-w-3xl mx-auto flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-primary-100 flex items-center justify-center text-primary-700 font-medium">
            {chatbotInfo.persona_name[0].toUpperCase()}
          </div>
          <div>
            <h1 className="font-semibold text-gray-900">
              {chatbotInfo.persona_name}
            </h1>
            <p className="text-sm text-gray-500">{chatbotInfo.name}</p>
          </div>
        </div>
      </header>

      {/* Messages area */}
      <main className="flex-1 overflow-y-auto">
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
          {/* Greeting message */}
          {messages.length === 0 && !isStreaming && (
            <ChatMessage
              role="assistant"
              content={chatbotInfo.greeting}
              personaName={chatbotInfo.persona_name}
            />
          )}

          {/* Message history */}
          {messages.map((message) => (
            <ChatMessage
              key={message.id}
              role={message.role}
              content={message.content}
              sources={message.sources}
              personaName={chatbotInfo.persona_name}
            />
          ))}

          {/* Streaming response */}
          {isStreaming && streamedContent && (
            <ChatMessage
              role="assistant"
              content={streamedContent}
              sources={sources}
              isStreaming={true}
              personaName={chatbotInfo.persona_name}
            />
          )}

          {/* Loading indicator */}
          {pendingUserMessage && !streamedContent && isStreaming && (
            <LoadingMessage personaName={chatbotInfo.persona_name} />
          )}

          {/* Stream error */}
          {streamError && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700 text-sm">
              {streamError}
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input area */}
      <footer className="bg-white border-t border-gray-200 p-4 flex-shrink-0">
        <div className="max-w-3xl mx-auto">
          <ChatInput
            onSend={handleSend}
            disabled={!sessionId || createSessionMutation.isPending}
            isGenerating={isStreaming}
            onStop={handleStop}
            placeholder={
              createSessionMutation.isPending
                ? 'Starting session...'
                : 'Ask a question...'
            }
          />
        </div>
      </footer>
    </div>
  )
}
