import { useEffect, useState } from 'react';
import {
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
import { FloatingWorkspace } from './components/FloatingWorkspace';
import { OnboardingWizard } from './components/OnboardingWizard';
import { ProviderSettingsPanel } from './components/ProviderSettingsPanel';

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

  function upsertTarget(target: ChatTarget) {
    setTargets((current) => {
      const exists = current.some((item) => item.id === target.id);
      return exists ? current.map((item) => (item.id === target.id ? target : item)) : [target, ...current];
    });
  }

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
    try {
      const result = await testProvider(provider.id);
      setStatus(`测试通过：${result.text} (#${result.llm_call_id})`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '测试失败');
    }
  }

  async function handleDemoSse() {
    setStreamText('');
    setStatus('正在读取 SSE...');
    try {
      const finalText = await readDemoSse((token) => setStreamText((current) => current + token));
      setStatus(`SSE 完成：${finalText}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'SSE 读取失败');
    }
  }

  const providerSettings = (
    <ProviderSettingsPanel
      provider={provider}
      providersCount={providers.length}
      providerModels={providerModels}
      streamText={streamText}
      onProviderChange={(nextProvider) => {
        setProvider(nextProvider);
        if (nextProvider.type === 'mock') {
          setProviderModels(['mock-chat', 'mock-vision']);
        }
      }}
      onSaveProvider={() => void handleSaveProvider()}
      onListModels={() => void handleListModels()}
      onTestProvider={() => void handleTestProvider()}
      onDemoSse={() => void handleDemoSse()}
    />
  );

  if (onboardingStatus && !onboardingStatus.has_default_profile) {
    return (
      <OnboardingWizard
        presets={stylePresets}
        targets={targets}
        onTargetImported={upsertTarget}
        onComplete={(profile) => {
          setOnboardingStatus({ has_default_profile: true, default_profile_id: profile.id });
          setStatus(`已保存默认人设：${profile.name}`);
        }}
      />
    );
  }

  return (
    <FloatingWorkspace
      targets={targets}
      providerCount={providers.length}
      status={status}
      providerSettings={providerSettings}
      onTargetsChange={setTargets}
      onTargetImported={upsertTarget}
    />
  );
}
