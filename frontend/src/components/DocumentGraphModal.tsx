/**
 * Modal component for displaying GraphRAG details of a document.
 */
import { useState, useEffect, useRef } from 'react'
import { useQuery } from '@tanstack/react-query'

import Button from '@/components/Button'
import {
  getDocumentGraphDetails,
  EntityInfo,
  RelationshipInfo,
  ChunkInfo,
} from '@/services/chatbots'

interface DocumentGraphModalProps {
  isOpen: boolean
  chatbotId: string
  documentId: string
  filename: string
  onClose: () => void
}

type TabType = 'entities' | 'relationships' | 'chunks'

const entityTypeColors: Record<string, string> = {
  Concept: 'bg-blue-100 text-blue-800',
  Definition: 'bg-green-100 text-green-800',
  Process: 'bg-purple-100 text-purple-800',
}

const relationTypeColors: Record<string, string> = {
  RELATED_TO: 'bg-gray-100 text-gray-800',
  DEFINES: 'bg-green-100 text-green-800',
  PART_OF: 'bg-blue-100 text-blue-800',
  FOLLOWS: 'bg-yellow-100 text-yellow-800',
  DEPENDS_ON: 'bg-red-100 text-red-800',
  EXAMPLE_OF: 'bg-purple-100 text-purple-800',
  SIMILAR_TO: 'bg-indigo-100 text-indigo-800',
}

function EntityCard({ entity }: { entity: EntityInfo }) {
  return (
    <div className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex items-center gap-2 mb-1">
        <span className="font-medium text-gray-900">{entity.name}</span>
        <span
          className={`px-2 py-0.5 text-xs rounded-full ${
            entityTypeColors[entity.type] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {entity.type}
        </span>
      </div>
      {entity.description && (
        <p className="text-sm text-gray-600 line-clamp-2">{entity.description}</p>
      )}
    </div>
  )
}

function RelationshipCard({ relationship }: { relationship: RelationshipInfo }) {
  return (
    <div className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex items-center gap-2 flex-wrap">
        <span className="font-medium text-gray-900">{relationship.source}</span>
        <span className="text-gray-400">→</span>
        <span
          className={`px-2 py-0.5 text-xs rounded-full ${
            relationTypeColors[relationship.type] || 'bg-gray-100 text-gray-800'
          }`}
        >
          {relationship.type}
        </span>
        <span className="text-gray-400">→</span>
        <span className="font-medium text-gray-900">{relationship.target}</span>
      </div>
    </div>
  )
}

function ChunkCard({ chunk, index }: { chunk: ChunkInfo; index: number }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="p-3 border border-gray-200 rounded-lg hover:bg-gray-50">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded">
            #{index + 1}
          </span>
          {chunk.page !== null && (
            <span className="text-xs text-gray-500">Page {chunk.page}</span>
          )}
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-xs text-primary-600 hover:text-primary-700"
        >
          {expanded ? 'Collapse' : 'Expand'}
        </button>
      </div>
      <p
        className={`text-sm text-gray-700 whitespace-pre-wrap ${
          expanded ? '' : 'line-clamp-3'
        }`}
      >
        {chunk.text}
      </p>
    </div>
  )
}

export default function DocumentGraphModal({
  isOpen,
  chatbotId,
  documentId,
  filename,
  onClose,
}: DocumentGraphModalProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const [activeTab, setActiveTab] = useState<TabType>('entities')

  const { data, isLoading, error } = useQuery({
    queryKey: ['document-graph-details', chatbotId, documentId],
    queryFn: () => getDocumentGraphDetails(chatbotId, documentId),
    enabled: isOpen && !!documentId,
  })

  // Escape key handler
  useEffect(() => {
    if (!isOpen) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.body.style.overflow = 'hidden'

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = ''
    }
  }, [isOpen, onClose])

  // Focus the dialog when it opens
  useEffect(() => {
    if (isOpen && dialogRef.current) {
      dialogRef.current.focus()
    }
  }, [isOpen])

  if (!isOpen) return null

  const tabs = [
    {
      id: 'entities' as const,
      label: 'Entities',
      count: data?.entity_count || 0,
    },
    {
      id: 'relationships' as const,
      label: 'Relationships',
      count: data?.relationship_count || 0,
    },
    {
      id: 'chunks' as const,
      label: 'Chunks',
      count: data?.chunk_count || 0,
    },
  ]

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto">
      {/* Backdrop */}
      <div
        className="fixed inset-0 bg-black/50 transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Dialog container */}
      <div className="flex min-h-full items-center justify-center p-4">
        <div
          ref={dialogRef}
          role="dialog"
          aria-modal="true"
          aria-labelledby="modal-title"
          tabIndex={-1}
          className="relative w-full max-w-4xl max-h-[85vh] transform rounded-lg bg-white shadow-xl transition-all flex flex-col"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200">
            <div>
              <h3 id="modal-title" className="text-lg font-semibold text-gray-900">
                GraphRAG Details
              </h3>
              <p className="text-sm text-gray-500 mt-0.5">{filename}</p>
            </div>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </div>

          {/* Tabs */}
          <div className="px-6 border-b border-gray-200">
            <nav className="flex gap-6 -mb-px">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`py-3 text-sm font-medium border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-primary-600 text-primary-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {tab.label}
                  <span
                    className={`ml-2 px-2 py-0.5 text-xs rounded-full ${
                      activeTab === tab.id
                        ? 'bg-primary-100 text-primary-700'
                        : 'bg-gray-100 text-gray-600'
                    }`}
                  >
                    {tab.count}
                  </span>
                </button>
              ))}
            </nav>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto p-6">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
              </div>
            ) : error ? (
              <div className="text-center py-12 text-red-600">
                Failed to load GraphRAG details. Please try again.
              </div>
            ) : data ? (
              <>
                {activeTab === 'entities' && (
                  <div className="space-y-3">
                    {data.entities.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        No entities extracted from this document.
                      </div>
                    ) : (
                      data.entities.map((entity, idx) => (
                        <EntityCard key={`${entity.name}-${idx}`} entity={entity} />
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'relationships' && (
                  <div className="space-y-3">
                    {data.relationships.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        No relationships extracted from this document.
                      </div>
                    ) : (
                      data.relationships.map((rel, idx) => (
                        <RelationshipCard
                          key={`${rel.source}-${rel.target}-${idx}`}
                          relationship={rel}
                        />
                      ))
                    )}
                  </div>
                )}

                {activeTab === 'chunks' && (
                  <div className="space-y-3">
                    {data.chunks.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        No chunks found for this document.
                      </div>
                    ) : (
                      data.chunks.map((chunk, idx) => (
                        <ChunkCard key={chunk.id} chunk={chunk} index={idx} />
                      ))
                    )}
                  </div>
                )}
              </>
            ) : null}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-200 flex justify-end">
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
