/**
 * Chat API service.
 */
import { api } from './api'

const API_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Types
export interface ChatbotInfo {
  name: string
  persona_name: string
  greeting: string
}

export interface ChatSession {
  id: string
  chatbot_id: string
  started_at: string
  message_count: number
}

export interface ChatMessage {
  id: string
  session_id: string
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
  created_at: string
}

export interface SessionDetail extends ChatSession {
  messages: ChatMessage[]
}

// API calls

/**
 * Get chatbot public info.
 */
export async function getChatbotInfo(accessUrl: string): Promise<ChatbotInfo> {
  const response = await api.get<ChatbotInfo>(`/chat/${accessUrl}`)
  return response.data
}

/**
 * Create a new chat session.
 */
export async function createSession(accessUrl: string): Promise<ChatSession> {
  const response = await api.post<ChatSession>(`/chat/${accessUrl}/sessions`)
  return response.data
}

/**
 * Get session details with messages.
 */
export async function getSession(
  accessUrl: string,
  sessionId: string
): Promise<SessionDetail> {
  const response = await api.get<SessionDetail>(
    `/chat/${accessUrl}/sessions/${sessionId}`
  )
  return response.data
}

/**
 * Send a message (non-streaming).
 */
export async function sendMessage(
  accessUrl: string,
  sessionId: string,
  content: string
): Promise<ChatMessage> {
  const response = await api.post<ChatMessage>(
    `/chat/${accessUrl}/sessions/${sessionId}/messages`,
    { content, stream: false }
  )
  return response.data
}

/**
 * Get SSE stream URL for sending a message.
 */
export function getStreamUrl(accessUrl: string, sessionId: string): string {
  return `${API_URL}/chat/${accessUrl}/sessions/${sessionId}/messages`
}

/**
 * Stop message generation.
 */
export async function stopGeneration(
  accessUrl: string,
  sessionId: string
): Promise<void> {
  await api.post(`/chat/${accessUrl}/sessions/${sessionId}/stop`)
}

/**
 * Send streaming message request body.
 */
export function createStreamBody(content: string) {
  return { content, stream: true }
}
