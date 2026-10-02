// What the UI knows about an LLM provider: how to name it and which logo to draw.
// Icon names stay literal strings so Nuxt Icon can find and serve them.

export interface ProviderMeta {
  /** Canonical key: aliases and casing collapse into it ("Together_AI" -> "together") */
  key: string
  label: string
  icon: string
  /** Logo is black on transparent: inverted on dark surfaces so it doesn't vanish */
  mono: boolean
  /** No brand logo: a neutral icon stands in, drawn in the muted text colour */
  generic: boolean
}

type KnownProvider = Omit<ProviderMeta, 'key' | 'generic'> & { generic?: boolean }

const PROVIDERS: Record<string, KnownProvider> = {
  openai: { label: 'OpenAI', icon: 'i-logos-openai-icon', mono: true },
  anthropic: { label: 'Anthropic', icon: 'i-logos-anthropic-icon', mono: true },
  google: { label: 'Google', icon: 'i-logos-google-gemini-icon', mono: false },
  mistral: { label: 'Mistral', icon: 'i-logos-mistral-ai-icon', mono: false },
  meta: { label: 'Meta', icon: 'i-logos-meta-icon', mono: false },
  deepseek: { label: 'DeepSeek', icon: 'i-logos-deepseek-icon', mono: false },
  together: { label: 'Together AI', icon: 'i-logos-togetherai-icon', mono: false },
  xai: { label: 'xAI', icon: 'i-logos-grok-icon', mono: true },
  qwen: { label: 'Qwen', icon: 'i-logos-qwen-icon', mono: false },
  perplexity: { label: 'Perplexity', icon: 'i-logos-perplexity-icon', mono: false },
  cerebras: { label: 'Cerebras', icon: 'i-logos-cerebras-icon', mono: false },
  huggingface: { label: 'Hugging Face', icon: 'i-logos-hugging-face-icon', mono: false },
  azure: { label: 'Azure', icon: 'i-logos-azure-icon', mono: false },
  // Supported by the backend but absent from the logos set
  groq: { label: 'Groq', icon: 'i-lucide-zap', mono: false, generic: true },
  other: { label: 'Other', icon: 'i-lucide-box', mono: false, generic: true },
}

const ALIASES: Record<string, string> = {
  gemini: 'google',
  together_ai: 'together',
  togetherai: 'together',
  grok: 'xai',
  x_ai: 'xai',
  hugging_face: 'huggingface',
  hf: 'huggingface',
  alibaba: 'qwen',
}

function normalize(provider: string): string {
  const key = provider.trim().toLowerCase().replace(/[\s-]+/g, '_')
  return ALIASES[key] ?? key.replace(/_/g, '')
}

export function providerMeta(provider: string | null | undefined): ProviderMeta {
  const raw = (provider ?? '').trim()
  const key = normalize(raw) || 'other'
  const known = PROVIDERS[key]
  if (known)
    return { key, generic: false, ...known }

  return {
    key,
    label: raw.charAt(0).toUpperCase() + raw.slice(1),
    icon: 'i-lucide-cpu',
    mono: false,
    generic: true,
  }
}

// "together" -> "Together AI"; unknown providers get capitalized
export function providerLabel(provider: string): string {
  return providerMeta(provider).label
}

/** Alphabetical by the name people read ("Anthropic" before "Google"), whatever the stored key */
export function compareProviders(a: string, b: string): number {
  return providerLabel(a).localeCompare(providerLabel(b), 'en', { sensitivity: 'base' })
}

/** The choices of a provider field: the providers the backend can call, plus a catch-all */
export const PROVIDER_OPTIONS = ['openai', 'anthropic', 'google', 'mistral', 'meta', 'deepseek', 'groq', 'together', 'other']
  .toSorted(compareProviders)
  .map(value => ({ value, label: providerLabel(value), icon: providerMeta(value).icon }))
