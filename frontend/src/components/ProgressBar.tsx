/**
 * Progress bar component for document processing.
 */

interface ProgressBarProps {
  progress: number
  stage?: string
  error?: string | null
  showPercentage?: boolean
  size?: 'sm' | 'md' | 'lg'
}

const stageLabels: Record<string, string> = {
  uploading: 'Uploading...',
  parsing: 'Parsing PDF...',
  chunking: 'Chunking text...',
  embedding: 'Generating embeddings...',
  extracting: 'Extracting entities...',
  graphing: 'Building knowledge graph...',
  completed: 'Completed',
  failed: 'Failed',
}

export default function ProgressBar({
  progress,
  stage,
  error,
  showPercentage = true,
  size = 'md',
}: ProgressBarProps) {
  const isError = progress < 0 || stage === 'failed' || !!error
  const isComplete = progress >= 100 || stage === 'completed'
  const displayProgress = isError ? 100 : Math.min(Math.max(progress, 0), 100)

  const sizeClasses = {
    sm: 'h-1',
    md: 'h-2',
    lg: 'h-3',
  }

  const getBarColor = () => {
    if (isError) return 'bg-red-500'
    if (isComplete) return 'bg-green-500'
    return 'bg-primary-500'
  }

  const getStatusColor = () => {
    if (isError) return 'text-red-600'
    if (isComplete) return 'text-green-600'
    return 'text-gray-600'
  }

  return (
    <div className="w-full">
      {/* Progress bar */}
      <div className={`w-full bg-gray-200 rounded-full overflow-hidden ${sizeClasses[size]}`}>
        <div
          className={`${sizeClasses[size]} ${getBarColor()} transition-all duration-300 ease-out`}
          style={{ width: `${displayProgress}%` }}
        />
      </div>

      {/* Status text */}
      <div className="flex items-center justify-between mt-1">
        <span className={`text-sm ${getStatusColor()}`}>
          {error || stageLabels[stage || ''] || stage || 'Processing...'}
        </span>
        {showPercentage && !isError && (
          <span className="text-sm text-gray-500">
            {Math.round(displayProgress)}%
          </span>
        )}
      </div>
    </div>
  )
}

/**
 * Detailed progress display for document processing.
 */
interface DocumentProgressProps {
  documentId: string
  filename: string
  progress: number
  stage: string
  error?: string | null
  onRetry?: () => void
  onDelete?: () => void
}

export function DocumentProgress({
  documentId,
  filename,
  progress,
  stage,
  error,
  onRetry,
  onDelete,
}: DocumentProgressProps) {
  const isError = progress < 0 || stage === 'failed' || !!error
  const isComplete = progress >= 100 || stage === 'completed'

  return (
    <div className="border border-gray-200 rounded-lg p-4">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          {/* File icon */}
          <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-red-600" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z"
                clipRule="evenodd"
              />
            </svg>
          </div>
          <div>
            <h4 className="text-sm font-medium text-gray-900 truncate max-w-[200px]">
              {filename}
            </h4>
            <p className="text-xs text-gray-500">
              {documentId.slice(0, 8)}...
            </p>
          </div>
        </div>

        {/* Status indicator */}
        <div className="flex items-center gap-2">
          {isComplete && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800">
              Completed
            </span>
          )}
          {isError && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
              Failed
            </span>
          )}
          {!isComplete && !isError && (
            <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">
              Processing
            </span>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <ProgressBar
        progress={progress}
        stage={stage}
        error={error}
        size="sm"
      />

      {/* Actions */}
      {(isError || isComplete) && (onRetry || onDelete) && (
        <div className="flex gap-2 mt-3">
          {isError && onRetry && (
            <button
              onClick={onRetry}
              className="text-xs text-primary-600 hover:text-primary-700"
            >
              Retry
            </button>
          )}
          {onDelete && (
            <button
              onClick={onDelete}
              className="text-xs text-red-600 hover:text-red-700"
            >
              Remove
            </button>
          )}
        </div>
      )}
    </div>
  )
}
