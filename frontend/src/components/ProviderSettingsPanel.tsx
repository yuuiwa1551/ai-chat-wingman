import { apiBaseUrl, LlmProviderConfig } from '../api';

export type ProviderFeedbackKind = 'idle' | 'info' | 'success' | 'warning' | 'error';

export interface ProviderFeedback {
  kind: ProviderFeedbackKind;
  message: string;
}

interface ProviderSettingsPanelProps {
  provider: LlmProviderConfig;
  providersCount: number;
  providerModels: string[];
  providerFeedback: ProviderFeedback;
  hasStoredApiKey: boolean;
  streamText: string;
  requireRealProvider?: boolean;
  hideDiagnostics?: boolean;
  onProviderChange: (provider: LlmProviderConfig) => void;
  onSaveProvider: () => void;
  onListModels: () => void;
  onTestProvider: () => void;
  onDemoSse: () => void;
}

export function ProviderSettingsPanel({
  provider,
  providersCount,
  providerModels,
  providerFeedback,
  hasStoredApiKey,
  streamText,
  requireRealProvider = false,
  hideDiagnostics = false,
  onProviderChange,
  onSaveProvider,
  onListModels,
  onTestProvider,
  onDemoSse,
}: ProviderSettingsPanelProps) {
  const modelOptions = Array.from(new Set([provider.default_model, ...providerModels].filter(Boolean)));
  const isMock = provider.type === 'mock';
  const hasBaseUrl = Boolean(provider.base_url?.trim());
  const hasApiKey = Boolean(provider.api_key?.trim()) || hasStoredApiKey;
  const apiKeyInvalid = provider.api_key_status === 'invalid';
  const hasModel = Boolean(provider.default_model?.trim());
  const readyForNetworkTest = !isMock && hasBaseUrl && hasApiKey && hasModel;
  const nextAction = isMock
    ? '切换到 openai_compatible 后填写真实模型配置。'
    : apiKeyInvalid
      ? '本机 API Key 密钥文件已失效，请重新填写并保存。'
    : readyForNetworkTest
      ? '现在可以检测模型或直接测试连通。'
      : '补齐 Base URL、API Key 和模型名后再测试。';

  return (
    <section className="settings-layout">
      <div className="settings-card">
        <div className="section-heading">
          <h2>{requireRealProvider ? '连接真实模型' : 'Provider 设置'}</h2>
          <span>
            {providersCount} 个真实 Provider · {apiBaseUrl}
          </span>
        </div>
        <div className={`provider-mode-callout ${providersCount ? 'ready' : 'mock'}`}>
          <strong>{providersCount ? '真实 Provider 可用' : requireRealProvider ? '首次使用必须配置真实 Provider' : '当前是 Mock 演示模式'}</strong>
          <p>
            {providersCount
              ? '生成会优先走已保存的 provider；如果测试失败，请重新检测模型或检查 Base URL。'
              : requireRealProvider
                ? '需要先填写 OpenAI-compatible 的 API URL、API Key 和模型名，并通过连通测试后才能导入聊天记录。'
              : 'Mock 只用于跑通界面和流式链路，回复质量不代表真实模型。配置 OpenAI-compatible provider 后再测试真实效果。'}
          </p>
        </div>

        <div className="provider-setup-guide" aria-label="真实 Provider 配置步骤">
          <div className={`provider-step ${isMock ? 'pending' : 'ready'}`}>
            <span>1</span>
            <strong>选择真实模型</strong>
            <p>{isMock ? '当前仍在 mock 演示模式。' : '已切换到 OpenAI-compatible。'}</p>
          </div>
          <div className={`provider-step ${!isMock && hasBaseUrl && hasApiKey ? 'ready' : 'pending'}`}>
            <span>2</span>
            <strong>填写连接信息</strong>
            <p>{apiKeyInvalid ? '已保存的 API Key 无法解密，需要重新填写。' : hasStoredApiKey ? '已保存 API Key，可留空保留。' : 'Base URL 和 API Key 都需要填写。'}</p>
          </div>
          <div className={`provider-step ${!isMock && hasModel ? 'ready' : 'pending'}`}>
            <span>3</span>
            <strong>确认模型</strong>
            <p>{providerModels.length > 1 ? `已检测到 ${providerModels.length} 个模型。` : '可手动填写或点击检测模型。'}</p>
          </div>
          <div className={`provider-step ${readyForNetworkTest ? 'ready' : 'pending'}`}>
            <span>4</span>
            <strong>测试连通</strong>
            <p>{nextAction}</p>
          </div>
        </div>

        <div className={`provider-feedback ${providerFeedback.kind}`}>
          <strong>配置状态</strong>
          <p>{providerFeedback.message}</p>
        </div>

        <div className="form-grid">
          <label>
            Provider ID
            <input value={provider.id} onChange={(event) => onProviderChange({ ...provider, id: event.target.value })} />
          </label>
          <label>
            类型
            <select
              value={provider.type}
              onChange={(event) => {
                const nextType = event.target.value;
                const nextDefaultModel =
                  nextType === 'mock' ? 'mock-chat' : provider.default_model === 'mock-chat' ? 'gpt-4o-mini' : provider.default_model;
                const nextId = nextType === 'mock' ? 'local-mock' : provider.id === 'local-mock' ? 'openai-compatible' : provider.id;
                onProviderChange({ ...provider, id: nextId, type: nextType, default_model: nextDefaultModel });
              }}
            >
              {requireRealProvider ? null : <option value="mock">mock</option>}
              <option value="openai_compatible">openai_compatible</option>
            </select>
          </label>
          <label>
            API URL
            <input
              placeholder="https://api.openai.com/v1"
              value={provider.base_url || ''}
              onChange={(event) => onProviderChange({ ...provider, base_url: event.target.value })}
            />
          </label>
          <label>
            Model
            <select value={provider.default_model} onChange={(event) => onProviderChange({ ...provider, default_model: event.target.value })}>
              {modelOptions.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </label>
          <label className="wide">
            API Key
            <input
              type="password"
              placeholder={apiKeyInvalid ? '本机密钥失效，请重新填写 API Key' : hasStoredApiKey ? '已保存，可留空保留原 key' : 'OpenAI-compatible 需要填写 API Key'}
              value={provider.api_key === '***' ? '' : provider.api_key || ''}
              onChange={(event) => onProviderChange({ ...provider, api_key: event.target.value })}
            />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={onSaveProvider}>
            保存 Provider
          </button>
          <button type="button" className="secondary" onClick={onListModels}>
            检测模型
          </button>
          <button type="button" className="secondary" onClick={onTestProvider}>
            测试连通
          </button>
        </div>
      </div>

      {hideDiagnostics ? null : <div className="settings-card">
        <div className="section-heading">
          <h2>SSE Demo</h2>
          <span>诊断流式链路</span>
        </div>
        <div className="stream-box">{streamText || '点击按钮后显示流式 token'}</div>
        <button type="button" onClick={onDemoSse}>
          读取流式响应
        </button>
      </div>}
    </section>
  );
}
