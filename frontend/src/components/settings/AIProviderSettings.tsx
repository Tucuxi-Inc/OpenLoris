import { useState, useEffect } from 'react'
import {
  orgApi,
  AIProviderSettings,
  AIProviderUpdate,
  AIProviderType,
  AIModelInfo,
  AIProviderTestResult,
} from '../../lib/api/org'

const PROVIDER_OPTIONS: { value: AIProviderType; label: string; description: string }[] = [
  {
    value: 'local_ollama',
    label: 'Ollama (Local/Cloud)',
    description: 'Local models or Ollama cloud — maximum data privacy',
  },
  {
    value: 'cloud_anthropic',
    label: 'Anthropic Claude',
    description: 'Direct Anthropic API — data sent to third party',
  },
  {
    value: 'cloud_bedrock',
    label: 'AWS Bedrock',
    description: 'Claude via AWS — data stays in your VPC',
  },
  {
    value: 'cloud_azure',
    label: 'Azure OpenAI',
    description: 'GPT via Azure — data stays in your tenant',
  },
]

const AWS_REGIONS = [
  'us-east-1',
  'us-east-2',
  'us-west-2',
  'eu-west-1',
  'eu-west-2',
  'eu-central-1',
  'ap-northeast-1',
  'ap-southeast-1',
  'ap-southeast-2',
]

