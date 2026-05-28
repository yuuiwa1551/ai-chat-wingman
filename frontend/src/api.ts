export interface LlmProviderConfig {
  id: string;
  type: string;
  base_url?: string | null;
  api_key?: string | null;
  default_model: string;
  enabled: boolean;
}

export interface StylePreset {
  id: number;
  name: string;
  description: string;
  example_reply: string;
  config_json: string;
  created_at: string;
}

export interface OnboardingStatus {
  has_default_profile: boolean;
  default_profile_id: number | null;
}

export interface UserProfile {
  id: number;
  name: string;
  source_type: string;
  style_summary: string;
  generation_guideline: string;
  is_default: boolean;
  current_version: number;
}

export interface ReplyGeneratePayload {
  chat_text: string;
  target_id?: number | null;
  target_name?: string | null;
  target_strategy?: string | null;
  reply_goal: string;
  tone: string;
  length: string;
  proactivity: number;
  risk_level: string;
  candidate_count: number;
}

export interface ReplyCandidate {
  index: number;
  text: string;
}

export interface ReplyGenerateDone {
  conversation_id: number;
  llm_call_id: number;
  prompt_version: string;
  replies: string[];
}

export interface ConversationRecord {
  id: number;
  chat_session_id: number;
  target_id: number | null;
  prompt_version: string;
  llm_call_id: number | null;
  generated_replies: string | null;
  selected_reply: string | null;
}

