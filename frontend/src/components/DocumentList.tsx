/**
 * Document list component with delete functionality and GraphRAG details view.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import ConfirmDialog from '@/components/ConfirmDialog'
import DocumentGraphModal from '@/components/DocumentGraphModal'
import StatusBadge, { mapChatbotStatus } from '@/components/StatusBadge'
import { Document, deleteDocument } from '@/services/chatbots'

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

interface DocumentListProps {
  chatbotId: string
  documents: Document[]
  isLoading?: boolean
}

export default function DocumentList({
  chatbotId,
  documents,
  isLoading = false,
}: DocumentListProps) {
  const queryClient = useQueryClient()
  const [deleteTarget, setDeleteTarget] = useState<Document | null>(null)
  const [detailTarget, setDetailTarget] = useState<Document | null>(null)

  const deleteMutation = useMutation({
    mutationFn: (documentId: string) => deleteDocument(chatbotId, documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['documents', chatbotId] })
      queryClient.invalidateQueries({ queryKey: ['chatbot', chatbotId] })
      setDeleteTarget(null)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (documents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <svg
          className="mx-auto h-10 w-10 text-gray-400"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
          />
        </svg>
        <p className="mt-2">No documents uploaded yet.</p>
        <p className="text-sm">Upload PDF files to build your chatbot's knowledge base.</p>
      </div>
    )
  }

  return (
    <>
      <div className="overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead>
            <tr>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Document
              </th>
              <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                Status
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Size
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Chunks
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Entities
              </th>
              <th className="px-4 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                Uploaded
              </th>
              <th className="px-4 py-3 w-10"></th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {documents.map((doc) => (
              <tr key={doc.id} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <svg
                      className="w-5 h-5 text-red-500 flex-shrink-0"
                      fill="currentColor"
                      viewBox="0 0 20 20"
                    >
                      <path
                        fillRule="evenodd"
                        d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z"
                        clipRule="evenodd"
                      />
                    </svg>
                    <span className="text-sm text-gray-900 truncate max-w-[200px]">
                      {doc.filename}
                    </span>
                  </div>
                </td>
                <td className="px-4 py-3">
                  <StatusBadge
                    status={mapChatbotStatus(doc.status)}
                    size="sm"
                  />
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 text-right">
                  {formatFileSize(doc.file_size)}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 text-right">
                  {doc.chunk_count || '-'}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 text-right">
                  {doc.entity_count || '-'}
                </td>
                <td className="px-4 py-3 text-sm text-gray-500 text-right whitespace-nowrap">
                  {formatDate(doc.created_at)}
                </td>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-1">
                    <button
                      onClick={() => setDetailTarget(doc)}
                      disabled={doc.status !== 'completed'}
                      className="p-1 text-gray-400 hover:text-primary-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="View GraphRAG details"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                    </button>
                    <button
                      onClick={() => setDeleteTarget(doc)}
                      disabled={doc.status === 'processing'}
                      className="p-1 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                      title="Delete document"
                    >
                      <svg
                        className="w-4 h-4"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                        />
                      </svg>
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Delete Confirmation */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="Delete Document"
        message={`Are you sure you want to delete "${deleteTarget?.filename}"? This will remove all associated vectors and graph data. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />

      {/* GraphRAG Details Modal */}
      {detailTarget && (
        <DocumentGraphModal
          isOpen={!!detailTarget}
          chatbotId={chatbotId}
          documentId={detailTarget.id}
          filename={detailTarget.filename}
          onClose={() => setDetailTarget(null)}
        />
      )}
    </>
  )
}
