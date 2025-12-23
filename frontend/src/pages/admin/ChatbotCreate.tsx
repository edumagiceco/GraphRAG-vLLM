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
      newErrors.name = 'Chatbot name is required'
    }

    if (!formData.access_url.trim()) {
      newErrors.access_url = 'Access URL is required'
    } else if (!/^[a-z0-9][a-z0-9-]*[a-z0-9]$/.test(formData.access_url)) {
      newErrors.access_url = 'Access URL must be lowercase alphanumeric with hyphens'
    }

    if (!formData.persona.name.trim()) {
      newErrors['persona.name'] = 'Persona name is required'
    }

    if (!formData.persona.description.trim()) {
      newErrors['persona.description'] = 'Persona description is required'
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
          ← Back to Chatbots
        </button>
        <h1 className="text-2xl font-bold text-gray-900">Create Chatbot</h1>
        <p className="text-gray-600 mt-1">
          Set up a new GraphRAG chatbot service
        </p>
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="max-w-2xl">
        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Basic Information
          </h2>

          <div className="space-y-4">
            <Input
              label="Chatbot Name"
              name="name"
              value={formData.name}
              onChange={(e) => handleChange('name', e.target.value)}
              onBlur={generateAccessUrl}
              error={errors.name}
              placeholder="My Knowledge Base"
              required
            />

            <div>
              <Input
                label="Access URL"
                name="access_url"
                value={formData.access_url}
                onChange={(e) => handleChange('access_url', e.target.value.toLowerCase())}
                error={errors.access_url}
                placeholder="my-chatbot"
                helperText={`Public URL: /chat/${formData.access_url || 'your-url'}`}
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Description
              </label>
              <textarea
                name="description"
                value={formData.description}
                onChange={(e) => handleChange('description', e.target.value)}
                className="input min-h-[80px]"
                placeholder="A brief description of this chatbot..."
                rows={3}
              />
            </div>
          </div>
        </div>

        <div className="card mb-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Persona Configuration
          </h2>

          <div className="space-y-4">
            <Input
              label="Persona Name"
              name="persona_name"
              value={formData.persona.name}
              onChange={(e) => handlePersonaChange('name', e.target.value)}
              error={errors['persona.name']}
              placeholder="Assistant"
              required
            />

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Persona Description <span className="text-red-500">*</span>
              </label>
              <textarea
                name="persona_description"
                value={formData.persona.description}
                onChange={(e) => handlePersonaChange('description', e.target.value)}
                className={`input min-h-[80px] ${
                  errors['persona.description'] ? 'border-red-300' : ''
                }`}
                placeholder="A helpful assistant that answers questions..."
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
                Greeting Message
              </label>
              <textarea
                name="greeting"
                value={formData.persona.greeting}
                onChange={(e) => handlePersonaChange('greeting', e.target.value)}
                className="input min-h-[60px]"
                placeholder="Hello! How can I help you today?"
                rows={2}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Custom System Prompt
              </label>
              <textarea
                name="system_prompt"
                value={formData.persona.system_prompt}
                onChange={(e) => handlePersonaChange('system_prompt', e.target.value)}
                className="input min-h-[100px] font-mono text-sm"
                placeholder="Optional: Custom instructions for the LLM..."
                rows={4}
              />
              <p className="mt-1 text-xs text-gray-500">
                Advanced: Override the default system prompt for fine-grained control.
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
            Create Chatbot
          </Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => navigate('/admin/chatbots')}
          >
            Cancel
          </Button>
        </div>
      </form>
    </Layout>
  )
}