export interface StyleTestSession {
  id: number;
  target_type: string;
  scenario: string;
  simulated_target_profile: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface StyleTestMessage {
  id: number;
  session_id: number;
  role: 'user' | 'simulated_target';
  content: string;
  created_at: string;
}

export interface StyleTestAnalysis {
  style_summary: string;
  tone_features: Record<string, number | string>;
  common_patterns: string[];
  avoid_patterns: string[];
  generation_guideline: string;
}

export interface ChatTarget {
  id: number;
  name: string;
  relationship: string | null;
  style_summary: string | null;
  preferences: string | null;
  taboos: string | null;
  strategy_guideline: string | null;
  created_at: string;
  updated_at: string;
}

export interface ChatTargetPayload {
  name: string;
  relationship?: string | null;
  style_summary?: string | null;
  preferences?: string | null;
  taboos?: string | null;
  strategy_guideline?: string | null;
}

interface SseHandlers {
  onEvent: (eventName: string, data: unknown) => void;
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

export async function getOnboardingStatus(): Promise<OnboardingStatus> {
  return requestJson('/onboarding/status');
}

export async function getStylePresets(): Promise<StylePreset[]> {
  const body = await requestJson<{ presets: StylePreset[] }>('/onboarding/style-presets');
  return body.presets;
}

export async function createDefaultProfile(payload: {
  name: string;
  selected_preset_ids: number[];
  avoid_patterns: string[];
}): Promise<UserProfile> {
  const body = await requestJson<{ profile: UserProfile }>('/onboarding/default-profile', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return body.profile;
}

export async function readDemoSse(onToken: (token: string) => void): Promise<string> {
  const response = await fetch(`${apiBaseUrl}/demo/sse`);
  if (!response.ok || !response.body) {
    throw new Error(`SSE request failed: ${response.status}`);
  }

  let finalText = '';
  await readSseResponse(response, {
    onEvent(eventName, data) {
      const payload = data as { delta?: string; text?: string };
      if (eventName === 'token' && payload.delta) {
        onToken(payload.delta);
      }
      if (eventName === 'done' && payload.text) {
        finalText = payload.text;
      }
    },
  });

  return finalText;
}

export async function generateReply(
  payload: ReplyGeneratePayload,
  handlers: {
    onConversation?: (conversationId: number, promptVersion: string) => void;
    onToken?: (candidate: ReplyCandidate) => void;
    onCandidate?: (candidate: ReplyCandidate) => void;
  } = {},
): Promise<ReplyGenerateDone> {
  const response = await fetch(`${apiBaseUrl}/reply/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(message || `Reply generation failed: ${response.status}`);
  }

  let done: ReplyGenerateDone | null = null;
  await readSseResponse(response, {
    onEvent(eventName, data) {
      if (eventName === 'conversation') {
        const event = data as { conversation_id: number; prompt_version: string };
        handlers.onConversation?.(event.conversation_id, event.prompt_version);
      }
      if (eventName === 'token') {
        const event = data as { index: number; delta: string };
        handlers.onToken?.({ index: event.index, text: event.delta });
      }
      if (eventName === 'candidate') {
        handlers.onCandidate?.(data as ReplyCandidate);
      }
      if (eventName === 'done') {
        done = data as ReplyGenerateDone;
      }
      if (eventName === 'error') {
        const event = data as { message?: string };
        throw new Error(event.message || 'Reply generation failed');
      }
    },
  });

  if (!done) {
    throw new Error('Reply generation ended without a done event');
  }
  return done;
}

export async function selectReply(conversationId: number, selectedIndex: number): Promise<ConversationRecord> {
  const body = await requestJson<{ conversation: ConversationRecord }>(`/reply/${conversationId}/select`, {
    method: 'POST',
    body: JSON.stringify({ selected_index: selectedIndex }),
  });
  return body.conversation;
}

export async function createStyleTestSession(payload: {
  target_type: string;
  scenario: string;
  simulated_target_profile?: string | null;
}): Promise<StyleTestSession> {
  const body = await requestJson<{ session: StyleTestSession }>('/style-test/sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return body.session;
}

export async function sendStyleTestMessage(
  sessionId: number,
  content: string,
  handlers: {
    onUserMessage?: (message: StyleTestMessage) => void;
    onToken?: (delta: string) => void;
  } = {},
): Promise<{ message_id: number; text: string }> {
  const response = await fetch(`${apiBaseUrl}/style-test/sessions/${sessionId}/message`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!response.ok || !response.body) {
    const message = await response.text();
    throw new Error(message || `Style test message failed: ${response.status}`);
  }

  let done: { message_id: number; text: string } | null = null;
  await readSseResponse(response, {
    onEvent(eventName, data) {
      if (eventName === 'user_message') {
        handlers.onUserMessage?.((data as { message: StyleTestMessage }).message);
      }
      if (eventName === 'token') {
        handlers.onToken?.((data as { delta: string }).delta);
      }
      if (eventName === 'done') {
        done = data as { message_id: number; text: string };
      }
      if (eventName === 'error') {
        throw new Error((data as { message?: string }).message || 'Style test message failed');
      }
    },
  });

  if (!done) {
    throw new Error('Style test message ended without a done event');
  }
  return done;
}

export async function analyzeStyleTestSession(sessionId: number): Promise<{
  analysis: StyleTestAnalysis;
  profile: UserProfile;
  llm_call_id: number;
}> {
  return requestJson(`/style-test/sessions/${sessionId}/analysis`, { method: 'POST' });
}

export async function listTargets(): Promise<ChatTarget[]> {
  const body = await requestJson<{ targets: ChatTarget[] }>('/targets');
  return body.targets;
}

export async function createTarget(payload: ChatTargetPayload): Promise<ChatTarget> {
  const body = await requestJson<{ target: ChatTarget }>('/targets', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return body.target;
}

export async function updateTarget(targetId: number, payload: Partial<ChatTargetPayload>): Promise<ChatTarget> {
  const body = await requestJson<{ target: ChatTarget }>(`/targets/${targetId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  return body.target;
}

export async function deleteTarget(targetId: number): Promise<void> {
  await requestJson<{ ok: boolean }>(`/targets/${targetId}`, { method: 'DELETE' });
}

export async function organizeTarget(targetId: number, notes: string): Promise<{ target: ChatTarget; llm_call_id: number }> {
  return requestJson(`/targets/${targetId}/organize`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
}

async function readSseResponse(response: Response, handlers: SseHandlers): Promise<void> {
  if (!response.body) {
    throw new Error('SSE response has no body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split('\n\n');
    buffer = events.pop() || '';
    for (const eventText of events) {
      handleSseEvent(eventText, handlers);
    }
  }
  if (buffer.trim()) {
    handleSseEvent(buffer, handlers);
  }
}

function handleSseEvent(eventText: string, handlers: SseHandlers): void {
  const eventName = eventText.match(/^event: (.+)$/m)?.[1];
  const dataLine = eventText.match(/^data: (.+)$/m)?.[1];
  if (!eventName || !dataLine) {
    return;
  }
  handlers.onEvent(eventName, JSON.parse(dataLine));
}

export { apiBaseUrl };
