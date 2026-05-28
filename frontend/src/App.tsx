import { useEffect, useState } from 'react';
import { apiBaseUrl, LlmProviderConfig, listProviders, readDemoSse, saveProvider, testProvider } from './api';

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
  const [status, setStatus] = useState('等待连接');
  const [streamText, setStreamText] = useState('');

  useEffect(() => {
    listProviders()
      .then((items) => {
        setProviders(items);
        if (items[0]) {
          setProvider({ ...defaultProvider, ...items[0], api_key: '' });
        }
      })
      .catch((error: Error) => setStatus(error.message));
  }, []);

  async function handleSaveProvider() {
    setStatus('正在保存 provider...');
    const saved = await saveProvider(provider);
    setProviders((current) => [saved, ...current.filter((item) => item.id !== saved.id)]);
    setStatus(`已保存 ${saved.id}`);
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
          <p className="eyebrow">Phase 0 Foundation</p>
          <h1>AI Chat Wingman</h1>
        </div>
        <span className="status-pill">{providers.length || 0} Providers</span>
      </header>

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
            <select value={provider.type} onChange={(event) => setProvider({ ...provider, type: event.target.value })}>
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
            <input
              value={provider.default_model}
              onChange={(event) => setProvider({ ...provider, default_model: event.target.value })}
            />
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
