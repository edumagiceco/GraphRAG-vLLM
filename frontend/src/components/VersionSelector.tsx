/**
 * Version selector component with activation capability.
 */
import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import Button from '@/components/Button'
import ConfirmDialog from '@/components/ConfirmDialog'
import { Version, activateVersion } from '@/services/versions'
import { getSystemSettings } from '@/services/settings'
import { formatDateWithTimezone } from '@/utils/timezone'

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
  building: '빌드 중',
  ready: '준비됨',
  active: '활성',
  archived: '보관됨',
}

export default function VersionSelector({
  chatbotId,
  versions,
  activeVersion: _activeVersion,
  isLoading = false,
}: VersionSelectorProps) {
  const queryClient = useQueryClient()
  const [activateTarget, setActivateTarget] = useState<Version | null>(null)

  // Get system timezone
  const { data: settings } = useQuery({
    queryKey: ['system-settings'],
    queryFn: getSystemSettings,
    staleTime: 5 * 60 * 1000,
  })
  const timezone = settings?.timezone || 'GMT+0'

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
        <p className="mt-2">아직 버전이 없습니다.</p>
        <p className="text-sm">
          문서가 처리되면 버전이 생성됩니다.
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
                  생성일: {formatDateWithTimezone(version.created_at, timezone)}
                  {version.activated_at && (
                    <> | 활성화일: {formatDateWithTimezone(version.activated_at, timezone)}</>
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
                활성화
              </Button>
            )}

            {version.status === 'active' && (
              <span className="text-sm text-green-600 font-medium">
                현재 활성
              </span>
            )}

            {version.status === 'building' && (
              <div className="flex items-center gap-2 text-sm text-yellow-600">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-yellow-600" />
                빌드 중...
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Activate Confirmation */}
      <ConfirmDialog
        isOpen={!!activateTarget}
        title="버전 활성화"
        message={`버전 ${activateTarget?.version}을(를) 활성화하시겠습니까? 이 버전이 챗봇의 활성 지식 베이스가 됩니다. 현재 활성 버전은 보관됩니다.`}
        confirmLabel="활성화"
        variant="info"
        isLoading={activateMutation.isPending}
        onConfirm={() => activateTarget && activateMutation.mutate(activateTarget.version)}
        onCancel={() => setActivateTarget(null)}
      />
    </>
  )
}
