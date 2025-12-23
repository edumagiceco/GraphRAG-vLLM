/**
 * Server-Sent Events hook for streaming chat responses.
 */
import { useState, useCallback, useRef } from 'react'

interface ThinkingStatus {
  isThinking: boolean
  stage: string
  message: string
  sourceCount?: number
}

interface SSEChunk {
  type: 'content' | 'sources' | 'done' | 'error' | 'thinking_status'
  content?: string
  sources?: Array<{
    source: string
    filename?: string
    page?: number
    entity?: string
    entity_type?: string
    score?: number
    chunk_text?: string
  }>
  message_id?: string
  error?: string
  stage?: string
  message?: string
  source_count?: number
}

interface UseSSEOptions {
  onContent?: (content: string) => void
  onSources?: (sources: SSEChunk['sources']) => void
  onDone?: (messageId: string | undefined, content: string, sources: SSEChunk['sources']) => void
  onError?: (error: string) => void
  onThinkingStatus?: (status: ThinkingStatus) => void
}

interface UseSSEReturn {
  isStreaming: boolean
  streamedContent: string
  sources: SSEChunk['sources']
  error: string | null
  thinkingStatus: ThinkingStatus | null
  startStream: (url: string, body: object) => Promise<void>
  stopStream: () => void
}

export function useSSE(options: UseSSEOptions = {}): UseSSEReturn {
  const [isStreaming, setIsStreaming] = useState(false)
  const [streamedContent, setStreamedContent] = useState('')
  const [sources, setSources] = useState<SSEChunk['sources']>()
  const [error, setError] = useState<string | null>(null)
  const [thinkingStatus, setThinkingStatus] = useState<ThinkingStatus | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  const stopStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setIsStreaming(false)
    setThinkingStatus(null)
  }, [])

  const startStream = useCallback(async (url: string, body: object) => {
    // Reset state
    setStreamedContent('')
    setSources(undefined)
    setError(null)
    setThinkingStatus(null)
    setIsStreaming(true)

    // Create abort controller
    abortControllerRef.current = new AbortController()

    try {
      const token = localStorage.getItem('graphrag_access_token')
      const response = await fetch(url, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify(body),
        signal: abortControllerRef.current.signal,
      })

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || `HTTP error ${response.status}`)
      }

      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let fullContent = ''
      let localSources: SSEChunk['sources'] = undefined

      while (true) {
        const { done, value } = await reader.read()

        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Process complete SSE messages
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6)
            if (data === '[DONE]') continue

            try {
              const chunk: SSEChunk = JSON.parse(data)

              switch (chunk.type) {
                case 'thinking_status':
                  console.log('[SSE] Received thinking_status:', chunk)
                  const status: ThinkingStatus = {
                    isThinking: true,
                    stage: chunk.stage || '',
                    message: chunk.message || '',
                    sourceCount: chunk.source_count,
                  }
                  setThinkingStatus(status)
                  options.onThinkingStatus?.(status)
                  break

                case 'content':
                  // Clear thinking status when content starts
                  console.log('[SSE] Received content chunk, clearing thinking status')
                  setThinkingStatus(null)
                  if (chunk.content) {
                    fullContent += chunk.content
                    setStreamedContent(fullContent)
                    options.onContent?.(chunk.content)
                  }
                  break

                case 'sources':
                  localSources = chunk.sources
                  setSources(chunk.sources)
                  options.onSources?.(chunk.sources)
                  break

                case 'done':
                  setIsStreaming(false)
                  setThinkingStatus(null)
                  options.onDone?.(chunk.message_id, fullContent, localSources)
                  break

                case 'error':
                  setError(chunk.error || 'Unknown error')
                  setIsStreaming(false)
                  setThinkingStatus(null)
                  options.onError?.(chunk.error || 'Unknown error')
                  break
              }
            } catch (e) {
              console.error('Failed to parse SSE data:', e)
            }
          }
        }
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') {
        // Stream was intentionally stopped
        return
      }
      const errorMessage = e instanceof Error ? e.message : 'Stream failed'
      setError(errorMessage)
      setIsStreaming(false)
      options.onError?.(errorMessage)
    } finally {
      abortControllerRef.current = null
      setIsStreaming(false)
    }
  }, [options])

  return {
    isStreaming,
    streamedContent,
    sources,
    error,
    thinkingStatus,
    startStream,
    stopStream,
  }
}

export type { ThinkingStatus }
