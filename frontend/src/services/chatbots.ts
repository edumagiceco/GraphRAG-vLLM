/**
 * Chatbot API service.
 */
import { api } from './api'

// Types
export interface PersonaConfig {
  name: string
  description: string
  greeting?: string
  system_prompt?: string
}

export interface CreateChatbotRequest {
  name: string
  description?: string
  persona: PersonaConfig
  access_url: string
}

export interface UpdateChatbotRequest {
  name?: string
  description?: string
  persona?: PersonaConfig
}

export interface Chatbot {
  id: string
  name: string
  description: string | null
  status: 'active' | 'inactive' | 'processing'
  access_url: string
  document_count: number
  created_at: string
  updated_at: string
}

export interface ChatbotDetail extends Chatbot {
  persona: PersonaConfig
  active_version: number
}

export interface ChatbotListResponse {
  items: Chatbot[]
  total: number
  page: number
  page_size: number
}

// API calls

/**
 * Create a new chatbot.
 */
export async function createChatbot(data: CreateChatbotRequest): Promise<ChatbotDetail> {
  const response = await api.post<ChatbotDetail>('/chatbots', data)
  return response.data
}

/**
 * Get chatbot list.
 */
export async function getChatbots(params?: {
  page?: number
  page_size?: number
  status?: string
}): Promise<ChatbotListResponse> {
  const response = await api.get<ChatbotListResponse>('/chatbots', { params })
  return response.data
}

/**
 * Get chatbot details.
 */
export async function getChatbot(id: string): Promise<ChatbotDetail> {
  const response = await api.get<ChatbotDetail>(`/chatbots/${id}`)
  return response.data
}

/**
 * Update chatbot.
 */
export async function updateChatbot(
  id: string,
  data: UpdateChatbotRequest
): Promise<ChatbotDetail> {
  const response = await api.patch<ChatbotDetail>(`/chatbots/${id}`, data)
  return response.data
}

/**
 * Update chatbot status.
 */
export async function updateChatbotStatus(
  id: string,
  status: 'active' | 'inactive'
): Promise<ChatbotDetail> {
  const response = await api.patch<ChatbotDetail>(`/chatbots/${id}/status`, { status })
  return response.data
}

/**
 * Delete chatbot.
 */
export async function deleteChatbot(id: string): Promise<void> {
  await api.delete(`/chatbots/${id}`)
}

// Document types
export interface Document {
  id: string
  chatbot_id: string
  filename: string
  file_size: number
  status: 'pending' | 'processing' | 'completed' | 'failed'
  chunk_count: number
  entity_count: number
  error_message: string | null
  created_at: string
  processed_at: string | null
}

export interface DocumentProgress {
  document_id: string
  progress: number
  stage: string
  message?: string
  error?: string
}

export interface DocumentListResponse {
  items: Document[]
  total: number
}

/**
 * Upload document to chatbot.
 */
export async function uploadDocument(
  chatbotId: string,
  file: File
): Promise<{ id: string; filename: string; status: string; message: string }> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await api.post(`/chatbots/${chatbotId}/documents`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
  return response.data
}

/**
 * Get documents for chatbot.
 */
export async function getDocuments(
  chatbotId: string,
  status?: string
): Promise<DocumentListResponse> {
  const response = await api.get<DocumentListResponse>(
    `/chatbots/${chatbotId}/documents`,
    { params: { status } }
  )
  return response.data
}

/**
 * Get document progress.
 */
export async function getDocumentProgress(
  chatbotId: string,
  documentId: string
): Promise<DocumentProgress> {
  const response = await api.get<DocumentProgress>(
    `/chatbots/${chatbotId}/documents/${documentId}/progress`
  )
  return response.data
}

/**
 * Delete document.
 */
export async function deleteDocument(
  chatbotId: string,
  documentId: string
): Promise<void> {
  await api.delete(`/chatbots/${chatbotId}/documents/${documentId}`)
}

// GraphRAG Details types
export interface EntityInfo {
  name: string
  type: string
  description: string | null
}

export interface RelationshipInfo {
  source: string
  target: string
  type: string
}

export interface ChunkInfo {
  id: string
  text: string
  page: number | null
  position: number
}

export interface DocumentGraphDetails {
  document_id: string
  filename: string
  entities: EntityInfo[]
  relationships: RelationshipInfo[]
  chunks: ChunkInfo[]
  entity_count: number
  relationship_count: number
  chunk_count: number
}

/**
 * Get GraphRAG details for a document.
 */
export async function getDocumentGraphDetails(
  chatbotId: string,
  documentId: string
): Promise<DocumentGraphDetails> {
  const response = await api.get<DocumentGraphDetails>(
    `/chatbots/${chatbotId}/documents/${documentId}/graph-details`
  )
  return response.data
}
