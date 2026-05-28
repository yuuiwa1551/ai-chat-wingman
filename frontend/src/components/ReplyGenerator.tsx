import { useState } from 'react';
import { ChatTarget, generateReply, ReplyCandidate, selectReply } from '../api';

const replyGoals = ['安慰并保留继续聊天空间', '自然接话', '推进邀约', '解释清楚', '结束话题但不生硬'];
const toneOptions = ['自然', '温柔', '轻松幽默', '冷静克制', '直接坦率'];
const lengthOptions = ['短', '中等', '稍微展开'];
const riskOptions = ['稳妥', '稍主动', '边界清楚'];

function upsertCandidate(items: ReplyCandidate[], index: number, text: string, mode: 'append' | 'replace'): ReplyCandidate[] {
  const nextItems = [...items];
  const existingIndex = nextItems.findIndex((item) => item.index === index);
  if (existingIndex >= 0) {
    const existing = nextItems[existingIndex];
    nextItems[existingIndex] = { index, text: mode === 'append' ? existing.text + text : text };
  } else {
    nextItems.push({ index, text });
  }
  return nextItems.sort((left, right) => left.index - right.index);
}

interface ReplyGeneratorProps {
  targets: ChatTarget[];
}

export function ReplyGenerator({ targets }: ReplyGeneratorProps) {
  const [chatText, setChatText] = useState('对方：今天真的累死了，不太想说话。');
  const [selectedTargetId, setSelectedTargetId] = useState<number | null>(null);
  const [targetName, setTargetName] = useState('');
  const [targetStrategy, setTargetStrategy] = useState('先接住情绪，不要追问太多。');
  const [replyGoal, setReplyGoal] = useState(replyGoals[0]);
  const [tone, setTone] = useState(toneOptions[0]);
  const [replyLength, setReplyLength] = useState(lengthOptions[0]);
  const [riskLevel, setRiskLevel] = useState(riskOptions[0]);
  const [proactivity, setProactivity] = useState(0.35);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [promptVersion, setPromptVersion] = useState('');
  const [candidates, setCandidates] = useState<ReplyCandidate[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [status, setStatus] = useState('等待输入聊天内容');
  const [generating, setGenerating] = useState(false);

  async function handleGenerate() {
    if (!chatText.trim()) {
      setStatus('先粘贴一段聊天内容');
      return;
    }

    setGenerating(true);
    setCandidates([]);
    setConversationId(null);
    setSelectedIndex(null);
    setStatus('正在生成候选回复...');
    try {
      const result = await generateReply(
        {
          chat_text: chatText,
          target_id: selectedTargetId,
          target_name: selectedTargetId ? null : targetName || null,
          target_strategy: selectedTargetId ? null : targetStrategy || null,
          reply_goal: replyGoal,
          tone,
          length: replyLength,
          proactivity,
          risk_level: riskLevel,
          candidate_count: 3,
        },
        {
          onConversation(nextConversationId, nextPromptVersion) {
            setConversationId(nextConversationId);
            setPromptVersion(nextPromptVersion);
          },
          onToken(candidate) {
            setCandidates((current) => upsertCandidate(current, candidate.index, candidate.text, 'append'));
          },
          onCandidate(candidate) {
            setCandidates((current) => upsertCandidate(current, candidate.index, candidate.text, 'replace'));
          },
        },
      );
      setConversationId(result.conversation_id);
      setPromptVersion(result.prompt_version);
      setCandidates(result.replies.map((text, index) => ({ index, text })));
      setStatus(`生成完成，LLM Call #${result.llm_call_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '生成失败');
    } finally {
      setGenerating(false);
    }
  }

  async function handleCopy(candidate: ReplyCandidate) {
    try {
      await navigator.clipboard.writeText(candidate.text);
      setStatus('已复制候选回复');
    } catch {
      setStatus('复制失败，可以手动选中文本复制');
    }
  }

  async function handleSelect(candidate: ReplyCandidate) {
    if (!conversationId) {
      return;
    }
    try {
      const conversation = await selectReply(conversationId, candidate.index);
      setSelectedIndex(candidate.index);
      setStatus(`已记录选择：Conversation #${conversation.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '选择上报失败');
    }
  }

  return (
    <section className="panel reply-panel">
      <div className="section-heading">
        <h2>帮聊回复生成</h2>
        <span>{promptVersion || 'Phase 4 Core Loop'}</span>
      </div>

      <label className="wide">
        当前聊天内容
        <textarea value={chatText} onChange={(event) => setChatText(event.target.value)} />
      </label>

      <div className="form-grid reply-controls">
        <label>
          已保存对象
          <select
            value={selectedTargetId ?? ''}
            onChange={(event) => setSelectedTargetId(event.target.value ? Number(event.target.value) : null)}
          >
            <option value="">手动填写</option>
            {targets.map((target) => (
              <option key={target.id} value={target.id}>
                {target.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          聊天对象
          <input
            disabled={selectedTargetId !== null}
            placeholder="可先只填名字"
            value={targetName}
            onChange={(event) => setTargetName(event.target.value)}
          />
        </label>
        <label>
          回复目标
          <select value={replyGoal} onChange={(event) => setReplyGoal(event.target.value)}>
            {replyGoals.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          语气
          <select value={tone} onChange={(event) => setTone(event.target.value)}>
            {toneOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          长度
          <select value={replyLength} onChange={(event) => setReplyLength(event.target.value)}>
            {lengthOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          风险
          <select value={riskLevel} onChange={(event) => setRiskLevel(event.target.value)}>
            {riskOptions.map((item) => (
              <option key={item} value={item}>
                {item}
              </option>
            ))}
          </select>
        </label>
        <label>
          推进感 {proactivity.toFixed(2)}
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={proactivity}
            onChange={(event) => setProactivity(Number(event.target.value))}
          />
        </label>
        <label className="wide">
          对象策略
          <input disabled={selectedTargetId !== null} value={targetStrategy} onChange={(event) => setTargetStrategy(event.target.value)} />
        </label>
      </div>

      <div className="actions">
        <button type="button" disabled={generating} onClick={() => void handleGenerate()}>
          {generating ? '生成中...' : '生成候选回复'}
        </button>
        {conversationId ? <span className="inline-meta">Conversation #{conversationId}</span> : null}
      </div>

      <div className="candidate-list">
        {candidates.length === 0 ? <div className="empty-state">候选回复会流式显示在这里</div> : null}
        {candidates.map((candidate) => (
          <article className={`candidate-card ${selectedIndex === candidate.index ? 'selected' : ''}`} key={candidate.index}>
            <div className="candidate-meta">候选 {candidate.index + 1}</div>
            <p>{candidate.text || '生成中...'}</p>
            <div className="candidate-actions">
              <button type="button" className="secondary" onClick={() => void handleCopy(candidate)}>
                复制
              </button>
              <button type="button" onClick={() => void handleSelect(candidate)} disabled={!conversationId || !candidate.text.trim()}>
                选中
              </button>
            </div>
          </article>
        ))}
      </div>

      <p className="reply-status">{status}</p>
    </section>
  );
}