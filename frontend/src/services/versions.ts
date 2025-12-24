/**
 * Version management API service.
 */
import api from '@/services/api'

export interface Version {
  id: string
  chatbot_id: string
  version: number
  status: 'building' | 'ready' | 'active' | 'archived'
  created_at: string
  activated_at: string | null
}

export interface VersionListResponse {
  items: Version[]
  total: number
  active_version: number | null
}

export interface ActivateVersionResponse {
  message: string
  version: Version
}

/**
 * Get versions for a chatbot.
 */
export async function getVersions(chatbotId: string): Promise<VersionListResponse> {
  const response = await api.get<VersionListResponse>(
    `/chatbots/${chatbotId}/versions`
  )
  return response.data
}

/**
 * Get a specific version.
 */
export async function getVersion(
  chatbotId: string,
  version: number
): Promise<Version> {
  const response = await api.get<Version>(
    `/chatbots/${chatbotId}/versions/${version}`
  )
  return response.data
}

/**
 * Activate a version.
 */
export async function activateVersion(
  chatbotId: string,
  version: number
): Promise<ActivateVersionResponse> {
  const response = await api.post<ActivateVersionResponse>(
    `/chatbots/${chatbotId}/versions/${version}/activate`
  )
  return response.data
}

/**
 * Delete a version.
 */
export async function deleteVersion(
  chatbotId: string,
  version: number
): Promise<void> {
  await api.delete(`/chatbots/${chatbotId}/versions/${version}`)
}
