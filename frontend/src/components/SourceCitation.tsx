/**
 * Source citation display component.
 */
import { useState } from 'react'

interface Source {
  source: string
  filename?: string
  page?: number
  entity?: string
  entity_type?: string
  score?: number
  chunk_text?: string
}

interface SourceCitationProps {
  sources: Source[]
  maxVisible?: number
}

export default function SourceCitation({
  sources,
  maxVisible = 5,
}: SourceCitationProps) {
  const [isExpanded, setIsExpanded] = useState(false)
  const visibleSources = isExpanded ? sources : sources.slice(0, maxVisible)
  const hasMore = sources.length > maxVisible

  if (sources.length === 0) return null

  return (
    <div className="mt-3 bg-gray-50 rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
          📚 참고 출처 ({sources.length}개)
        </h4>
        {hasMore && (
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="text-xs text-primary-600 hover:text-primary-700"
          >
            {isExpanded ? '접기' : `+${sources.length - maxVisible}개 더보기`}
          </button>
        )}
      </div>
      <div className="space-y-2">
        {visibleSources.map((source, index) => (
          <SourceItem key={index} source={source} index={index + 1} />
        ))}
      </div>
    </div>
  )
}

function SourceItem({ source, index }: { source: Source; index: number }) {
  const [showPreview, setShowPreview] = useState(false)

  const getLabel = () => {
    if (source.filename) {
      const page = source.page ? `, 페이지 ${source.page}` : ''
      return `${source.filename}${page}`
    }
    if (source.entity) {
      const type = source.entity_type ? ` (${source.entity_type})` : ''
      return `${source.entity}${type}`
    }
    return `출처 ${index}`
  }

  const getSourceType = () => {
    return source.source === 'graph' ? '지식 그래프' : '문서'
  }

  const bgColor = source.source === 'graph'
    ? 'border-purple-200 bg-purple-50'
    : 'border-blue-200 bg-blue-50'

  const iconColor = source.source === 'graph'
    ? 'text-purple-600'
    : 'text-blue-600'

  return (
    <div className={`border rounded-lg p-2 ${bgColor}`}>
      <div className="flex items-start gap-2">
        <span className={`flex-shrink-0 w-5 h-5 rounded-full bg-white flex items-center justify-center text-xs font-medium ${iconColor}`}>
          {index}
        </span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-medium text-gray-800 truncate">
              {getLabel()}
            </span>
            <span className={`text-xs px-1.5 py-0.5 rounded ${source.source === 'graph' ? 'bg-purple-100 text-purple-700' : 'bg-blue-100 text-blue-700'}`}>
              {getSourceType()}
            </span>
            {source.score && (
              <span className="text-xs text-gray-500">
                관련도 {Math.round(source.score * 100)}%
              </span>
            )}
          </div>
          {source.chunk_text && (
            <div className="mt-1">
              <button
                onClick={() => setShowPreview(!showPreview)}
                className="text-xs text-gray-500 hover:text-gray-700"
              >
                {showPreview ? '내용 숨기기 ▲' : '내용 미리보기 ▼'}
              </button>
              {showPreview && (
                <p className="mt-1 text-xs text-gray-600 bg-white rounded p-2 line-clamp-3">
                  {source.chunk_text}
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

/**
 * Detailed sources list for expandable view.
 */
export function SourcesList({ sources }: { sources: Source[] }) {
  if (sources.length === 0) return null

  return (
    <div className="bg-gray-50 rounded-lg p-3 text-sm">
      <h4 className="font-medium text-gray-700 mb-2">Sources</h4>
      <ul className="space-y-2">
        {sources.map((source, index) => (
          <li key={index} className="flex items-start gap-2">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-200 text-gray-600 flex items-center justify-center text-xs">
              {index + 1}
            </span>
            <div>
              <div className="font-medium text-gray-800">
                {source.filename || source.entity || `Source ${index + 1}`}
              </div>
              <div className="text-gray-500 text-xs">
                {source.source === 'graph' ? (
                  <>Knowledge Graph{source.entity_type && ` - ${source.entity_type}`}</>
                ) : (
                  <>Document{source.page && ` - Page ${source.page}`}</>
                )}
                {source.score && ` (${Math.round(source.score * 100)}% relevance)`}
              </div>
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
