/**
 * Chat input component with send button.
 */
import { useState, useRef, KeyboardEvent, FormEvent } from 'react'

interface ChatInputProps {
  onSend: (message: string) => void
  disabled?: boolean
  placeholder?: string
  isGenerating?: boolean
  onStop?: () => void
}

export default function ChatInput({
  onSend,
  disabled = false,
  placeholder = 'Type your message...',
  isGenerating = false,
  onStop,
}: ChatInputProps) {
  const [message, setMessage] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const handleSubmit = (e?: FormEvent) => {
    e?.preventDefault()
    if (message.trim() && !disabled && !isGenerating) {
      onSend(message.trim())
      setMessage('')
      // Reset textarea height
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    }
  }

  const handleInput = () => {
    const textarea = textareaRef.current
    if (textarea) {
      // Auto-resize
      textarea.style.height = 'auto'
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex items-end gap-2">
      <div className="flex-1 relative">
        <textarea
          ref={textareaRef}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={handleKeyDown}
          onInput={handleInput}
          placeholder={placeholder}
          disabled={disabled || isGenerating}
          rows={1}
          className="w-full resize-none rounded-2xl border border-gray-300 px-4 py-3 pr-12 focus:border-primary-500 focus:ring-2 focus:ring-primary-500 focus:ring-opacity-50 outline-none disabled:bg-gray-50 disabled:cursor-not-allowed transition-colors"
          style={{ maxHeight: '200px' }}
        />
      </div>

      {isGenerating ? (
        <button
          type="button"
          onClick={onStop}
          className="flex-shrink-0 w-12 h-12 rounded-full bg-red-500 text-white flex items-center justify-center hover:bg-red-600 transition-colors"
          title="Stop generating"
        >
          <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
            <rect x="6" y="6" width="12" height="12" rx="2" />
          </svg>
        </button>
      ) : (
        <button
          type="submit"
          disabled={disabled || !message.trim()}
          className="flex-shrink-0 w-12 h-12 rounded-full bg-primary-600 text-white flex items-center justify-center hover:bg-primary-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          title="Send message"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
          </svg>
        </button>
      )}
    </form>
  )
}
