/**
 * Version selector component with activation capability.
 */
import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

import Button from '@/components/Button'
import ConfirmDialog from '@/components/ConfirmDialog'
import { Version, activateVersion } from '@/services/versions'

interface VersionSelectorProps {
  chatbotId: string
  versions: Version[]
  activeVersion: number | null
  isLoading?: boolean
}

const statusColors = {
  building: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-blue-100 text-blue-800',
  active: 'bg-green-100 text-green-800',
  archived: 'bg-gray-100 text-gray-500',
}

const statusLabels = {
  building: 'Building',
  ready: 'Ready',
  active: 'Active',
  archived: 'Archived',
}

function formatDate(dateString: string | null): string {
  if (!dateString) return '-'
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export default function VersionSelector({
  chatbotId,
  versions,
  activeVersion: _activeVersion,
  isLoading = false,
}: VersionSelectorProps) {
  const queryClient = useQueryClient()
  const [activateTarget, setActivateTarget] = useState<Version | null>(null)

  const activateMutation = useMutation({
    mutationFn: (version: number) => activateVersion(chatbotId, version),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['versions', chatbotId] })
      queryClient.invalidateQueries({ queryKey: ['chatbot', chatbotId] })
      setActivateTarget(null)
    },
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary-600" />
      </div>
    )
  }

  if (versions.length === 0) {
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
            d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
          />
        </svg>
        <p className="mt-2">No versions yet.</p>
        <p className="text-sm">
          Versions will be created when documents are processed.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="space-y-2">
        {versions.map((version) => (
          <div
            key={version.id}
            className={`flex items-center justify-between p-3 rounded-lg border ${
              version.status === 'active'
                ? 'border-green-200 bg-green-50'
                : 'border-gray-200 bg-white'
            }`}
          >
            <div className="flex items-center gap-3">
              <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gray-100 text-gray-700 font-medium">
                v{version.version}
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                      statusColors[version.status]
                    }`}
                  >
                    {statusLabels[version.status]}
                  </span>
                </div>
                <div className="text-xs text-gray-500 mt-0.5">
                  Created: {formatDate(version.created_at)}
                  {version.activated_at && (
                    <> | Activated: {formatDate(version.activated_at)}</>
                  )}
                </div>
              </div>
            </div>

            {version.status === 'ready' && (
              <Button
                variant="primary"
                size="sm"
                onClick={() => setActivateTarget(version)}
              >
                Activate
              </Button>
            )}

            {version.status === 'active' && (
              <span className="text-sm text-green-600 font-medium">
                Currently Active
              </span>
            )}

            {version.status === 'building' && (
              <div className="flex items-center gap-2 text-sm text-yellow-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600" />
                Building...
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Activate Confirmation */}
      <ConfirmDialog
        isOpen={!!activateTarget}
        title="Activate Version"
        message={`Are you sure you want to activate version ${activateTarget?.version}? This will make it the active knowledge base for your chatbot. The current active version will be archived.`}
        confirmLabel="Activate"
        variant="info"
        isLoading={activateMutation.isPending}
        onConfirm={() => activateTarget && activateMutation.mutate(activateTarget.version)}
        onCancel={() => setActivateTarget(null)}
      />
    </>
  )
}
