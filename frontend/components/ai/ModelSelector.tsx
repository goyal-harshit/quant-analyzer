'use client'

import { useState } from 'react'
import { ChevronDown, Key, Check, Cpu, Cloud, Lock } from 'lucide-react'
import { useModelStore, MODEL_OPTIONS, PROVIDERS, Provider } from '@/lib/model-store'

export default function ModelSelector({ compact = false }: { compact?: boolean }) {
  const { provider, modelId, apiKeys, setProvider, setModelId, setApiKey, getActiveModel } = useModelStore()
  const [open, setOpen] = useState(false)
  const [keyInputs, setKeyInputs] = useState<Partial<Record<Provider, string>>>({})

  const active = getActiveModel()
  const providerInfo = PROVIDERS[provider]
  const needsKey = active?.requiresKey && !apiKeys[provider]
  const modelsForProvider = MODEL_OPTIONS.filter(m => m.provider === provider)

  const handleKeySubmit = (p: Provider) => {
    const key = keyInputs[p]?.trim()
    if (key) {
      setApiKey(p, key)
      setKeyInputs(prev => ({ ...prev, [p]: '' }))
    }
  }

  if (compact) {
    return (
      <div className="relative">
        <button
          onClick={() => setOpen(o => !o)}
          className={`flex items-center gap-1.5 px-2 py-1 rounded-md border text-[10px] font-mono font-semibold transition-all ${
            needsKey
              ? 'border-warn/40 text-warn bg-warn/10'
              : 'border-border/60 text-textSub hover:text-textPrimary hover:border-brand/40 bg-elevated'
          }`}
        >
          {provider === 'ollama' ? <Cpu className="w-3 h-3" /> : <Cloud className="w-3 h-3" />}
          <span className="max-w-[90px] truncate">{active?.label ?? modelId}</span>
          {needsKey && <Lock className="w-2.5 h-2.5" />}
          <ChevronDown className={`w-3 h-3 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>

        {open && (
          <div
            className="absolute bottom-full mb-2 left-0 z-50 w-72 bg-card border border-border rounded-xl shadow-2xl overflow-hidden"
            onMouseLeave={() => setOpen(false)}
          >
            <ModelSelectorPanel
              provider={provider}
              modelId={modelId}
              apiKeys={apiKeys}
              keyInputs={keyInputs}
              setProvider={setProvider}
              setModelId={setModelId}
              setKeyInputs={setKeyInputs}
              handleKeySubmit={handleKeySubmit}
              onClose={() => setOpen(false)}
            />
          </div>
        )}
      </div>
    )
  }

  return (
    <ModelSelectorPanel
      provider={provider}
      modelId={modelId}
      apiKeys={apiKeys}
      keyInputs={keyInputs}
      setProvider={setProvider}
      setModelId={setModelId}
      setKeyInputs={setKeyInputs}
      handleKeySubmit={handleKeySubmit}
    />
  )
}

function ModelSelectorPanel({
  provider, modelId, apiKeys, keyInputs,
  setProvider, setModelId, setKeyInputs, handleKeySubmit, onClose
}: any) {
  const providerInfo = PROVIDERS[provider as Provider]
  const modelsForProvider = MODEL_OPTIONS.filter(m => m.provider === provider)
  const hasKey = !!apiKeys[provider]

  return (
    <div className="p-3 space-y-3">
      {/* Provider tabs */}
      <div>
        <div className="text-[9px] text-textMuted uppercase tracking-widest font-semibold mb-1.5">Provider</div>
        <div className="grid grid-cols-3 gap-1">
          {(Object.entries(PROVIDERS) as [Provider, any][]).map(([p, info]) => (
            <button
              key={p}
              onClick={() => setProvider(p)}
              className={`px-2 py-1.5 rounded-md text-[10px] font-semibold border transition-all truncate ${
                provider === p
                  ? 'border-current text-current bg-current/10'
                  : 'border-border/40 text-textMuted hover:border-border hover:text-textSub'
              }`}
              style={provider === p ? { color: info.color, borderColor: `${info.color}60`, background: `${info.color}15` } : {}}
            >
              {p === 'ollama' ? '⚡ ' : '☁️ '}{info.label.split(' ')[0]}
            </button>
          ))}
        </div>
      </div>

      {/* Model list */}
      <div>
        <div className="text-[9px] text-textMuted uppercase tracking-widest font-semibold mb-1.5">Model</div>
        <div className="space-y-0.5 max-h-40 overflow-y-auto">
          {modelsForProvider.map(m => (
            <button
              key={m.id}
              onClick={() => { setModelId(m.id); onClose?.() }}
              className={`w-full flex items-center justify-between px-2.5 py-1.5 rounded-md text-left transition-all ${
                modelId === m.id
                  ? 'bg-brand/15 border border-brand/30 text-brand'
                  : 'hover:bg-elevated text-textSub hover:text-textPrimary border border-transparent'
              }`}
            >
              <span className="text-xs font-medium">{m.label}</span>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                {m.note && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-elevated border border-border/60 text-textMuted font-mono">
                    {m.note}
                  </span>
                )}
                {m.free && (
                  <span className="text-[9px] px-1.5 py-0.5 rounded bg-success/10 border border-success/30 text-success font-semibold">
                    FREE
                  </span>
                )}
                {modelId === m.id && <Check className="w-3 h-3 text-brand" />}
              </div>
            </button>
          ))}
        </div>
      </div>

      {/* API Key input (cloud providers only) */}
      {provider !== 'ollama' && (
        <div>
          <div className="text-[9px] text-textMuted uppercase tracking-widest font-semibold mb-1.5 flex items-center gap-1">
            <Key className="w-2.5 h-2.5" />
            API Key {hasKey && <span className="text-success">✓ saved</span>}
          </div>
          <div className="flex gap-1.5">
            <input
              type="password"
              placeholder={hasKey ? '••••••••••••• (saved)' : PROVIDERS[provider as Provider].keyPlaceholder}
              value={keyInputs[provider] ?? ''}
              onChange={e => setKeyInputs((p: any) => ({ ...p, [provider]: e.target.value }))}
              onKeyDown={e => e.key === 'Enter' && handleKeySubmit(provider)}
              className="flex-1 bg-elevated border border-border/60 rounded-md px-2 py-1 text-xs text-textPrimary placeholder:text-textMuted focus:outline-none focus:border-brand/60 font-mono"
            />
            <button
              onClick={() => handleKeySubmit(provider)}
              className="px-2.5 py-1 bg-brand text-white rounded-md text-xs font-semibold hover:bg-brand/80 transition-colors"
            >
              Save
            </button>
          </div>
          <div className="text-[9px] text-textMuted mt-1">Stored in browser only — never sent to our servers except to forward your request.</div>
        </div>
      )}

      {/* Ollama setup hint */}
      {provider === 'ollama' && (
        <div className="text-[9px] text-textMuted bg-elevated/60 rounded-md px-2.5 py-2 border border-border/40 font-mono leading-relaxed">
          ollama serve<br />
          ollama pull {modelId}
        </div>
      )}
    </div>
  )
}
