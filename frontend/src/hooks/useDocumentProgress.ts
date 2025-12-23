/**
 * Hook for polling document processing progress.
 */
import { useState, useEffect, useCallback } from 'react'
import { getDocumentProgress, DocumentProgress } from '@/services/chatbots'

interface UseDocumentProgressOptions {
  chatbotId: string
  documentId: string
  enabled?: boolean
  pollInterval?: number
  onComplete?: () => void
  onError?: (error: string) => void
}

interface UseDocumentProgressReturn {
  progress: DocumentProgress | null
  isPolling: boolean
  error: string | null
  startPolling: () => void
  stopPolling: () => void
}

export function useDocumentProgress({
  chatbotId,
  documentId,
  enabled = true,
  pollInterval = 2000,
  onComplete,
  onError,
}: UseDocumentProgressOptions): UseDocumentProgressReturn {
  const [progress, setProgress] = useState<DocumentProgress | null>(null)
  const [isPolling, setIsPolling] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const fetchProgress = useCallback(async () => {
    try {
      const data = await getDocumentProgress(chatbotId, documentId)
      setProgress(data)
      setError(null)

      // Check if completed or failed
      if (data.progress >= 100 || data.stage === 'completed') {
        setIsPolling(false)
        onComplete?.()
      } else if (data.progress < 0 || data.stage === 'failed' || data.error) {
        setIsPolling(false)
        const errorMsg = data.error || 'Processing failed'
        setError(errorMsg)
        onError?.(errorMsg)
      }
    } catch (err) {
      setError('Failed to fetch progress')
      setIsPolling(false)
    }
  }, [chatbotId, documentId, onComplete, onError])

  const startPolling = useCallback(() => {
    setIsPolling(true)
    setError(null)
  }, [])

  const stopPolling = useCallback(() => {
    setIsPolling(false)
  }, [])

  // Start polling when enabled
  useEffect(() => {
    if (enabled && !isPolling) {
      startPolling()
    }
  }, [enabled, startPolling])

  // Polling loop
  useEffect(() => {
    if (!isPolling) return

    // Initial fetch
    fetchProgress()

    // Set up interval
    const intervalId = setInterval(fetchProgress, pollInterval)

    return () => {
      clearInterval(intervalId)
    }
  }, [isPolling, pollInterval, fetchProgress])

  return {
    progress,
    isPolling,
    error,
    startPolling,
    stopPolling,
  }
}

/**
 * Hook for tracking multiple documents' progress.
 */
interface DocumentProgressItem {
  documentId: string
  filename: string
  progress: number
  stage: string
  error?: string | null
}

interface UseDocumentsProgressOptions {
  chatbotId: string
  documentIds: { id: string; filename: string }[]
  pollInterval?: number
  onAllComplete?: () => void
}

export function useDocumentsProgress({
  chatbotId,
  documentIds,
  pollInterval = 2000,
  onAllComplete,
}: UseDocumentsProgressOptions) {
  const [documents, setDocuments] = useState<Map<string, DocumentProgressItem>>(
    new Map()
  )
  const [isPolling, setIsPolling] = useState(false)

  // Initialize documents
  useEffect(() => {
    const initial = new Map<string, DocumentProgressItem>()
    documentIds.forEach(({ id, filename }) => {
      if (!documents.has(id)) {
        initial.set(id, {
          documentId: id,
          filename,
          progress: 0,
          stage: 'pending',
        })
      }
    })
    if (initial.size > 0) {
      setDocuments((prev) => new Map([...prev, ...initial]))
      setIsPolling(true)
    }
  }, [documentIds])

  // Polling
  useEffect(() => {
    if (!isPolling || documentIds.length === 0) return

    const fetchAll = async () => {
      const updates = await Promise.all(
        documentIds.map(async ({ id, filename }) => {
          try {
            const progress = await getDocumentProgress(chatbotId, id)
            return {
              documentId: id,
              filename,
              progress: progress.progress,
              stage: progress.stage,
              error: progress.error,
            }
          } catch {
            return {
              documentId: id,
              filename,
              progress: -1,
              stage: 'failed',
              error: 'Failed to fetch progress',
            }
          }
        })
      )

      setDocuments((prev) => {
        const next = new Map(prev)
        updates.forEach((item) => {
          next.set(item.documentId, item)
        })
        return next
      })

      // Check if all completed
      const allDone = updates.every(
        (item) =>
          item.progress >= 100 ||
          item.stage === 'completed' ||
          item.progress < 0 ||
          item.stage === 'failed'
      )

      if (allDone) {
        setIsPolling(false)
        onAllComplete?.()
      }
    }

    fetchAll()
    const intervalId = setInterval(fetchAll, pollInterval)

    return () => clearInterval(intervalId)
  }, [isPolling, chatbotId, documentIds, pollInterval, onAllComplete])

  return {
    documents: Array.from(documents.values()),
    isPolling,
  }
}
