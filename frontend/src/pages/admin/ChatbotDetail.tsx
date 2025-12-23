/**
 * Chatbot detail and management page.
 */
import { useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import Button from '@/components/Button'
import FileUpload from '@/components/FileUpload'
import { DocumentProgress } from '@/components/ProgressBar'
import ConfirmDialog from '@/components/ConfirmDialog'
import DocumentList from '@/components/DocumentList'
import VersionSelector from '@/components/VersionSelector'
import StatusBadge, { mapChatbotStatus } from '@/components/StatusBadge'
import { useDocumentsProgress } from '@/hooks/useDocumentProgress'
import {
  getChatbot,
  getDocuments,
  uploadDocument,
  updateChatbotStatus,
  deleteChatbot,
} from '@/services/chatbots'
import { getVersions } from '@/services/versions'
import { getErrorMessage } from '@/services/api'

export default function ChatbotDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [uploadingDocs, setUploadingDocs] = useState<{ id: string; filename: string }[]>([])
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [activeTab, setActiveTab] = useState<'documents' | 'versions'>('documents')

  // Fetch chatbot details
  const { data: chatbot, isLoading: chatbotLoading } = useQuery({
    queryKey: ['chatbot', id],
    queryFn: () => getChatbot(id!),
    enabled: !!id,
  })

  // Fetch documents
  const { data: documentsData, isLoading: documentsLoading } = useQuery({
    queryKey: ['documents', id],
    queryFn: () => getDocuments(id!),
    enabled: !!id,
    refetchInterval: uploadingDocs.length > 0 ? 5000 : false,
  })

  // Fetch versions
  const { data: versionsData, isLoading: versionsLoading } = useQuery({
    queryKey: ['versions', id],
    queryFn: () => getVersions(id!),
    enabled: !!id,
  })

  // Track progress for uploading documents
  const { documents: progressDocs } = useDocumentsProgress({
    chatbotId: id!,
    documentIds: uploadingDocs,
    onAllComplete: () => {
      setUploadingDocs([])
      queryClient.invalidateQueries({ queryKey: ['documents', id] })
      queryClient.invalidateQueries({ queryKey: ['chatbot', id] })
      queryClient.invalidateQueries({ queryKey: ['versions', id] })
    },
  })

  // Upload mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => uploadDocument(id!, file),
    onSuccess: (data) => {
      setUploadingDocs((prev) => [...prev, { id: data.id, filename: data.filename }])
    },
  })

  // Status toggle mutation
  const statusMutation = useMutation({
    mutationFn: (status: 'active' | 'inactive') => updateChatbotStatus(id!, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chatbot', id] })
    },
  })

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: () => deleteChatbot(id!),
    onSuccess: () => {
      navigate('/admin/chatbots')
    },
  })

  const handleUpload = (file: File) => {
    uploadMutation.mutate(file)
  }

  const handleToggleStatus = () => {
    const newStatus = chatbot?.status === 'active' ? 'inactive' : 'active'
    statusMutation.mutate(newStatus)
  }

  if (chatbotLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Layout>
    )
  }

  if (!chatbot) {
    return (
      <Layout>
        <div className="card text-center py-12">
          <h2 className="text-xl font-semibold text-gray-900">Chatbot not found</h2>
          <Button
            variant="secondary"
            className="mt-4"
            onClick={() => navigate('/admin/chatbots')}
          >
            Back to Chatbots
          </Button>
        </div>
      </Layout>
    )
  }

  const chatUrl = `${window.location.origin}/chat/${chatbot.access_url}`

  return (
    <Layout>
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center gap-2 text-sm text-gray-500 mb-2">
          <Link to="/admin/chatbots" className="hover:text-gray-700">
            Chatbots
          </Link>
          <span>/</span>
          <span>{chatbot.name}</span>
        </div>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-bold text-gray-900">{chatbot.name}</h1>
              <p className="text-gray-600 mt-1">
                {chatbot.description || 'No description'}
              </p>
            </div>
            <StatusBadge status={mapChatbotStatus(chatbot.status)} />
          </div>
          <div className="flex gap-2">
            <Link to={`/admin/chatbots/${id}/stats`}>
              <Button variant="secondary">
                <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                Stats
              </Button>
            </Link>
            <Button
              variant={chatbot.status === 'active' ? 'secondary' : 'primary'}
              onClick={handleToggleStatus}
              isLoading={statusMutation.isPending}
            >
              {chatbot.status === 'active' ? 'Deactivate' : 'Activate'}
            </Button>
            <Button
              variant="danger"
              onClick={() => setShowDeleteConfirm(true)}
            >
              Delete
            </Button>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Main content */}
        <div className="lg:col-span-2 space-y-6">
          {/* Upload section */}
          <div className="card">
            <h2 className="text-lg font-semibold text-gray-900 mb-4">
              Upload Documents
            </h2>
            <FileUpload
              onUpload={handleUpload}
              isUploading={uploadMutation.isPending}
            />
            {uploadMutation.error && (
              <p className="mt-2 text-sm text-red-600">
                {getErrorMessage(uploadMutation.error)}
              </p>
            )}
          </div>

          {/* Processing documents */}
          {progressDocs.length > 0 && (
            <div className="card">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">
                Processing
              </h2>
              <div className="space-y-4">
                {progressDocs.map((doc) => (
                  <DocumentProgress
                    key={doc.documentId}
                    documentId={doc.documentId}
                    filename={doc.filename}
                    progress={doc.progress}
                    stage={doc.stage}
                    error={doc.error}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Tabs for Documents/Versions */}
          <div className="card">
            <div className="border-b border-gray-200 mb-4">
              <nav className="-mb-px flex gap-4">
                <button
                  onClick={() => setActiveTab('documents')}
                  className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'documents'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Documents ({documentsData?.total || 0})
                </button>
                <button
                  onClick={() => setActiveTab('versions')}
                  className={`pb-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === 'versions'
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Versions ({versionsData?.total || 0})
                </button>
              </nav>
            </div>

            {activeTab === 'documents' && (
              <DocumentList
                chatbotId={id!}
                documents={documentsData?.items || []}
                isLoading={documentsLoading}
              />
            )}

            {activeTab === 'versions' && (
              <VersionSelector
                chatbotId={id!}
                versions={versionsData?.items || []}
                activeVersion={versionsData?.active_version || null}
                isLoading={versionsLoading}
              />
            )}
          </div>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Info card */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Chatbot Info
            </h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Status</dt>
                <dd className="mt-1">
                  <StatusBadge status={mapChatbotStatus(chatbot.status)} size="sm" />
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Access URL</dt>
                <dd className="mt-1 font-mono text-xs break-all">
                  {chatUrl}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Documents</dt>
                <dd className="mt-1 font-medium">{chatbot.document_count}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Active Version</dt>
                <dd className="mt-1 font-medium">v{chatbot.active_version || 1}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Created</dt>
                <dd className="mt-1">
                  {new Date(chatbot.created_at).toLocaleDateString()}
                </dd>
              </div>
            </dl>
            {chatbot.status === 'active' && (
              <a
                href={chatUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-4 block w-full btn-primary text-center"
              >
                Open Chat
              </a>
            )}
          </div>

          {/* Persona card */}
          <div className="card">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">
              Persona
            </h3>
            <dl className="space-y-3 text-sm">
              <div>
                <dt className="text-gray-500">Name</dt>
                <dd className="mt-1 font-medium">{chatbot.persona.name}</dd>
              </div>
              <div>
                <dt className="text-gray-500">Description</dt>
                <dd className="mt-1 text-gray-700">
                  {chatbot.persona.description}
                </dd>
              </div>
              <div>
                <dt className="text-gray-500">Greeting</dt>
                <dd className="mt-1 text-gray-700 italic">
                  "{chatbot.persona.greeting}"
                </dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Chatbot"
        message={`Are you sure you want to delete "${chatbot.name}"? This will permanently remove all documents, vectors, and knowledge graph data. This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        isLoading={deleteMutation.isPending}
        onConfirm={() => deleteMutation.mutate()}
        onCancel={() => setShowDeleteConfirm(false)}
      />
    </Layout>
  )
}
