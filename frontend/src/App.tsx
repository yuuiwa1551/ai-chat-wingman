import { useEffect, useState } from 'react';
import {
  apiBaseUrl,
  getOnboardingStatus,
  getStylePresets,
  ChatTarget,
  LlmProviderConfig,
  listTargets,
  listProviderModels,
  listProviders,
  OnboardingStatus,
  readDemoSse,
  saveProvider,
  StylePreset,
  testProvider,
} from './api';
import { OnboardingWizard } from './components/OnboardingWizard';
import { MemoryReviewPanel } from './components/MemoryReviewPanel';
import { HistoryPanel } from './components/HistoryPanel';
import { DataPanel } from './components/DataPanel';
import { QQImportPanel } from './components/QQImportPanel';
import { ReplyGenerator } from './components/ReplyGenerator';
import { StyleTestPanel } from './components/StyleTestPanel';
import { TargetManager } from './components/TargetManager';

const defaultProvider: LlmProviderConfig = {
  id: 'local-mock',
  type: 'mock',
  base_url: '',
  api_key: '',
  default_model: 'mock-chat',
  enabled: true,
};

export function App() {
  const [provider, setProvider] = useState<LlmProviderConfig>(defaultProvider);
  const [providers, setProviders] = useState<LlmProviderConfig[]>([]);
  const [onboardingStatus, setOnboardingStatus] = useState<OnboardingStatus | null>(null);
  const [stylePresets, setStylePresets] = useState<StylePreset[]>([]);
  const [targets, setTargets] = useState<ChatTarget[]>([]);
  const [providerModels, setProviderModels] = useState<string[]>([defaultProvider.default_model]);
  const [status, setStatus] = useState('等待连接');
  const [streamText, setStreamText] = useState('');

  useEffect(() => {
    Promise.all([listProviders(), getOnboardingStatus(), getStylePresets(), listTargets()])
      .then(([items, nextOnboardingStatus, presets, nextTargets]) => {
        setProviders(items);
        setOnboardingStatus(nextOnboardingStatus);
        setStylePresets(presets);
        setTargets(nextTargets);
        if (items[0]) {
          setProvider({ ...defaultProvider, ...items[0], api_key: '' });
          setProviderModels([items[0].default_model || defaultProvider.default_model]);
        }
      })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  async function handleSaveProvider() {
    setStatus('正在保存 provider...');
    const saved = await saveProvider(provider);
    setProviders((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
    setProvider({ ...provider, ...saved, api_key: '' });
    setProviderModels((current) => Array.from(new Set([saved.default_model, ...current].filter(Boolean))));
    setStatus(`已保存 ${saved.id}`);
  }

  async function handleListModels() {
    if (!provider.id.trim()) {
      setStatus('先填写 Provider ID');
      return;
    }
    setStatus('正在保存配置并检测模型...');
    try {
      const saved = await saveProvider(provider);
      setProviders((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
      const result = await listProviderModels(saved.id);
      const models = result.models.length ? result.models : [saved.default_model];
      setProviderModels(models);
      const nextModel = models.includes(saved.default_model) ? saved.default_model : models[0];
      setProvider({ ...saved, api_key: '', default_model: nextModel });
      setStatus(`检测到 ${models.length} 个模型`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '检测模型失败');
    }
  }

  async function handleTestProvider() {
    setStatus('正在测试 provider...');
    const result = await testProvider(provider.id);
    setStatus(`测试通过：${result.text} (#${result.llm_call_id})`);
  }

  async function handleDemoSse() {
    setStreamText('');
    setStatus('正在读取 SSE...');
    const finalText = await readDemoSse((token) => setStreamText((current) => current + token));
    setStatus(`SSE 完成：${finalText}`);
  }

  return (
    <main className="window-shell">
      <header className="titlebar">
        <div>
          <p className="eyebrow">Phase 8 Data Backup</p>
          <h1>AI Chat Wingman</h1>
        </div>
        <span className="status-pill">{providers.length || 0} Providers</span>
      </header>

      {onboardingStatus && !onboardingStatus.has_default_profile ? (
        <OnboardingWizard
          presets={stylePresets}
          onComplete={(profile) => {
            setOnboardingStatus({ has_default_profile: true, default_profile_id: profile.id });
            setStatus(`已保存默认人设：${profile.name}`);
          }}
        />
      ) : null}

      {onboardingStatus?.has_default_profile ? <TargetManager targets={targets} onTargetsChange={setTargets} /> : null}

      {onboardingStatus?.has_default_profile ? (
        <QQImportPanel
          targets={targets}
          onTargetImported={(target) => {
            setTargets((current) => {
              const exists = current.some((item) => item.id === target.id);
              return exists ? current.map((item) => (item.id === target.id ? target : item)) : [target, ...current];
            });
          }}
        />
      ) : null}

      {onboardingStatus?.has_default_profile ? <MemoryReviewPanel targets={targets} /> : null}

      {onboardingStatus?.has_default_profile ? (
        <ReplyGenerator
          targets={targets}
          onTargetUsed={(targetId) => {
            setTargets((current) => {
              const used = current.find((target) => target.id === targetId);
              return used ? [used, ...current.filter((target) => target.id !== targetId)] : current;
            });
          }}
        />
      ) : null}

      {onboardingStatus?.has_default_profile ? <HistoryPanel targets={targets} /> : null}

      {onboardingStatus?.has_default_profile ? <DataPanel /> : null}

      {onboardingStatus?.has_default_profile ? <StyleTestPanel /> : null}

      <section className="panel">
        <div className="section-heading">
          <h2>Provider 设置</h2>
          <span>{apiBaseUrl}</span>
        </div>
        <div className="form-grid">
          <label>
            Provider ID
            <input value={provider.id} onChange={(event) => setProvider({ ...provider, id: event.target.value })} />
          </label>
          <label>
            类型
            <select
              value={provider.type}
              onChange={(event) => {
                const nextType = event.target.value;
                const nextDefaultModel = nextType === 'mock' ? 'mock-chat' : provider.default_model;
                setProvider({ ...provider, type: nextType, default_model: nextDefaultModel });
                if (nextType === 'mock') {
                  setProviderModels(['mock-chat', 'mock-vision']);
                }
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
              onChange={(event) => setProvider({ ...provider, base_url: event.target.value })}
            />
          </label>
          <label>
            Model
            <select
              value={provider.default_model}
              onChange={(event) => setProvider({ ...provider, default_model: event.target.value })}
            >
              {Array.from(new Set([provider.default_model, ...providerModels].filter(Boolean))).map((model) => (
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
              onChange={(event) => setProvider({ ...provider, api_key: event.target.value })}
            />
          </label>
        </div>
        <div className="actions">
          <button type="button" onClick={() => void handleSaveProvider()}>
            保存 Provider
          </button>
          <button type="button" className="secondary" onClick={() => void handleListModels()}>
            检测模型
          </button>
          <button type="button" className="secondary" onClick={() => void handleTestProvider()}>
            测试连通
          </button>
        </div>
      </section>

      <section className="panel">
        <div className="section-heading">
          <h2>SSE Demo</h2>
          <span>验证流式链路</span>
        </div>
        <div className="stream-box">{streamText || '点击按钮后显示流式 token'}</div>
        <button type="button" onClick={() => void handleDemoSse()}>
          读取流式响应
        </button>
      </section>

      <footer className="status-line">{status}</footer>
    </main>
  );
}