export default function AIProviderSettingsPanel() {
  const [settings, setSettings] = useState<AIProviderSettings | null>(null)
  const [models, setModels] = useState<AIModelInfo[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isTesting, setIsTesting] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [testResult, setTestResult] = useState<AIProviderTestResult | null>(null)

  // Form state
  const [formData, setFormData] = useState<AIProviderUpdate>({})
  const [showApiKeyInput, setShowApiKeyInput] = useState<'anthropic' | 'azure' | null>(null)
  const [apiKeyValue, setApiKeyValue] = useState('')
  const [showAdvanced, setShowAdvanced] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  useEffect(() => {
    if (settings) {
      loadModels()
    }
  }, [settings?.provider])

  const loadSettings = async () => {
    try {
      setIsLoading(true)
      const result = await orgApi.getAIProvider()
      setSettings(result)
      setFormData({
        provider: result.provider,
        model: result.model,
        ollama_url: result.ollama_url || undefined,
        ollama_fallback_model: result.ollama_fallback_model || undefined,
        azure_endpoint: result.azure_endpoint || undefined,
        azure_deployment: result.azure_deployment || undefined,
        aws_region: result.aws_region || undefined,
        max_tokens: result.max_tokens,
        temperature: result.temperature,
      })
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load settings')
    } finally {
      setIsLoading(false)
    }
  }

  const loadModels = async () => {
    try {
      const result = await orgApi.listAIModels()
      setModels(result)
    } catch {
      // Models not available — that's okay
      setModels([])
    }
  }

  const handleProviderChange = (provider: AIProviderType) => {
    setFormData((prev) => ({ ...prev, provider }))
    setTestResult(null)
  }

  const handleSave = async () => {
    setIsSaving(true)
    setError('')
    setSuccess('')
    setTestResult(null)

    try {
      const updateData: AIProviderUpdate = { ...formData }

      // Include API key if user entered one
      if (showApiKeyInput === 'anthropic' && apiKeyValue) {
        updateData.anthropic_api_key = apiKeyValue
      } else if (showApiKeyInput === 'azure' && apiKeyValue) {
        updateData.azure_api_key = apiKeyValue
      }

      const result = await orgApi.updateAIProvider(updateData)
      setSettings(result)
      setSuccess('AI provider settings saved.')
      setShowApiKeyInput(null)
      setApiKeyValue('')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings')
    } finally {
      setIsSaving(false)
    }
  }

  const handleTest = async () => {
    setIsTesting(true)
    setTestResult(null)
    setError('')

    try {
      // Save first if there are changes
      if (hasChanges) {
        await handleSave()
      }
      const result = await orgApi.testAIProvider()
      setTestResult(result)
    } catch (err) {
      setTestResult({
        success: false,
        message: err instanceof Error ? err.message : 'Test failed',
        provider: formData.provider || 'unknown',
        model: formData.model || '',
        response_preview: null,
      })
    } finally {
      setIsTesting(false)
    }
  }

  const handleClearApiKey = async (keyType: 'anthropic' | 'azure') => {
    setIsSaving(true)
    try {
      const updateData: AIProviderUpdate =
        keyType === 'anthropic' ? { anthropic_api_key: '' } : { azure_api_key: '' }
      const result = await orgApi.updateAIProvider(updateData)
      setSettings(result)
      setSuccess('API key cleared.')
      setTimeout(() => setSuccess(''), 3000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to clear API key')
    } finally {
      setIsSaving(false)
    }
  }

  const hasChanges =
    settings &&
    (formData.provider !== settings.provider ||
      formData.model !== settings.model ||
      formData.ollama_url !== (settings.ollama_url || undefined) ||
      formData.ollama_fallback_model !== (settings.ollama_fallback_model || undefined) ||
      formData.azure_endpoint !== (settings.azure_endpoint || undefined) ||
      formData.azure_deployment !== (settings.azure_deployment || undefined) ||
      formData.aws_region !== (settings.aws_region || undefined) ||
      formData.max_tokens !== settings.max_tokens ||
      formData.temperature !== settings.temperature ||
      showApiKeyInput !== null)

  if (isLoading) {
    return (
      <div className="card-tufte">
        <p className="font-serif text-ink-secondary">Loading AI provider settings...</p>
      </div>
    )
  }

  const currentProvider = formData.provider || settings?.provider || 'local_ollama'

  return (
    <div className="card-tufte">
      <h3 className="font-mono text-xs text-ink-tertiary tracking-wide uppercase mb-4">
        AI Provider
      </h3>
      <p className="font-serif text-sm text-ink-secondary mb-6">
        Configure which AI service Open Loris uses for inference. Different providers offer different
        trade-offs between capability, cost, and data privacy.
      </p>

      {error && (
        <div className="p-3 bg-cream-200 border border-status-error rounded-sm mb-4">
          <p className="font-serif text-sm text-status-error">{error}</p>
        </div>
      )}
      {success && (
        <div className="p-3 bg-cream-200 border border-status-success rounded-sm mb-4">
          <p className="font-serif text-sm text-status-success">{success}</p>
        </div>
      )}

      {/* Provider Selection */}
      <div className="mb-6">
        <label className="label-tufte">Provider</label>
        <div className="space-y-2">
          {PROVIDER_OPTIONS.map((opt) => (
            <label
              key={opt.value}
              className={`flex items-start gap-3 p-3 border rounded-sm cursor-pointer transition-colors ${
                currentProvider === opt.value
                  ? 'border-loris-brown bg-cream-200'
                  : 'border-rule-light hover:border-rule-medium'
              }`}
            >
              <input
                type="radio"
                name="provider"
                value={opt.value}
                checked={currentProvider === opt.value}
                onChange={() => handleProviderChange(opt.value)}
                className="mt-1"
              />
              <div>
                <span className="font-serif text-ink-primary">{opt.label}</span>
                <p className="font-mono text-[10px] text-ink-tertiary mt-0.5">{opt.description}</p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Provider-specific settings */}
      {currentProvider === 'local_ollama' && (
        <div className="space-y-4 mb-6 p-4 bg-cream-100 rounded-sm">
          <div>
            <label className="label-tufte">Ollama URL</label>
            <input
              type="text"
              value={formData.ollama_url || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, ollama_url: e.target.value }))}
              className="input-tufte w-full"
              placeholder="http://localhost:11434"
            />
            <p className="font-mono text-[10px] text-ink-tertiary mt-1">
              URL of your Ollama server. Use host.docker.internal for local Docker setups.
            </p>
          </div>

          <div>
            <label className="label-tufte">Model</label>
            <select
              value={formData.model || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, model: e.target.value }))}
              className="input-tufte w-full"
            >
              <option value="">Select a model...</option>
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                  {m.size && m.size > 1000000 ? ` (${(m.size / 1e9).toFixed(1)}GB)` : ''}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="label-tufte">Fallback Model (Optional)</label>
            <select
              value={formData.ollama_fallback_model || ''}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, ollama_fallback_model: e.target.value }))
              }
              className="input-tufte w-full"
            >
              <option value="">No fallback</option>
              {models
                .filter((m) => m.name !== formData.model)
                .map((m) => (
                  <option key={m.name} value={m.name}>
                    {m.name}
                  </option>
                ))}
            </select>
          </div>
        </div>
      )}

      {currentProvider === 'cloud_anthropic' && (
        <div className="space-y-4 mb-6 p-4 bg-cream-100 rounded-sm">
          <div>
            <label className="label-tufte">API Key</label>
            {settings?.anthropic_api_key_set && showApiKeyInput !== 'anthropic' ? (
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm text-ink-secondary">
                  {settings.anthropic_api_key_masked || '••••••••••••'}
                </span>
                <button
                  onClick={() => setShowApiKeyInput('anthropic')}
                  className="font-mono text-xs text-loris-brown hover:text-loris-brown-dark"
                >
                  Change
                </button>
                <button
                  onClick={() => handleClearApiKey('anthropic')}
                  className="font-mono text-xs text-status-error hover:text-ink-primary"
                >
                  Clear
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="password"
                  value={apiKeyValue}
                  onChange={(e) => {
                    setApiKeyValue(e.target.value)
                    setShowApiKeyInput('anthropic')
                  }}
                  className="input-tufte w-full"
                  placeholder="sk-ant-..."
                />
                {showApiKeyInput === 'anthropic' && (
                  <button
                    onClick={() => {
                      setShowApiKeyInput(null)
                      setApiKeyValue('')
                    }}
                    className="font-mono text-xs text-ink-tertiary hover:text-ink-secondary mt-1"
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="label-tufte">Model</label>
            <select
              value={formData.model || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, model: e.target.value }))}
              className="input-tufte w-full"
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {currentProvider === 'cloud_bedrock' && (
        <div className="space-y-4 mb-6 p-4 bg-cream-100 rounded-sm">
          <div>
            <label className="label-tufte">AWS Region</label>
            <select
              value={formData.aws_region || 'us-east-1'}
              onChange={(e) => setFormData((prev) => ({ ...prev, aws_region: e.target.value }))}
              className="input-tufte w-full"
            >
              {AWS_REGIONS.map((region) => (
                <option key={region} value={region}>
                  {region}
                </option>
              ))}
            </select>
            <p className="font-mono text-[10px] text-ink-tertiary mt-1">
              Uses IAM credentials from the server environment.
            </p>
          </div>

          <div>
            <label className="label-tufte">Model</label>
            <select
              value={formData.model || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, model: e.target.value }))}
              className="input-tufte w-full"
            >
              {models.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {currentProvider === 'cloud_azure' && (
        <div className="space-y-4 mb-6 p-4 bg-cream-100 rounded-sm">
          <div>
            <label className="label-tufte">Azure Endpoint</label>
            <input
              type="text"
              value={formData.azure_endpoint || ''}
              onChange={(e) => setFormData((prev) => ({ ...prev, azure_endpoint: e.target.value }))}
              className="input-tufte w-full"
              placeholder="https://your-resource.openai.azure.com"
            />
          </div>

          <div>
            <label className="label-tufte">API Key</label>
            {settings?.azure_api_key_set && showApiKeyInput !== 'azure' ? (
              <div className="flex items-center gap-3">
                <span className="font-mono text-sm text-ink-secondary">
                  {settings.azure_api_key_masked || '••••••••••••'}
                </span>
                <button
                  onClick={() => setShowApiKeyInput('azure')}
                  className="font-mono text-xs text-loris-brown hover:text-loris-brown-dark"
                >
                  Change
                </button>
                <button
                  onClick={() => handleClearApiKey('azure')}
                  className="font-mono text-xs text-status-error hover:text-ink-primary"
                >
                  Clear
                </button>
              </div>
            ) : (
              <div>
                <input
                  type="password"
                  value={apiKeyValue}
                  onChange={(e) => {
                    setApiKeyValue(e.target.value)
                    setShowApiKeyInput('azure')
                  }}
                  className="input-tufte w-full"
                  placeholder="Your Azure API key"
                />
                {showApiKeyInput === 'azure' && (
                  <button
                    onClick={() => {
                      setShowApiKeyInput(null)
                      setApiKeyValue('')
                    }}
                    className="font-mono text-xs text-ink-tertiary hover:text-ink-secondary mt-1"
                  >
                    Cancel
                  </button>
                )}
              </div>
            )}
          </div>

          <div>
            <label className="label-tufte">Deployment Name</label>
            <input
              type="text"
              value={formData.azure_deployment || ''}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, azure_deployment: e.target.value }))
              }
              className="input-tufte w-full"
              placeholder="gpt-4"
            />
          </div>
        </div>
      )}

      {/* Advanced Settings */}
      <div className="mb-6">
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="font-mono text-xs text-ink-secondary hover:text-ink-primary"
        >
          {showAdvanced ? '- Hide' : '+ Show'} advanced settings
        </button>

        {showAdvanced && (
          <div className="mt-4 space-y-4 p-4 bg-cream-100 rounded-sm">
            <div>
              <label className="label-tufte">Max Tokens</label>
              <input
                type="number"
                value={formData.max_tokens || 4096}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, max_tokens: parseInt(e.target.value) || 4096 }))
                }
                className="input-tufte w-32"
                min={100}
                max={32000}
              />
            </div>

            <div>
              <label className="label-tufte">Temperature</label>
              <input
                type="number"
                value={formData.temperature || 0.7}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    temperature: parseFloat(e.target.value) || 0.7,
                  }))
                }
                className="input-tufte w-32"
                min={0}
                max={2}
                step={0.1}
              />
              <p className="font-mono text-[10px] text-ink-tertiary mt-1">
                Lower values = more deterministic, higher = more creative
              </p>
            </div>
          </div>
        )}
      </div>

      {/* Data Privacy Info */}
      {settings && (
        <div className="mb-6 p-4 border border-rule-light rounded-sm">
          <div className="flex items-start gap-3">
            <span className="text-lg">
              {currentProvider === 'local_ollama' ? '🔒' : currentProvider === 'cloud_anthropic' ? '☁️' : '🛡️'}
            </span>
            <div>
              <p className="font-serif text-sm text-ink-primary">{settings.data_locality}</p>
              <p className="font-mono text-[10px] text-ink-tertiary mt-1">
                Privacy level: {settings.privacy_level}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Test Result */}
      {testResult && (
        <div
          className={`mb-6 p-4 border rounded-sm ${
            testResult.success ? 'border-status-success bg-cream-100' : 'border-status-error bg-cream-100'
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            <span>{testResult.success ? '✓' : '✗'}</span>
            <span
              className={`font-serif text-sm ${
                testResult.success ? 'text-status-success' : 'text-status-error'
              }`}
            >
              {testResult.message}
            </span>
          </div>
          {testResult.response_preview && (
            <p className="font-mono text-xs text-ink-secondary mt-2">
              Response: "{testResult.response_preview}"
            </p>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4">
        <button
          onClick={handleSave}
          disabled={isSaving || !hasChanges}
          className="btn-primary disabled:opacity-50"
        >
          {isSaving ? 'Saving...' : 'Save Settings'}
        </button>
        <button onClick={handleTest} disabled={isTesting} className="btn-secondary disabled:opacity-50">
          {isTesting ? 'Testing...' : 'Test Connection'}
        </button>
        {hasChanges && <span className="font-mono text-xs text-status-warning">Unsaved changes</span>}
      </div>
    </div>
  )
}
