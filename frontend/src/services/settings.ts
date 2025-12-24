/**
 * Settings API service for model configuration.
 */
import api from './api'

export interface ModelInfo {
  name: string
  size: number
  size_formatted: string
  modified_at: string
  family: string | null
  parameter_size: string | null
  quantization_level: string | null
}

export interface SystemSettings {
  default_llm_model: string
  embedding_model: string
  embedding_dimension: number
  ollama_base_url: string
  timezone: string
}

export interface AvailableModels {
  models: ModelInfo[]
  chat_models: ModelInfo[]
  embedding_models: ModelInfo[]
  total: number
}

export interface ConnectionTest {
  connected: boolean
  ollama_version: string | null
  ollama_base_url: string
  error: string | null
}

export interface ReprocessResult {
  task_id: string
  document_count: number
  message: string
}

/**
 * Get current system settings for models.
 */
export async function getSystemSettings(): Promise<SystemSettings> {
  const response = await api.get<SystemSettings>('/settings/models')
  return response.data
}

/**
 * Get available models from Ollama.
 */
export async function getAvailableModels(): Promise<AvailableModels> {
  const response = await api.get<AvailableModels>('/settings/models/available')
  return response.data
}

/**
 * Update the default LLM model.
 */
export async function updateDefaultLLMModel(model: string): Promise<SystemSettings> {
  const response = await api.put<SystemSettings>('/settings/models/default-llm', { model })
  return response.data
}

/**
 * Update the embedding model.
 */
export async function updateEmbeddingModel(model: string): Promise<SystemSettings> {
  const response = await api.put<SystemSettings>('/settings/models/embedding', { model })
  return response.data
}

/**
 * Test connection to Ollama server.
 */
export async function testOllamaConnection(): Promise<ConnectionTest> {
  const response = await api.get<ConnectionTest>('/settings/models/test-connection')
  return response.data
}

/**
 * Reprocess all documents (useful after changing embedding model).
 */
export async function reprocessDocuments(
  chatbotId?: string,
  force?: boolean
): Promise<ReprocessResult> {
  const response = await api.post<ReprocessResult>('/settings/documents/reprocess', {
    chatbot_id: chatbotId,
    force: force ?? false,
  })
  return response.data
}

/**
 * Update the Ollama server base URL.
 */
export async function updateOllamaUrl(url: string): Promise<SystemSettings> {
  const response = await api.put<SystemSettings>('/settings/models/ollama-url', { url })
  return response.data
}

/**
 * Update the system timezone.
 */
export async function updateTimezone(timezone: string): Promise<SystemSettings> {
  const response = await api.put<SystemSettings>('/settings/timezone', { timezone })
  return response.data
}
