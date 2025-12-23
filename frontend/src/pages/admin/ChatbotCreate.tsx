/**
 * Chatbot creation page.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'

import Layout from '@/components/Layout'
import Button from '@/components/Button'
import Input from '@/components/Input'
import { createChatbot, CreateChatbotRequest } from '@/services/chatbots'
import { getErrorMessage } from '@/services/api'

export default function ChatbotCreate() {
  const navigate = useNavigate()
  const [formData, setFormData] = useState<CreateChatbotRequest>({
    name: '',
    description: '',
    access_url: '',
    persona: {
      name: '',
      description: '',
      greeting: '안녕하세요! 무엇을 도와드릴까요?',
      system_prompt: '',
    },
  })
  const [errors, setErrors] = useState<Record<string, string>>({})

  const mutation = useMutation({
    mutationFn: createChatbot,
    onSuccess: (data) => {
      navigate(`/admin/chatbots/${data.id}`)
    },
  })

  const handleChange = (field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      [field]: value,
    }))
    setErrors((prev) => ({ ...prev, [field]: '' }))
  }

  const handlePersonaChange = (field: string, value: string) => {
    setFormData((prev) => ({
      ...prev,
      persona: {
        ...prev.persona,
        [field]: value,
      },
    }))
    setErrors((prev) => ({ ...prev, [`persona.${field}`]: '' }))
  }

  const generateAccessUrl = () => {
    const slug = formData.name
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/^-|-$/g, '')

    if (slug) {
      handleChange('access_url', slug)
    }
  }

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!formData.name.trim()) {
      newErrors.name = '챗봇 이름은 필수입니다'
    }

    if (!formData.access_url.trim()) {
      newErrors.access_url = '접근 URL은 필수입니다'
    } else if (!/^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(formData.access_url)) {
      newErrors.access_url = '접근 URL은 소문자, 숫자, 하이픈만 사용 가능합니다'
    }

    if (!formData.persona.name.trim()) {
      newErrors['persona.name'] = '페르소나 이름은 필수입니다'
    }

    if (!formData.persona.description.trim()) {
      newErrors['persona.description'] = '페르소나 설명은 필수입니다'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!validate()) return

    mutation.mutate(formData)
  }

  return (
    <Layout>
      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate('/admin/chatbots')}
          className="text-sm text-gray-500 hover:text-gray-700 mb-2"
        >
          ← 챗봇 목록으로
        </button>
        <h1 className="text-2xl font-bold text-gray-900">챗봇 생성</h1>
        <p className="text-gray-600 mt-1">
          새로운 GraphRAG 챗봇 서비스를 설정하세요
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="max-w-2xl">
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            기본 정보
          </h2>

          <div className="space-y-4">
            <Input
              label="챗봇 이름"
              name="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              onBlur={generateAccessUrl}
              error={errors.name}
              placeholder="나의 지식 베이스"
              required
            />

            <div>
              <Input
                label="접근 URL"
                name="access_url"
                value={formData.access_url}
                onChange={(e) => handleChange('access_url', e.target.value.toLowerCase())}
                error={errors.access_url}
                placeholder="my-chatbot"
                helperText={`공개 URL: /chat/${formData.access_url || 'your-url'}`}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                설명
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                className="input min-h-[80px]"
                placeholder="이 챗봇에 대한 간단한 설명..."
                rows={3}
              />
            </div>
          </div>
        </div>

        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            페르소나 설정
          </h2>

          <div className="space-y-4">
            <Input
              label="페르소나 이름"
              name="persona_name"
              value={formData.persona.name}
              onChange={(e) => handlePersonaChange('name', e.target.value)}
              error={errors['persona.name']}
              placeholder="어시스턴트"
              required
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                페르소나 설명 <span className="text-red-500">*</span>
              </label>
              <textarea
                name="persona_description"
                value={formData.persona.description}
                onChange={(e) => handlePersonaChange('description', e.target.value)}
                className={`input min-h-[80px] ${
                  errors['persona.description'] ? 'border-red-300' : ''
                }`}
                placeholder="질문에 답변하는 친절한 어시스턴트..."
                rows={3}
              />
              {errors['persona.description'] && (
                <p className="mt-1 text-sm text-red-600">
                  {errors['persona.description']}
                </p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                인사말
              </label>
              <textarea
                name="greeting"
                value={formData.persona.greeting}
                onChange={(e) => handlePersonaChange('greeting', e.target.value)}
                className="input min-h-[60px]"
                placeholder="안녕하세요! 무엇을 도와드릴까요?"
                rows={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                시스템 프롬프트
              </label>
              <textarea
                name="system_prompt"
                value={formData.persona.system_prompt}
                onChange={(e) => handlePersonaChange('system_prompt', e.target.value)}
                className="input min-h-[100px] font-mono text-sm"
                placeholder="선택사항: LLM을 위한 맞춤 지시사항..."
                rows={4}
              />
              <p className="mt-1 text-xs text-gray-500">
                고급: 세밀한 제어를 위해 기본 시스템 프롬프트를 재정의합니다.
              </p>
            </div>
          </div>
        </div>

        {/* Error message */}
        {mutation.error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {getErrorMessage(mutation.error)}
          </div>
        )}

        {/* Submit buttons */}
        <div className="flex gap-4">
          <Button
            type="submit"
            isLoading={mutation.isPending}
          >
            챗봇 생성
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate('/admin/chatbots')}
          >
            취소
          </Button>
        </div>
      </form>
    </Layout>
  )
}
