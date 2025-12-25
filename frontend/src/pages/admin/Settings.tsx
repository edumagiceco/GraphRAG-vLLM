/**
 * System Settings page for vLLM model configuration.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import Button from '@/components/Button'
import {
  getSystemSettings,
  getAvailableModels,
  updateTimezone,
  testVLLMConnection,
  reprocessDocuments,
} from '@/services/settings'

// GMT timezone options
const TIMEZONE_OPTIONS = [
  { value: 'GMT-12', label: 'GMT-12 (Baker Island)' },
  { value: 'GMT-11', label: 'GMT-11 (American Samoa)' },
  { value: 'GMT-10', label: 'GMT-10 (Hawaii)' },
  { value: 'GMT-9', label: 'GMT-9 (Alaska)' },
  { value: 'GMT-8', label: 'GMT-8 (Pacific Time)' },
  { value: 'GMT-7', label: 'GMT-7 (Mountain Time)' },
  { value: 'GMT-6', label: 'GMT-6 (Central Time)' },
  { value: 'GMT-5', label: 'GMT-5 (Eastern Time)' },
  { value: 'GMT-4', label: 'GMT-4 (Atlantic Time)' },
  { value: 'GMT-3', label: 'GMT-3 (Brazil)' },
  { value: 'GMT-2', label: 'GMT-2 (Mid-Atlantic)' },
  { value: 'GMT-1', label: 'GMT-1 (Azores)' },
  { value: 'GMT+0', label: 'GMT+0 (London, UTC)' },
  { value: 'GMT+1', label: 'GMT+1 (Paris, Berlin)' },
  { value: 'GMT+2', label: 'GMT+2 (Cairo, Athens)' },
  { value: 'GMT+3', label: 'GMT+3 (Moscow, Istanbul)' },
  { value: 'GMT+4', label: 'GMT+4 (Dubai)' },
  { value: 'GMT+5', label: 'GMT+5 (Pakistan)' },
  { value: 'GMT+5:30', label: 'GMT+5:30 (India)' },
  { value: 'GMT+6', label: 'GMT+6 (Bangladesh)' },
  { value: 'GMT+7', label: 'GMT+7 (Bangkok, Jakarta)' },
  { value: 'GMT+8', label: 'GMT+8 (Singapore, Beijing)' },
  { value: 'GMT+9', label: 'GMT+9 (Tokyo, Seoul)' },
  { value: 'GMT+10', label: 'GMT+10 (Sydney)' },
  { value: 'GMT+11', label: 'GMT+11 (Solomon Islands)' },
  { value: 'GMT+12', label: 'GMT+12 (Auckland, Fiji)' },
]

export default function Settings() {
  const queryClient = useQueryClient()
  const [selectedTimezone, setSelectedTimezone] = useState<string>('GMT+0')

  // Fetch current settings
  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: getSystemSettings,
  })

  // Sync selected values with fetched settings
  useEffect(() => {
    if (settings) {
      setSelectedTimezone(settings.timezone)
    }
  }, [settings])

  // Fetch available models
  const { data: availableModels, isLoading: modelsLoading } = useQuery({
    queryKey: ['available-models'],
    queryFn: getAvailableModels,
  })

  // Connection test
  const connectionMutation = useMutation({
    mutationFn: testVLLMConnection,
  })

  // Update timezone
  const updateTimezoneMutation = useMutation({
    mutationFn: updateTimezone,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
    },
  })

  // Reprocess documents
  const reprocessMutation = useMutation({
    mutationFn: () => reprocessDocuments(undefined, true),
  })

  const handleTestConnection = () => {
    connectionMutation.mutate()
  }

  const handleSaveTimezone = () => {
    if (selectedTimezone && selectedTimezone !== settings?.timezone) {
      updateTimezoneMutation.mutate(selectedTimezone)
    }
  }

  const handleReprocess = () => {
    if (window.confirm('모든 문서를 재처리하시겠습니까?\n이 작업은 시간이 소요될 수 있습니다.')) {
      reprocessMutation.mutate()
    }
  }

  if (settingsLoading) {
    return (
      <Layout>
        <div className="flex items-center justify-center h-64">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-600" />
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        <h1 className="text-2xl font-bold text-gray-900 mb-6">시스템 설정</h1>

        {/* vLLM Connection Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">vLLM 서버 설정</h2>

          <div className="space-y-4">
            {/* LLM Server URL */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  LLM 서버 URL
                </label>
                <input
                  type="text"
                  value={settings?.vllm_base_url || ''}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  임베딩 서버 URL
                </label>
                <input
                  type="text"
                  value={settings?.vllm_embedding_url || ''}
                  readOnly
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 font-mono text-sm"
                />
              </div>
            </div>

            <div className="flex items-center gap-4">
              <Button
                onClick={handleTestConnection}
                isLoading={connectionMutation.isPending}
                variant="secondary"
              >
                연결 테스트
              </Button>

              {connectionMutation.data && (
                <div className="flex-1">
                  <div className="flex items-center gap-4">
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      connectionMutation.data.llm_connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      LLM: {connectionMutation.data.llm_connected ? '연결됨' : '연결 안됨'}
                    </span>
                    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                      connectionMutation.data.embedding_connected ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                    }`}>
                      임베딩: {connectionMutation.data.embedding_connected ? '연결됨' : '연결 안됨'}
                    </span>
                  </div>
                  {connectionMutation.data.error && (
                    <p className="text-sm text-red-600 mt-1">{connectionMutation.data.error}</p>
                  )}
                </div>
              )}
            </div>

            <p className="text-xs text-gray-500">
              vLLM 서버 URL은 환경 변수로 설정됩니다. 변경하려면 docker-compose.yml을 수정하세요.
            </p>
          </div>
        </div>

        {/* Current Models */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">현재 모델 설정</h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                LLM 모델 (채팅용)
              </label>
              <div className="px-3 py-2 border border-gray-300 rounded-lg bg-gray-50">
                <span className="font-mono text-sm">{settings?.default_llm_model || '-'}</span>
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                임베딩 모델 (벡터 생성용)
              </label>
              <div className="px-3 py-2 border border-gray-300 rounded-lg bg-gray-50">
                <span className="font-mono text-sm">{settings?.embedding_model || '-'}</span>
              </div>
              <p className="text-xs text-gray-500 mt-1">
                차원: {settings?.embedding_dimension}
              </p>
            </div>
          </div>

          <p className="text-xs text-gray-500 mt-4">
            모델은 환경 변수(VLLM_MODEL, VLLM_EMBEDDING_MODEL)로 설정됩니다.
          </p>
        </div>

        {/* Document Reprocessing */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">문서 재처리</h2>

          <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg mb-4">
            <p className="text-sm text-yellow-800">
              <span className="font-semibold">주의:</span> 임베딩 모델이 변경된 경우, 기존 문서를 재처리해야 합니다.
              이 작업은 시간이 소요될 수 있습니다.
            </p>
          </div>

          <Button
            onClick={handleReprocess}
            isLoading={reprocessMutation.isPending}
            variant="secondary"
          >
            전체 문서 재처리
          </Button>

          {reprocessMutation.isSuccess && (
            <p className="text-sm text-green-600 mt-2">
              {reprocessMutation.data?.document_count}개 문서의 재처리가 시작되었습니다.
            </p>
          )}
        </div>

        {/* Timezone Settings */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">시간대 설정</h2>

          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                시스템 시간대
              </label>
              <select
                value={selectedTimezone}
                onChange={(e) => setSelectedTimezone(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
              >
                {TIMEZONE_OPTIONS.map((tz) => (
                  <option key={tz.value} value={tz.value}>
                    {tz.label}
                  </option>
                ))}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                내부 데이터 처리 및 표시에 사용되는 시간대입니다.
              </p>
            </div>
            <Button
              onClick={handleSaveTimezone}
              isLoading={updateTimezoneMutation.isPending}
              disabled={selectedTimezone === settings?.timezone}
            >
              저장
            </Button>
          </div>

          {updateTimezoneMutation.isSuccess && (
            <p className="text-sm text-green-600 mt-2">시간대가 변경되었습니다.</p>
          )}
          {updateTimezoneMutation.isError && (
            <p className="text-sm text-red-600 mt-2">
              시간대 변경 실패: {(updateTimezoneMutation.error as Error)?.message}
            </p>
          )}
        </div>

        {/* Available Models List */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            사용 가능한 모델 ({availableModels?.total || 0}개)
          </h2>

          {modelsLoading ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-10 bg-gray-200 rounded" />
              ))}
            </div>
          ) : (
            <div className="space-y-4">
              {/* Chat Models */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">LLM 모델</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">모델 이름</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {availableModels?.chat_models.map((model) => (
                        <tr key={model.name} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 font-mono">{model.name}</td>
                          <td className="px-4 py-3 text-sm">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              활성
                            </span>
                          </td>
                        </tr>
                      ))}
                      {(!availableModels?.chat_models || availableModels.chat_models.length === 0) && (
                        <tr>
                          <td colSpan={2} className="px-4 py-3 text-sm text-gray-500 text-center">
                            연결된 LLM 모델이 없습니다
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Embedding Models */}
              <div>
                <h3 className="text-sm font-medium text-gray-700 mb-2">임베딩 모델</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">모델 이름</th>
                        <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">상태</th>
                      </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                      {availableModels?.embedding_models.map((model) => (
                        <tr key={model.name} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm font-medium text-gray-900 font-mono">{model.name}</td>
                          <td className="px-4 py-3 text-sm">
                            <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                              활성
                            </span>
                          </td>
                        </tr>
                      ))}
                      {(!availableModels?.embedding_models || availableModels.embedding_models.length === 0) && (
                        <tr>
                          <td colSpan={2} className="px-4 py-3 text-sm text-gray-500 text-center">
                            연결된 임베딩 모델이 없습니다
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
