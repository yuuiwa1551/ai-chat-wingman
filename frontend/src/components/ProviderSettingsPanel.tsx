import { apiBaseUrl, LlmProviderConfig } from '../api';

interface ProviderSettingsPanelProps {
  provider: LlmProviderConfig;
  providersCount: number;
  providerModels: string[];
  streamText: string;
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
  streamText,
  onProviderChange,
  onSaveProvider,
  onListModels,
  onTestProvider,
  onDemoSse,
}: ProviderSettingsPanelProps) {
  const modelOptions = Array.from(new Set([provider.default_model, ...providerModels].filter(Boolean)));

  return (
    <section className="settings-layout">
      <div className="settings-card">
        <div className="section-heading">
          <h2>Provider 设置</h2>
          <span>
            {providersCount} providers · {apiBaseUrl}
          </span>
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
                const nextDefaultModel = nextType === 'mock' ? 'mock-chat' : provider.default_model;
                onProviderChange({ ...provider, type: nextType, default_model: nextDefaultModel });
              }}
            >
              <option value="mock">mock</option>
              <option value="openai_compatible">openai_compatible</option>
            </select>
          </label>
          <label>
            Base URL
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
              placeholder="mock 类型可以留空"
              value={provider.api_key || ''}
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

      <div className="settings-card">
        <div className="section-heading">
          <h2>SSE Demo</h2>
          <span>诊断流式链路</span>
        </div>
        <div className="stream-box">{streamText || '点击按钮后显示流式 token'}</div>
        <button type="button" onClick={onDemoSse}>
          读取流式响应
        </button>
      </div>
    </section>
  );
}
