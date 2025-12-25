/**
 * Metric card component for displaying statistics.
 */

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon?: React.ReactNode
  trend?: {
    value: number
    isPositive?: boolean
  }
  className?: string
}

export default function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  className = '',
}: MetricCardProps) {
  return (
    <div className={`card ${className}`}>
      <div className="flex items-start justify-between">
        <div className="flex-1">
          <div className="text-sm text-gray-500">{title}</div>
          <div className="text-3xl font-bold text-gray-900 mt-1">{value}</div>
          {subtitle && <div className="text-sm text-gray-500 mt-1">{subtitle}</div>}
          {trend && (
            <div
              className={`text-sm mt-1 ${
                trend.isPositive ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {trend.isPositive ? '+' : ''}
              {trend.value}%
            </div>
          )}
        </div>
        {icon && (
          <div className="p-2 bg-primary-50 rounded-lg text-primary-600">{icon}</div>
        )}
      </div>
    </div>
  )
}
