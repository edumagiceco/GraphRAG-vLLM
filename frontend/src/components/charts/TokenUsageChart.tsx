/**
 * Token usage chart using Recharts.
 */
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'

interface DailyTokenStats {
  date: string
  input_tokens: number
  output_tokens: number
}

interface TokenUsageChartProps {
  data: DailyTokenStats[]
  title?: string
}

function formatTokens(value: number): string {
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`
  }
  return value.toString()
}

export default function TokenUsageChart({
  data,
  title = '토큰 사용량',
}: TokenUsageChartProps) {
  // Transform data for display
  const chartData = data.map((item) => ({
    ...item,
    displayDate: item.date.slice(5), // MM-DD format
    total: item.input_tokens + item.output_tokens,
  }))

  return (
    <div className="card">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">{title}</h3>
      {data.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          데이터가 없습니다.
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={chartData}
              margin={{ top: 5, right: 30, left: 20, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
              <XAxis
                dataKey="displayDate"
                tick={{ fill: '#6b7280', fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
              />
              <YAxis
                tick={{ fill: '#6b7280', fontSize: 12 }}
                axisLine={{ stroke: '#d1d5db' }}
                tickFormatter={formatTokens}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#fff',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
                }}
                formatter={(value, name) => [
                  Number(value).toLocaleString(),
                  name === 'input_tokens' ? '입력 토큰' : '출력 토큰',
                ]}
                labelFormatter={(label) => `날짜: ${label}`}
              />
              <Legend
                formatter={(value) =>
                  value === 'input_tokens' ? '입력 토큰' : '출력 토큰'
                }
              />
              <Bar
                dataKey="input_tokens"
                name="input_tokens"
                stackId="tokens"
                fill="#6366f1"
                radius={[0, 0, 0, 0]}
              />
              <Bar
                dataKey="output_tokens"
                name="output_tokens"
                stackId="tokens"
                fill="#a5b4fc"
                radius={[4, 4, 0, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}
