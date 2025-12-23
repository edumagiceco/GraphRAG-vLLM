/**
 * Chatbot list page with management features.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import Button from '@/components/Button'
import StatusBadge, { mapChatbotStatus } from '@/components/StatusBadge'
import ConfirmDialog from '@/components/ConfirmDialog'
import { getChatbots, updateChatbotStatus, deleteChatbot, Chatbot } from '@/services/chatbots'

function ChatbotCard({
  chatbot,
  onStatusToggle,
  onDelete,
  isUpdating,
}: {
  chatbot: Chatbot
  onStatusToggle: () => void
  onDelete: () => void
  isUpdating: boolean
}) {
  const chatUrl = `${window.location.origin}/chat/${chatbot.access_url}`

  return (
    <div className="card hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1 min-w-0">
          <h3 className="text-lg font-semibold text-gray-900 truncate">{chatbot.name}</h3>
          <p className="text-sm text-gray-500 mt-1 line-clamp-2">
            {chatbot.description || 'No description'}
          </p>
        </div>
        <StatusBadge status={mapChatbotStatus(chatbot.status)} />
      </div>

      <div className="grid grid-cols-2 gap-4 mb-4 text-sm">
        <div>
          <span className="text-gray-500">Documents:</span>
          <span className="ml-2 font-medium">{chatbot.document_count}</span>
        </div>
        <div>
          <span className="text-gray-500">Created:</span>
          <span className="ml-2 font-medium">
            {new Date(chatbot.created_at).toLocaleDateString()}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between pt-4 border-t border-gray-100">
        <div className="text-sm text-gray-500 truncate max-w-[150px]">
          <span className="font-mono">/chat/{chatbot.access_url}</span>
        </div>
        <div className="flex items-center gap-2">
          {/* Status Toggle */}
          <button
            onClick={onStatusToggle}
            disabled={isUpdating || chatbot.status === 'processing'}
            className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed ${
              chatbot.status === 'active' ? 'bg-primary-600' : 'bg-gray-200'
            }`}
            title={chatbot.status === 'active' ? 'Deactivate' : 'Activate'}
          >
            <span
              className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                chatbot.status === 'active' ? 'translate-x-5' : 'translate-x-0'
              }`}
            />
          </button>

          {/* Open Chat */}
          {chatbot.status === 'active' && (
            <a
              href={chatUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="p-1.5 text-gray-400 hover:text-primary-600 transition-colors"
              title="Open Chat"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                />
              </svg>
            </a>
          )}

          {/* Stats */}
          <Link
            to={`/admin/chatbots/${chatbot.id}/stats`}
            className="p-1.5 text-gray-400 hover:text-primary-600 transition-colors"
            title="View Statistics"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
              />
            </svg>
          </Link>

          {/* Manage */}
          <Link
            to={`/admin/chatbots/${chatbot.id}`}
            className="p-1.5 text-gray-400 hover:text-gray-600 transition-colors"
            title="Manage"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </Link>

          {/* Delete */}
          <button
            onClick={onDelete}
            disabled={chatbot.status === 'processing'}
            className="p-1.5 text-gray-400 hover:text-red-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            title="Delete"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

export default function ChatbotList() {
  const queryClient = useQueryClient()
  const [page, setPage] = useState(1)
  const [deleteTarget, setDeleteTarget] = useState<Chatbot | null>(null)
  const pageSize = 12

  const { data, isLoading, error } = useQuery({
    queryKey: ['chatbots', page, pageSize],
    queryFn: () => getChatbots({ page, page_size: pageSize }),
  })

  const statusMutation = useMutation({
    mutationFn: ({ id, status }: { id: string; status: 'active' | 'inactive' }) =>
      updateChatbotStatus(id, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatbots'] })
    },
  })

  const deleteMutation = useMutation({
    mutationFn: deleteChatbot,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatbots'] })
      setDeleteTarget(null)
    },
  })

  const handleStatusToggle = (chatbot: Chatbot) => {
    const newStatus = chatbot.status === 'active' ? 'inactive' : 'active'
    statusMutation.mutate({ id: chatbot.id, status: newStatus })
  }

  return (
    <Layout>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Chatbots</h1>
          <p className="text-gray-600 mt-1">
            Manage your GraphRAG chatbot services
          </p>
        </div>
        <Link to="/admin/chatbots/new">
          <Button
            leftIcon={
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
              </svg>
            }
          >
            Create Chatbot
          </Button>
        </Link>
      </div>

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      )}

      {/* Error state */}
      {error && (
        <div className="card bg-red-50 border-red-200">
          <p className="text-red-700">Failed to load chatbots. Please try again.</p>
        </div>
      )}

      {/* Empty state */}
      {data && data.items.length === 0 && (
        <div className="card text-center py-12">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <h3 className="mt-4 text-lg font-medium text-gray-900">No chatbots yet</h3>
          <p className="mt-2 text-gray-500">
            Get started by creating your first chatbot.
          </p>
          <div className="mt-6">
            <Link to="/admin/chatbots/new">
              <Button>Create Chatbot</Button>
            </Link>
          </div>
        </div>
      )}

      {/* Chatbot grid */}
      {data && data.items.length > 0 && (
        <>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {data.items.map((chatbot) => (
              <ChatbotCard
                key={chatbot.id}
                chatbot={chatbot}
                onStatusToggle={() => handleStatusToggle(chatbot)}
                onDelete={() => setDeleteTarget(chatbot)}
                isUpdating={statusMutation.isPending}
              />
            ))}
          </div>

          {/* Pagination */}
          {data.total > pageSize && (
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-gray-500">
                Showing {(page - 1) * pageSize + 1} to{' '}
                {Math.min(page * pageSize, data.total)} of {data.total} chatbots
              </p>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page === 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  disabled={page * pageSize >= data.total}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!deleteTarget}
        title="Delete Chatbot"
        message={`Are you sure you want to delete "${deleteTarget?.name}"? This will permanently remove all associated documents, conversations, and data. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteTarget && deleteMutation.mutate(deleteTarget.id)}
        onCancel={() => setDeleteTarget(null)}
      />
    </Layout>
  )
}
