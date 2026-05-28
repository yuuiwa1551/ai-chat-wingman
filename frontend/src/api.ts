export interface LlmProviderConfig {
  id: string;
  type: string;
  base_url?: string | null;
  api_key?: string | null;
  default_model: string;
  enabled: boolean;
}

export function getApiBaseUrl(): string {
  const fromQuery = new URLSearchParams(window.location.search).get('apiBase');
  return fromQuery || import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
}

const apiBaseUrl = getApiBaseUrl();

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || `Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export async function listProviders(): Promise<LlmProviderConfig[]> {
  const body = await requestJson<{ providers: LlmProviderConfig[] }>('/settings/llm/providers');
  return body.providers;
}

export async function saveProvider(provider: LlmProviderConfig): Promise<LlmProviderConfig> {
  const body = await requestJson<{ provider: LlmProviderConfig }>(`/settings/llm/providers/${provider.id}`, {
    method: 'PUT',
    body: JSON.stringify(provider),
  });
  return body.provider;
}

export async function testProvider(providerId: string): Promise<{ ok: boolean; text: string; llm_call_id: number }> {
  return requestJson(`/settings/llm/providers/${providerId}/test`, { method: 'POST' });
}

export async function readDemoSse(onToken: (token: string) => void): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/demo/sse`);
  if (!response.ok || !response.body) {
    throw new Error(`SSE request failed: ${response.status}`);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let finalText = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const eventText of events) {
      const eventName = eventText.match(/^event: (.+)$/m)?.[1];
      const dataLine = eventText.match(/^data: (.+)$/m)?.[1];
      if (!eventName || !dataLine) {
        continue;
      }
      const data = JSON.parse(dataLine) as { delta?: string; text?: string };
      if (eventName === 'token' && data.delta) {
        onToken(data.delta);
      }
      if (eventName === 'done' && data.text) {
        finalText = data.text;
      }
    }
  }

  return finalText;
}

export { apiBaseUrl };
