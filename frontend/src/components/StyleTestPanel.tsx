import { useState } from 'react';
import {
  analyzeStyleTestSession,
  createStyleTestSession,
  sendStyleTestMessage,
  StyleTestAnalysis,
  StyleTestMessage,
  StyleTestSession,
  UserProfile,
} from '../api';

const targetTypes = ['朋友', '暧昧对象', '同事', '伴侣', '家人'];

interface StyleTestPanelProps {
  onProfileSaved?: (profile: UserProfile) => void;
}

export function StyleTestPanel({ onProfileSaved }: StyleTestPanelProps = {}) {
  const [targetType, setTargetType] = useState(targetTypes[0]);
  const [scenario, setScenario] = useState('对方今天很累，回复欲望不高。');
  const [targetProfile, setTargetProfile] = useState('情绪比较慢热，压力大时不喜欢被连续追问。');
  const [session, setSession] = useState<StyleTestSession | null>(null);
  const [messages, setMessages] = useState<StyleTestMessage[]>([]);
  const [draft, setDraft] = useState('那你先歇会儿，不急着回我。');
  const [streamingReply, setStreamingReply] = useState('');
  const [analysis, setAnalysis] = useState<StyleTestAnalysis | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [status, setStatus] = useState('等待开始风格测试');
  const [sending, setSending] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);

  const userTurnCount = messages.filter((message) => message.role === 'user').length;

  async function ensureSession(): Promise<StyleTestSession> {
    if (session) {
      return session;
    }
    const nextSession = await createStyleTestSession({
      target_type: targetType,
      scenario,
      simulated_target_profile: targetProfile || null,
    });
    setSession(nextSession);
    setMessages([]);
    setAnalysis(null);
    setProfile(null);
    setStatus(`已创建测试会话 #${nextSession.id}`);
    return nextSession;
  }

  async function handleStart() {
    try {
      await ensureSession();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '创建测试会话失败');
    }
  }

  async function handleSend() {
    if (!draft.trim()) {
      setStatus('先输入一句自己的回复');
      return;
    }

    setSending(true);
    setStreamingReply('');
    setAnalysis(null);
    try {
      const activeSession = await ensureSession();
      const result = await sendStyleTestMessage(activeSession.id, draft, {
        onUserMessage(message) {
          setMessages((current) => [...current, message]);
        },
        onToken(delta) {
          setStreamingReply((current) => current + delta);
        },
      });
      setMessages((current) => [
        ...current,
        {
          id: result.message_id,
          session_id: activeSession.id,
          role: 'simulated_target',
          content: result.text,
          created_at: new Date().toISOString(),
        },
      ]);
      setStreamingReply('');
      setDraft('');
      setStatus(`已完成第 ${userTurnCount + 1} 轮`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '发送失败');
    } finally {
      setSending(false);
    }
  }

  async function handleAnalyze() {
    if (!session) {
      setStatus('先开始一次风格测试');
      return;
    }
    setAnalyzing(true);
    try {
      const result = await analyzeStyleTestSession(session.id);
      setAnalysis(result.analysis);
      setProfile(result.profile);
      onProfileSaved?.(result.profile);
      setStatus(`已保存风格档案，LLM Call #${result.llm_call_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '分析失败');
    } finally {
      setAnalyzing(false);
    }
  }

  return (
    <section className="panel style-test-panel">
      <div className="section-heading">
        <h2>风格测试聊天</h2>
        <span>{session ? `Session #${session.id} · ${userTurnCount}/10` : 'Phase 2 Style Test'}</span>
      </div>

      <div className="form-grid">
        <label>
          模拟对象
          <select value={targetType} disabled={Boolean(session)} onChange={(event) => setTargetType(event.target.value)}>
            {targetTypes.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          场景
          <input value={scenario} disabled={Boolean(session)} onChange={(event) => setScenario(event.target.value)} />
        </label>
        <label className="wide">
          对象设定
          <input value={targetProfile} disabled={Boolean(session)} onChange={(event) => setTargetProfile(event.target.value)} />
        </label>
      </div>

      <div className="actions">
        <button type="button" className="secondary" disabled={Boolean(session)} onClick={() => void handleStart()}>
          开始测试
        </button>
        <button type="button" disabled={!session || analyzing || userTurnCount === 0} onClick={() => void handleAnalyze()}>
          {analyzing ? '分析中...' : '分析并保存人设'}
        </button>
      </div>

      <div className="chat-transcript">
        {messages.length === 0 && !streamingReply ? <div className="empty-state">测试消息会显示在这里</div> : null}
        {messages.map((message) => (
          <div className={`chat-message ${message.role === 'user' ? 'user' : 'target'}`} key={message.id}>
            <span>{message.role === 'user' ? '我' : '模拟对象'}</span>
            <p>{message.content}</p>
          </div>
        ))}
        {streamingReply ? (
          <div className="chat-message target streaming">
            <span>模拟对象</span>
            <p>{streamingReply}</p>
          </div>
        ) : null}
      </div>

      <div className="chat-compose">
        <textarea value={draft} onChange={(event) => setDraft(event.target.value)} />
        <button type="button" disabled={sending} onClick={() => void handleSend()}>
          {sending ? '发送中...' : '发送并等待回复'}
        </button>
      </div>

      {analysis ? (
        <div className="analysis-box">
          <strong>{profile ? `${profile.name} v${profile.current_version}` : '风格分析'}</strong>
          <p>{analysis.style_summary}</p>
          <small>{analysis.generation_guideline}</small>
        </div>
      ) : null}

      <p className="reply-status">{status}</p>
    </section>
  );
}
