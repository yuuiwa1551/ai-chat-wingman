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
  target_name: string | null;
  input_text: string;
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

export type MemoryStatus = 'pending' | 'approved' | 'rejected';

export interface Memory {
  id: number;
  target_id: number | null;
  memory_type: string | null;
  content: string;
  confidence: number;
  status: MemoryStatus;
  source_conversation_id: number | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryPayload {
  content: string;
  memory_type?: string | null;
  confidence?: number;
}

export type ParsedSpeaker = 'me' | 'target' | 'unknown';

export interface ParsedChatMessage {
  speaker: ParsedSpeaker;
  content: string;
  time: string;
}

export interface ChatScreenshotParseResult {
  messages: ParsedChatMessage[];
  summary: string;
  uncertain_parts: string[];
  stored_image_path: string;
  llm_call_id: number;
  prompt_version: string;
}

export interface JobRecord {
  id: number;
  job_type: string;
  status: 'pending' | 'running' | 'success' | 'failed' | 'cancelled';
  progress: number;
  payload: string | null;
  result: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface ImportedMessagePreview {
  role: 'me' | 'target' | 'unknown';
  speaker: string;
  content: string;
  timestamp: string | null;
}

export interface QQImportResult {
  import_id: number;
  raw_path: string;
  message_count: number;
  user_message_count: number;
  target_message_count: number;
  speaker_counts: Record<string, number>;
  messages_preview: ImportedMessagePreview[];
  profile: UserProfile;
  target: ChatTarget;
  analysis: {
    user: StyleTestAnalysis;
    target: {
      relationship: string;
      style_summary: string;
      preferences: string;
      taboos: string;
      strategy_guideline: string;
    };
  };
}

export interface QQJsonImportPayload {
  filename?: string | null;
  raw_json: unknown;
  me_speakers: string[];
  target_id?: number | null;
  target_name?: string | null;
}

export interface SavedReply {
  id: number;
  conversation_id: number;
  target_id: number | null;
  candidate_index: number | null;
  text: string;
  note: string | null;
  created_at: string;
}

export interface DataSummary {
  data_path: string;
  db_path: string;
  screenshots_path: string;
  imports_path: string;
  logs_path: string;
  backups_path: string;
  total_size_bytes: number;
  section_sizes: Record<string, number>;
  table_counts: Record<string, number>;
}

export interface BackupExportResult {
  backup_path: string;
  backup_size_bytes: number;
  included_file_count: number;
  data_path: string;
  created_at: string;
}

export interface ProviderModelsResult {
  provider_id: string;
  models: string[];
  default_model: string | null;
}

interface SseHandlers {
  onEvent: (eventName: string, data: unknown) => void;
}

export function getApiBaseUrl(): string {
  const fromQuery = new URLSearchParams(window.location.search).get('apiBase');
  return fromQuery || import.meta.env.VITE_API_BASE_URL || window.location.origin || 'http://127.0.0.1:8000';
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

export async function listProviderModels(providerId: string): Promise<ProviderModelsResult> {
  return requestJson(`/settings/llm/providers/${providerId}/models`);
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

export async function favoriteReply(
  conversationId: number,
  payload: { candidate_index?: number | null; selected_reply?: string | null; note?: string | null },
): Promise<SavedReply> {
  const body = await requestJson<{ saved_reply: SavedReply }>(`/history/conversations/${conversationId}/favorite`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return body.saved_reply;
}

export async function listConversations(params: { query?: string; target_id?: number | null; limit?: number } = {}): Promise<ConversationRecord[]> {
  const body = await requestJson<{ conversations: ConversationRecord[] }>(`/history/conversations${queryString(params)}`);
  return body.conversations;
}

export async function listSavedReplies(params: { query?: string; target_id?: number | null; limit?: number } = {}): Promise<SavedReply[]> {
  const body = await requestJson<{ saved_replies: SavedReply[] }>(`/history/favorites${queryString(params)}`);
  return body.saved_replies;
}

export async function deleteSavedReply(savedReplyId: number): Promise<void> {
  await requestJson<{ ok: boolean }>(`/history/favorites/${savedReplyId}`, { method: 'DELETE' });
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

export async function analyzeStyleTestSession(
  sessionId: number,
  options: PollJobOptions = {},
): Promise<{
  analysis: StyleTestAnalysis;
  profile: UserProfile;
  llm_call_id: number;
}> {
  const started = await requestJson<{ job_id: number; status: string }>(
    `/style-test/sessions/${sessionId}/analysis`,
    { method: 'POST' },
  );
  return pollJobResult<{ analysis: StyleTestAnalysis; profile: UserProfile; llm_call_id: number }>(
    started.job_id,
    options,
  );
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

export async function organizeTarget(
  targetId: number,
  notes: string,
  options: PollJobOptions = {},
): Promise<{ target: ChatTarget; llm_call_id: number }> {
  const started = await requestJson<{ job_id: number; status: string }>(`/targets/${targetId}/organize`, {
    method: 'POST',
    body: JSON.stringify({ notes }),
  });
  return pollJobResult<{ target: ChatTarget; llm_call_id: number }>(started.job_id, options);
}

export async function listMemories(targetId: number, status?: MemoryStatus): Promise<Memory[]> {
  const query = status ? `?status=${status}` : '';
  const body = await requestJson<{ memories: Memory[] }>(`/targets/${targetId}/memories${query}`);
  return body.memories;
}

export async function createMemory(targetId: number, payload: MemoryPayload): Promise<Memory> {
  const body = await requestJson<{ memory: Memory }>(`/targets/${targetId}/memories`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  return body.memory;
}

export async function updateMemory(memoryId: number, payload: Partial<MemoryPayload> & { status?: MemoryStatus }): Promise<Memory> {
  const body = await requestJson<{ memory: Memory }>(`/memories/${memoryId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
  return body.memory;
}

export async function deleteMemory(memoryId: number): Promise<void> {
  await requestJson<{ ok: boolean }>(`/memories/${memoryId}`, { method: 'DELETE' });
}

export async function approveMemory(memoryId: number): Promise<Memory> {
  const body = await requestJson<{ memory: Memory }>(`/memories/${memoryId}/approve`, { method: 'POST' });
  return body.memory;
}

export async function rejectMemory(memoryId: number): Promise<Memory> {
  const body = await requestJson<{ memory: Memory }>(`/memories/${memoryId}/reject`, { method: 'POST' });
  return body.memory;
}

export async function parseChatScreenshot(
  file: File,
  options: PollJobOptions = {},
): Promise<ChatScreenshotParseResult> {
  const imageData = await fileToDataUrl(file);
  const started = await requestJson<{ job_id: number; status: string }>('/multimodal/parse-chat-screenshot', {
    method: 'POST',
    body: JSON.stringify({
      filename: file.name,
      mime_type: file.type || 'image/png',
      image_base64: imageData,
    }),
  });
  return pollJobResult<ChatScreenshotParseResult>(started.job_id, options);
}

export async function startQQJsonImport(payload: QQJsonImportPayload): Promise<{ job_id: number; status: string }> {
  return requestJson('/import/qq-json', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function getJob(jobId: number): Promise<JobRecord> {
  return requestJson(`/jobs/${jobId}`);
}

export interface PollJobOptions {
  intervalMs?: number;
  maxAttempts?: number;
  shouldCancel?: () => boolean;
  onProgress?: (job: JobRecord) => void;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export async function pollJobResult<T>(jobId: number, options: PollJobOptions = {}): Promise<T> {
  const { intervalMs = 500, maxAttempts = 80, shouldCancel, onProgress } = options;
  for (let attempt = 0; attempt < maxAttempts; attempt += 1) {
    if (shouldCancel?.()) {
      throw new Error('任务已取消');
    }
    const job = await getJob(jobId);
    if (shouldCancel?.()) {
      throw new Error('任务已取消');
    }
    onProgress?.(job);
    if (job.status === 'success') {
      if (!job.result) {
        throw new Error('任务完成但没有结果');
      }
      return JSON.parse(job.result) as T;
    }
    if (job.status === 'failed') {
      throw new Error(job.error_message || '任务失败');
    }
    if (job.status === 'cancelled') {
      throw new Error('任务已取消');
    }
    await delay(intervalMs);
  }
  throw new Error('任务超时');
}

export async function getDataSummary(): Promise<DataSummary> {
  return requestJson('/privacy/data-summary');
}

export async function startDataExport(): Promise<{ job_id: number; status: string }> {
  return requestJson('/privacy/export', { method: 'POST' });
}

export interface PurgeResult {
  deleted_rows: Record<string, number>;
  removed_files: number;
  include_settings: boolean;
}

export async function purgeAllData(confirmText: string, includeSettings = false): Promise<PurgeResult> {
  return requestJson('/privacy/purge', {
    method: 'POST',
    body: JSON.stringify({ confirm: true, confirm_text: confirmText, include_settings: includeSettings }),
  });
}

async function readSseResponse(response: Response, handlers: SseHandlers): Promise<void> {
  if (!response.body) {
    throw new Error('SSE response has no body');
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
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
  } finally {
    await reader.cancel().catch(() => undefined);
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

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ''));
    reader.onerror = () => reject(reader.error || new Error('读取图片失败'));
    reader.readAsDataURL(file);
  });
}

function queryString(params: Record<string, string | number | null | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== null && value !== undefined && value !== '') {
      search.set(key, String(value));
    }
  }
  const serialized = search.toString();
  return serialized ? `?${serialized}` : '';
}

export { apiBaseUrl };
