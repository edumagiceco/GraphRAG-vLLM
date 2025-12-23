/**
 * Status badge component for displaying chatbot status.
 */

type StatusType = 'active' | 'inactive' | 'processing' | 'error'

interface StatusBadgeProps {
  status: StatusType
  size?: 'sm' | 'md' | 'lg'
}

const statusConfig = {
  active: {
    bg: 'bg-green-100',
    text: 'text-green-800',
    dot: 'bg-green-500',
    label: '활성',
  },
  inactive: {
    bg: 'bg-gray-100',
    text: 'text-gray-800',
    dot: 'bg-gray-500',
    label: '비활성',
  },
  processing: {
    bg: 'bg-yellow-100',
    text: 'text-yellow-800',
    dot: 'bg-yellow-500',
    label: '처리 중',
  },
  error: {
    bg: 'bg-red-100',
    text: 'text-red-800',
    dot: 'bg-red-500',
    label: '오류',
  },
}

const sizeConfig = {
  sm: {
    container: 'px-2 py-0.5 text-xs',
    dot: 'w-1.5 h-1.5',
  },
  md: {
    container: 'px-2.5 py-1 text-sm',
    dot: 'w-2 h-2',
  },
  lg: {
    container: 'px-3 py-1.5 text-base',
    dot: 'w-2.5 h-2.5',
  },
}

export default function StatusBadge({ status, size = 'md' }: StatusBadgeProps) {
  const config = statusConfig[status]
  const sizes = sizeConfig[size]

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full font-medium ${config.bg} ${config.text} ${sizes.container}`}
    >
      <span
        className={`rounded-full ${config.dot} ${sizes.dot} ${
          status === 'processing' ? 'animate-pulse' : ''
        }`}
      />
      {config.label}
    </span>
  )
}

// Helper to map backend status to component status
export function mapChatbotStatus(status: string): StatusType {
  switch (status.toLowerCase()) {
    case 'active':
      return 'active'
    case 'inactive':
      return 'inactive'
    case 'processing':
      return 'processing'
    case 'error':
      return 'error'
    default:
      return 'inactive'
  }
}
