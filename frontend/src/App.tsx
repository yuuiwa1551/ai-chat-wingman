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
import type { ProviderFeedback } from './components/ProviderSettingsPanel';

const defaultProvider: LlmProviderConfig = {
  id: 'openai-compatible',
  type: 'openai_compatible',
  base_url: '',
  api_key: '',
  default_model: 'gpt-4o-mini',
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
  const [providerFeedback, setProviderFeedback] = useState<ProviderFeedback>({
    kind: 'warning',
    message: '当前可以先用 Mock 跑通流程；配置 OpenAI-compatible provider 后再验证真实回复质量。',
  });
  const [streamText, setStreamText] = useState('');
  const [bootFinished, setBootFinished] = useState(false);
  const [bootError, setBootError] = useState<string | null>(null);
  const [providerConnectivityOk, setProviderConnectivityOk] = useState(false);
  const [alwaysOnTop, setAlwaysOnTop] = useState(false);

  useEffect(() => {
    void loadAppState();
  }, []);

  async function loadAppState() {
    setBootError(null);
    setBootFinished(false);
    setStatus('正在连接本地服务...');
    try {
      const [providersResult, onboardingResult, presetsResult, targetsResult] = await Promise.allSettled([
        listProviders(),
        getOnboardingStatus(),
        getStylePresets(),
        listTargets(),
      ]);
      if (providersResult.status === 'rejected') {
        // Providers are required to render the core workspace; fail the boot.
        throw providersResult.reason;
      }
      if (onboardingResult.status === 'rejected') {
        // Onboarding decides whether to show the wizard or workspace; it cannot degrade safely.
        throw onboardingResult.reason;
      }
      const items = providersResult.value;
      setProviders(items);
      setOnboardingStatus(onboardingResult.value);
      if (presetsResult.status === 'fulfilled') {
        setStylePresets(presetsResult.value);
      }
      if (targetsResult.status === 'fulfilled') {
        setTargets(targetsResult.value);
      }
      const degraded = [onboardingResult, presetsResult, targetsResult].some(
        (result) => result.status === 'rejected',
      );
      const realProviders = items.filter((item) => item.type !== 'mock');
      const preferredProvider = realProviders[0] || items[0];
      if (preferredProvider) {
        setProvider({ ...defaultProvider, ...preferredProvider, api_key: '' });
        setProviderModels([preferredProvider.default_model || defaultProvider.default_model]);
      }
      const realProviderCount = realProviders.length;
      const hasInvalidApiKey = items.some((item) => item.api_key_status === 'invalid');
      setProviderFeedback(
        hasInvalidApiKey
          ? { kind: 'warning', message: '有 Provider 的 API Key 无法解密，请重新填写并保存。' }
          : realProviderCount
          ? { kind: 'success', message: `已加载 ${realProviderCount} 个真实 Provider，可以直接测试连通。` }
          : { kind: 'warning', message: '当前没有真实 Provider；Mock 只用于演示流程和本地链路。' },
      );
      setStatus(degraded ? '已连接本地服务（部分数据加载失败，可稍后重试）' : '已连接本地服务');
      setProviderConnectivityOk(false);
    } catch (error) {
      const message = readableError(error, '初始化失败');
      setStatus(message);
      setBootError(message);
      setProviderFeedback({ kind: 'error', message });
    } finally {
      setBootFinished(true);
    }
  }

  function upsertTarget(target: ChatTarget) {
    setTargets((current) => {
      const exists = current.some((item) => item.id === target.id);
      return exists ? current.map((item) => (item.id === target.id ? target : item)) : [target, ...current];
    });
  }

  const activeStoredProvider = providers.find((item) => item.id === provider.id);
  const hasStoredApiKey = Boolean(activeStoredProvider?.api_key);

  function mergeSavedProvider(saved: LlmProviderConfig) {
    setProviders((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
    setProvider({ ...provider, ...saved, api_key: '' });
    setProviderModels((current) => Array.from(new Set([saved.default_model, ...current].filter(Boolean))));
    setProviderConnectivityOk(false);
  }

  function validateProviderForNetwork(): string | null {
    if (provider.type === 'mock') {
      return 'Mock provider 不需要连通真实模型；请先切换到 openai_compatible。';
    }
    if (!provider.base_url?.trim()) {
      return '缺少 Base URL，例如 https://api.openai.com/v1。';
    }
    if (!provider.api_key?.trim() && !hasStoredApiKey) {
      return '缺少 API Key；它只会保存在本地设置中，不会写进仓库。';
    }
    if (!provider.default_model.trim()) {
      return '缺少模型名；可以先填写常用模型名，或保存后点击检测模型。';
    }
    return null;
  }

  async function handleSaveProvider() {
    setStatus('正在保存 provider...');
    setProviderFeedback({ kind: 'info', message: '正在保存 Provider 配置...' });
    try {
      const saved = await saveProvider(provider);
      mergeSavedProvider(saved);
      const isMock = saved.type === 'mock';
      const message = isMock
        ? `已保存 ${saved.id}，当前仍是 Mock 演示模式。`
        : `已保存 ${saved.id}，下一步建议检测模型或测试连通。`;
      setStatus(message);
      setProviderFeedback({ kind: isMock ? 'warning' : 'success', message });
    } catch (error) {
      const message = readableError(error, '保存 Provider 失败');
      setStatus(message);
      setProviderFeedback({ kind: 'error', message });
    }
  }

  async function handleListModels() {
    if (!provider.id.trim()) {
      setStatus('先填写 Provider ID');
      setProviderFeedback({ kind: 'warning', message: '先填写 Provider ID，再保存或检测模型。' });
      return;
    }
    const validationError = validateProviderForNetwork();
    if (validationError) {
      setStatus(validationError);
      setProviderFeedback({ kind: 'warning', message: validationError });
      return;
    }
    setStatus('正在保存配置并检测模型...');
    setProviderFeedback({ kind: 'info', message: '正在保存配置并从 provider 拉取模型列表...' });
    try {
      const saved = await saveProvider(provider);
      mergeSavedProvider(saved);
      const result = await listProviderModels(saved.id);
      const models = result.models.length ? result.models : [saved.default_model];
      setProviderModels(models);
      const nextModel = models.includes(saved.default_model) ? saved.default_model : models[0];
      setProvider({ ...saved, api_key: '', default_model: nextModel });
      const message = `检测到 ${models.length} 个模型，已选择 ${nextModel}。`;
      setStatus(message);
      setProviderFeedback({ kind: 'success', message });
    } catch (error) {
      const message = readableError(error, '检测模型失败');
      setStatus(message);
      setProviderFeedback({ kind: 'error', message: `${message} 请检查 Base URL、API Key 或服务端模型列表接口。` });
    }
  }

  async function handleTestProvider() {
    const validationError = validateProviderForNetwork();
    if (validationError) {
      setStatus(validationError);
      setProviderFeedback({ kind: 'warning', message: validationError });
      return;
    }
    setStatus('正在测试 provider...');
    setProviderFeedback({ kind: 'info', message: '正在保存配置并发送一条 ping 测试...' });
    try {
      const saved = await saveProvider(provider);
      mergeSavedProvider(saved);
      const result = await testProvider(saved.id);
      const message = `测试通过：${compactProviderTestText(result.text)} (#${result.llm_call_id})`;
      setStatus(message);
      setProviderFeedback({ kind: 'success', message });
      setProviderConnectivityOk(true);
    } catch (error) {
      const message = readableError(error, '测试失败');
      setStatus(message);
      setProviderFeedback({ kind: 'error', message: `${message} 请检查网络、鉴权和模型名是否匹配。` });
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

  async function handleToggleAlwaysOnTop() {
    const nextValue = !alwaysOnTop;
    const api = desktopApi();
    if (!api?.set_on_top) {
      setStatus('当前浏览器预览不支持窗口置顶，桌面壳中可用。');
      return;
    }
    try {
      const result = await api.set_on_top(nextValue);
      setAlwaysOnTop(Boolean(result?.on_top ?? nextValue));
      setStatus(nextValue ? '窗口已钉在最前面' : '已取消窗口置顶');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '切换窗口置顶失败');
    }
  }

  async function handleMinimizeWindow() {
    const api = desktopApi();
    if (!api?.minimize) {
      setStatus('当前浏览器预览不支持最小化，桌面壳中可用。');
      return;
    }
    try {
      await api.minimize();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '最小化窗口失败');
    }
  }

  const realProviderCount = providers.filter((item) => item.type !== 'mock').length;

  const providerSettings = (
    <ProviderSettingsPanel
      provider={provider}
      providersCount={realProviderCount}
      providerModels={providerModels}
      providerFeedback={providerFeedback}
      hasStoredApiKey={hasStoredApiKey}
      streamText={streamText}
      requireRealProvider={onboardingStatus ? !onboardingStatus.has_default_profile : false}
      hideDiagnostics={onboardingStatus ? !onboardingStatus.has_default_profile : false}
      onProviderChange={(nextProvider) => {
        setProvider(nextProvider);
        setProviderConnectivityOk(false);
        if (nextProvider.type === 'mock') {
          setProviderModels(['mock-chat', 'mock-vision']);
          setProviderFeedback({ kind: 'warning', message: '已切换到 Mock；它只验证本地流程，不代表真实回复质量。' });
        } else {
          setProviderFeedback({ kind: 'info', message: '已切换到 OpenAI-compatible；请补齐 Base URL、API Key 和模型名。' });
        }
      }}
      onSaveProvider={() => void handleSaveProvider()}
      onListModels={() => void handleListModels()}
      onTestProvider={() => void handleTestProvider()}
      onDemoSse={() => void handleDemoSse()}
    />
  );

  if (!bootFinished || bootError || !onboardingStatus) {
    return (
      <main className="window-shell boot-shell">
        <section className="boot-panel">
          <h1>AI Chat Wingman</h1>
          <p>{bootError ? '没有连上本地后端服务。' : '正在连接本地后端服务...'}</p>
          {bootError ? <pre>{bootError}</pre> : null}
          <button type="button" onClick={() => void loadAppState()}>
            重新连接
          </button>
        </section>
      </main>
    );
  }

  if (!onboardingStatus.has_default_profile) {
    return (
      <OnboardingWizard
        presets={stylePresets}
        targets={targets}
        providerSettings={providerSettings}
        providerReady={providerConnectivityOk}
        providerStatus={providerFeedback.message}
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
      providerCount={realProviderCount}
      status={status}
      providerSettings={providerSettings}
      onTargetsChange={setTargets}
      onTargetImported={upsertTarget}
      alwaysOnTop={alwaysOnTop}
      onToggleAlwaysOnTop={() => void handleToggleAlwaysOnTop()}
      onMinimizeWindow={() => void handleMinimizeWindow()}
    />
  );
}

interface DesktopApi {
  set_on_top?: (enabled: boolean) => Promise<{ on_top: boolean }>;
  minimize?: () => Promise<{ minimized: boolean }>;
}

function desktopApi(): DesktopApi | null {
  return (window as Window & { pywebview?: { api?: DesktopApi } }).pywebview?.api || null;
}

function readableError(error: unknown, fallback: string): string {
  if (!(error instanceof Error)) {
    return fallback;
  }
  const rawMessage = error.message || fallback;
  try {
    const parsed = JSON.parse(rawMessage) as { detail?: string };
    return parsed.detail || rawMessage;
  } catch {
    return rawMessage;
  }
}

function compactProviderTestText(text: string): string {
  const compact = text.replace(/\s+/g, ' ').trim() || 'OK';
  return compact.length > 80 ? `${compact.slice(0, 80)}...` : compact;
}
