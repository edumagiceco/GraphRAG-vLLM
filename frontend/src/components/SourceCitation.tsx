/**
 * Source citation display component.
 */
interface Source {
  source: string
  filename?: string
  page?: number
  entity?: string
  entity_type?: string
  score?: number
}

interface SourceCitationProps {
  sources: Source[]
  maxVisible?: number
}

export default function SourceCitation({
  sources,
  maxVisible = 3,
}: SourceCitationProps) {
  const visibleSources = sources.slice(0, maxVisible)
  const hasMore = sources.length > maxVisible

  if (sources.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2">
      {visibleSources.map((source, index) => (
        <SourceBadge key={index} source={source} index={index + 1} />
      ))}
      {hasMore && (
        <span className="text-xs text-gray-500 self-center">
          +{sources.length - maxVisible} more
        </span>
      )}
    </div>
  )
}

function SourceBadge({ source, index }: { source: Source; index: number }) {
  const getLabel = () => {
    if (source.filename) {
      const page = source.page ? ` p.${source.page}` : ''
      return `${source.filename}${page}`
    }
    if (source.entity) {
      return source.entity
    }
    return `Source ${index}`
  }

  const getIcon = () => {
    if (source.source === 'graph') {
      return (
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
        </svg>
      )
    }
    return (
      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
      </svg>
    )
  }

  const bgColor = source.source === 'graph'
    ? 'bg-purple-50 text-purple-700 border-purple-200'
    : 'bg-blue-50 text-blue-700 border-blue-200'

  return (
    <div
      className={`inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs border ${bgColor}`}
      title={`${source.source === 'graph' ? 'Knowledge Graph' : 'Document'}: ${getLabel()}`}
    >
      {getIcon()}
      <span className="max-w-[120px] truncate">{getLabel()}</span>
      {source.score && (
        <span className="text-xs opacity-60">
          {Math.round(source.score * 100)}%
        </span>
      )}
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
