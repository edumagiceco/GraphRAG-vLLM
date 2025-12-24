/**
 * System Settings page for model configuration.
 */
import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import Layout from '@/components/Layout'
import Button from '@/components/Button'
import {
  getSystemSettings,
  getAvailableModels,
  updateDefaultLLMModel,
  updateEmbeddingModel,
  updateOllamaUrl,
  testOllamaConnection,
  reprocessDocuments,
} from '@/services/settings'

export default function Settings() {
  const queryClient = useQueryClient()
  const [selectedLLM, setSelectedLLM] = useState<string>('')
  const [selectedEmbedding, setSelectedEmbedding] = useState<string>('')
  const [ollamaUrl, setOllamaUrl] = useState<string>('')
  const [showReprocessWarning, setShowReprocessWarning] = useState(false)

  // Fetch current settings
  const { data: settings, isLoading: settingsLoading } = useQuery({
    queryKey: ['system-settings'],
    queryFn: getSystemSettings,
  })

  // Sync selected values with fetched settings
  useEffect(() => {
    if (settings) {
      setSelectedLLM(settings.default_llm_model)
      setSelectedEmbedding(settings.embedding_model)
      setOllamaUrl(settings.ollama_base_url)
    }
  }, [settings])

  // Fetch available models
  const { data: availableModels, isLoading: modelsLoading } = useQuery({
    queryKey: ['available-models'],
    queryFn: getAvailableModels,
  })

  // Connection test
  const connectionMutation = useMutation({
    mutationFn: testOllamaConnection,
  })

  // Update Ollama URL
  const updateUrlMutation = useMutation({
    mutationFn: updateOllamaUrl,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
      queryClient.invalidateQueries({ queryKey: ['available-models'] })
      connectionMutation.reset()
    },
  })

  // Update LLM model
  const updateLLMMutation = useMutation({
    mutationFn: updateDefaultLLMModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
    },
  })

  // Update embedding model
  const updateEmbeddingMutation = useMutation({
    mutationFn: updateEmbeddingModel,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['system-settings'] })
      setShowReprocessWarning(true)
    },
  })

  // Reprocess documents
  const reprocessMutation = useMutation({
    mutationFn: () => reprocessDocuments(undefined, true),
    onSuccess: () => {
      setShowReprocessWarning(false)
    },
  })

  const handleTestConnection = () => {
    connectionMutation.mutate()
  }

  const handleSaveUrl = () => {
    if (ollamaUrl && ollamaUrl !== settings?.ollama_base_url) {
      updateUrlMutation.mutate(ollamaUrl)
    }
  }

  const handleSaveLLM = () => {
    if (selectedLLM && selectedLLM !== settings?.default_llm_model) {
      updateLLMMutation.mutate(selectedLLM)
    }
  }

  const handleSaveEmbedding = () => {
    if (selectedEmbedding && selectedEmbedding !== settings?.embedding_model) {
      if (window.confirm(
        '임베딩 모델을 변경하면 기존 문서와 호환되지 않을 수 있습니다.\n' +
        '변경 후 문서 재처리가 필요합니다.\n\n계속하시겠습니까?'
      )) {
        updateEmbeddingMutation.mutate(selectedEmbedding)
      }
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

        {/* Ollama Connection Status */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Ollama 서버 설정</h2>

          <div className="space-y-4">
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Ollama 서버 URL
                </label>
                <input
                  type="text"
                  value={ollamaUrl}
                  onChange={(e) => setOllamaUrl(e.target.value)}
                  placeholder="http://localhost:11434"
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 font-mono text-sm"
                />
              </div>
              <Button
                onClick={handleSaveUrl}
                isLoading={updateUrlMutation.isPending}
                disabled={ollamaUrl === settings?.ollama_base_url}
              >
                저장
              </Button>
              <Button
                onClick={handleTestConnection}
                isLoading={connectionMutation.isPending}
                variant="secondary"
              >
                연결 테스트
              </Button>
            </div>

            {updateUrlMutation.isSuccess && (
              <p className="text-sm text-green-600">Ollama URL이 변경되었습니다.</p>
            )}
            {updateUrlMutation.isError && (
              <p className="text-sm text-red-600">
                URL 변경 실패: {(updateUrlMutation.error as Error)?.message}
              </p>
            )}

            {connectionMutation.data && (
              <p className={`text-sm ${connectionMutation.data.connected ? 'text-green-600' : 'text-red-600'}`}>
                {connectionMutation.data.connected
                  ? `연결됨 (버전: ${connectionMutation.data.ollama_version})`
                  : `연결 실패: ${connectionMutation.data.error}`}
              </p>
            )}
          </div>
        </div>

        {/* Default LLM Model */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">기본 LLM 모델</h2>

          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                채팅용 모델
              </label>
              <select
                value={selectedLLM}
                onChange={(e) => setSelectedLLM(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={modelsLoading}
              >
                {modelsLoading ? (
                  <option>모델 목록 불러오는 중...</option>
                ) : (
                  <>
                    {availableModels?.chat_models.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name} ({model.size_formatted})
                      </option>
                    ))}
                  </>
                )}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                챗봇별 설정이 없을 때 사용되는 기본 모델입니다.
              </p>
            </div>
            <Button
              onClick={handleSaveLLM}
              isLoading={updateLLMMutation.isPending}
              disabled={selectedLLM === settings?.default_llm_model}
            >
              저장
            </Button>
          </div>

          {updateLLMMutation.isSuccess && (
            <p className="text-sm text-green-600 mt-2">기본 LLM 모델이 변경되었습니다.</p>
          )}
          {updateLLMMutation.isError && (
            <p className="text-sm text-red-600 mt-2">
              모델 변경 실패: {(updateLLMMutation.error as Error)?.message}
            </p>
          )}
        </div>

        {/* Embedding Model */}
        <div className="bg-white rounded-lg shadow p-6 mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">임베딩 모델</h2>

          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                벡터 생성용 모델
              </label>
              <select
                value={selectedEmbedding}
                onChange={(e) => setSelectedEmbedding(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500"
                disabled={modelsLoading}
              >
                {modelsLoading ? (
                  <option>모델 목록 불러오는 중...</option>
                ) : (
                  <>
                    {availableModels?.embedding_models.map((model) => (
                      <option key={model.name} value={model.name}>
                        {model.name} ({model.size_formatted})
                      </option>
                    ))}
                  </>
                )}
              </select>
              <p className="text-xs text-gray-500 mt-1">
                현재 차원: {settings?.embedding_dimension}
              </p>
            </div>
            <Button
              onClick={handleSaveEmbedding}
              isLoading={updateEmbeddingMutation.isPending}
              disabled={selectedEmbedding === settings?.embedding_model}
            >
              저장
            </Button>
          </div>

          {/* Warning for embedding model change */}
          <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <p className="text-sm text-yellow-800">
              <span className="font-semibold">주의:</span> 임베딩 모델을 변경하면 기존에 처리된 문서의 벡터와 호환되지 않습니다.
              변경 후 모든 문서를 다시 처리해야 합니다.
            </p>
          </div>

          {updateEmbeddingMutation.isSuccess && (
            <p className="text-sm text-green-600 mt-2">임베딩 모델이 변경되었습니다.</p>
          )}

          {showReprocessWarning && (
            <div className="mt-4 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <p className="text-sm text-orange-800 mb-3">
                임베딩 모델이 변경되었습니다. 기존 문서가 제대로 검색되지 않을 수 있습니다.
              </p>
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
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">이름</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">크기</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">패밀리</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">파라미터</th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase">양자화</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {availableModels?.models.map((model) => (
                    <tr key={model.name} className="hover:bg-gray-50">
                      <td className="px-4 py-3 text-sm font-medium text-gray-900">{model.name}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{model.size_formatted}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{model.family || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{model.parameter_size || '-'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">{model.quantization_level || '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>
    </Layout>
  )
}
