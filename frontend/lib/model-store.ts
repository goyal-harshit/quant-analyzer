import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export type Provider = 'ollama' | 'openai' | 'anthropic' | 'gemini' | 'groq'

export interface ModelOption {
  id: string
  label: string
  provider: Provider
  requiresKey: boolean
  free: boolean
  note?: string
}

export const PROVIDERS: Record<Provider, { label: string; color: string; keyPlaceholder: string }> = {
  ollama:    { label: 'Ollama (Local)',   color: '#22c55e', keyPlaceholder: '' },
  openai:    { label: 'OpenAI',           color: '#a78bfa', keyPlaceholder: 'sk-...' },
  anthropic: { label: 'Anthropic',        color: '#f59e0b', keyPlaceholder: 'sk-ant-...' },
  gemini:    { label: 'Google Gemini',    color: '#06b6d4', keyPlaceholder: 'AIza...' },
  groq:      { label: 'Groq',             color: '#f43f5e', keyPlaceholder: 'gsk_...' },
}

export const MODEL_OPTIONS: ModelOption[] = [
  // Ollama — local, free
  { id: 'llama3.2',        label: 'Llama 3.2 (3B)',        provider: 'ollama',    requiresKey: false, free: true, note: '8GB RAM' },
  { id: 'llama3.1',        label: 'Llama 3.1 (8B)',        provider: 'ollama',    requiresKey: false, free: true, note: '16GB RAM' },
  { id: 'mistral',         label: 'Mistral (7B)',           provider: 'ollama',    requiresKey: false, free: true, note: '16GB RAM' },
  { id: 'qwen2.5',         label: 'Qwen 2.5 (7B)',         provider: 'ollama',    requiresKey: false, free: true, note: '16GB RAM' },
  { id: 'phi3',            label: 'Phi-3 (3.8B)',          provider: 'ollama',    requiresKey: false, free: true, note: '8GB RAM' },
  { id: 'gemma2',          label: 'Gemma 2 (9B)',          provider: 'ollama',    requiresKey: false, free: true, note: '16GB RAM' },
  // Groq — API key, free tier available
  { id: 'llama-3.3-70b-versatile', label: 'Llama 3.3 (70B)',    provider: 'groq', requiresKey: true, free: true,  note: 'Free tier' },
  { id: 'mixtral-8x7b-32768',      label: 'Mixtral 8x7B',       provider: 'groq', requiresKey: true, free: true,  note: 'Free tier' },
  { id: 'llama-3.1-8b-instant',    label: 'Llama 3.1 (8B Fast)', provider: 'groq', requiresKey: true, free: true, note: 'Free tier' },
  // OpenAI
  { id: 'gpt-4o-mini',   label: 'GPT-4o Mini',   provider: 'openai',    requiresKey: true,  free: false },
  { id: 'gpt-4o',        label: 'GPT-4o',         provider: 'openai',    requiresKey: true,  free: false },
  { id: 'gpt-3.5-turbo', label: 'GPT-3.5 Turbo', provider: 'openai',    requiresKey: true,  free: false },
  // Anthropic
  { id: 'claude-3-haiku-20240307',       label: 'Claude 3 Haiku',   provider: 'anthropic', requiresKey: true, free: false },
  { id: 'claude-3-5-sonnet-20241022',    label: 'Claude 3.5 Sonnet', provider: 'anthropic', requiresKey: true, free: false },
  // Gemini
  { id: 'gemini-1.5-flash', label: 'Gemini 1.5 Flash', provider: 'gemini', requiresKey: true, free: true,  note: 'Free tier' },
  { id: 'gemini-1.5-pro',   label: 'Gemini 1.5 Pro',   provider: 'gemini', requiresKey: true, free: false },
  { id: 'gemini-2.0-flash', label: 'Gemini 2.0 Flash', provider: 'gemini', requiresKey: true, free: true,  note: 'Free tier' },
]

interface ModelState {
  provider: Provider
  modelId: string
  apiKeys: Partial<Record<Provider, string>>
  setProvider: (p: Provider) => void
  setModelId: (id: string) => void
  setApiKey: (provider: Provider, key: string) => void
  getApiKey: () => string
  getActiveModel: () => ModelOption | undefined
}

export const useModelStore = create<ModelState>()(
  persist(
    (set, get) => ({
      provider: 'ollama',
      modelId: 'llama3.2',
      apiKeys: {},

      setProvider: (provider) => {
        const first = MODEL_OPTIONS.find(m => m.provider === provider)
        set({ provider, modelId: first?.id ?? '' })
      },

      setModelId: (modelId) => set({ modelId }),

      setApiKey: (provider, key) =>
        set(s => ({ apiKeys: { ...s.apiKeys, [provider]: key } })),

      getApiKey: () => {
        const { provider, apiKeys } = get()
        return apiKeys[provider] ?? ''
      },

      getActiveModel: () => {
        const { modelId } = get()
        return MODEL_OPTIONS.find(m => m.id === modelId)
      },
    }),
    { name: 'quantai-model-store' }
  )
)
