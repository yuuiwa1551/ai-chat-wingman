import { useEffect, useMemo, useState } from 'react';
import { favoriteReply, generateReply, selectReply } from '../api';
import type { ChatTarget, ReplyCandidate } from '../api';
import { buildTargetPromptSummary, buildTargetRules } from '../targetInsights';
import { ImageInputPanel } from './ImageInputPanel';

const replyGoals = ['接住情绪', '自然接话', '推进邀约', '解释清楚', '结束话题'];
const toneOptions = ['自然', '温柔', '轻松一点', '冷静克制', '直接坦率'];
const lengthOptions = ['短句', '中等', '稍微展开'];
const riskOptions = ['别太主动', '稍主动', '边界清楚'];
const candidateLabels = ['自然版', '轻松版', '短句版'];

type BubbleSpeaker = 'me' | 'target' | 'unknown';

interface ReplyScenario {
  id: string;
  label: string;
  goal: string;
  tone: string;
  length: string;
  risk: string;
  proactivity: number;
  strategy: string;
  candidateReasons: [string, string, string];
}

const replyScenarios: ReplyScenario[] = [
  {
    id: 'tired-space',
    label: '对方累了',
    goal: '接住情绪',
    tone: '温柔',
    length: '短句',
    risk: '别太主动',
    proactivity: 0.2,
    strategy: '先承认对方状态，再给空间，不追问原因。',
    candidateReasons: ['先给空间，不追问原因。', '共情更明显，适合对方愿意多聊时。', '更短，适合直接收住。'],
  },
  {
    id: 'cold-reply',
    label: '对方冷淡',
    goal: '自然接话',
    tone: '轻松一点',
    length: '短句',
    risk: '别太主动',
    proactivity: 0.3,
    strategy: '降低压迫感，用一句轻量回应把话题接住。',
    candidateReasons: ['轻接一句，不拉高压力。', '稍微带一点情绪回应，避免尴尬。', '短句保留退路。'],
  },
  {
    id: 'invite',
    label: '推进邀约',
    goal: '推进邀约',
    tone: '自然',
    length: '中等',
    risk: '稍主动',
    proactivity: 0.65,
    strategy: '给出具体但可拒绝的选项，避免让对方必须马上答应。',
    candidateReasons: ['给具体选项，也允许对方拒绝。', '语气更轻，降低邀约压力。', '短句试探，不把话说满。'],
  },
  {
    id: 'repair',
    label: '缓和误会',
    goal: '解释清楚',
    tone: '冷静克制',
    length: '稍微展开',
    risk: '边界清楚',
    proactivity: 0.45,
    strategy: '先承认影响，再解释立场，最后给对方空间。',
    candidateReasons: ['先承认影响，再解释自己。', '语气更软，适合对方还在情绪里。', '把边界说短，避免继续争辩。'],
  },
  {
    id: 'exit',
    label: '体面结束',
    goal: '结束话题',
    tone: '自然',
    length: '短句',
    risk: '边界清楚',
    proactivity: 0.15,
    strategy: '礼貌收住话题，不继续拉扯，也不显得突然消失。',
    candidateReasons: ['自然收尾，保留礼貌。', '多一点缓和，不显得冷处理。', '一句话结束，减少继续拉扯。'],
  },
];
const initialScenario = replyScenarios[0];

interface ChatBubble {
  speaker: BubbleSpeaker;
  content: string;
}

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

function parseChatBubbles(value: string): ChatBubble[] {
  const lines = value
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean);

  return lines.map((line) => {
    const match = line.match(/^([^:：]{1,16})[:：]\s*(.*)$/);
    if (!match) {
      return { speaker: 'unknown', content: line };
    }
    const label = match[1].toLowerCase();
    const content = match[2] || line;
    if (label.includes('我') || label.includes('me') || label.includes('user')) {
      return { speaker: 'me', content };
    }
    if (label.includes('对方') || label.includes('target') || label.includes('ta')) {
      return { speaker: 'target', content };
    }
    return { speaker: 'unknown', content: line };
  });
}

function nextOption(options: string[], current: string): string {
  const index = options.indexOf(current);
  return options[(index + 1) % options.length] || options[0];
}

function getCandidateReason(index: number, scenario: ReplyScenario | undefined, replyGoal: string, tone: string, riskLevel: string) {
  const scenarioLabel = scenario?.label || replyGoal;
  const fallbackReasons = [`语气保持${tone}。`, `稍微多给一点情绪，但仍然${riskLevel}。`, '压短表达，方便直接复制发送。'];
  return `${scenarioLabel}：${scenario?.candidateReasons[index] || fallbackReasons[index] || fallbackReasons[0]}`;
}

interface ReplyGeneratorProps {
  targets: ChatTarget[];
  activeTargetId?: number | null;
  onActiveTargetChange?: (targetId: number | null) => void;
  onTargetUsed?: (targetId: number) => void;
}

export function ReplyGenerator({ targets, activeTargetId, onActiveTargetChange, onTargetUsed }: ReplyGeneratorProps) {
  const [internalTargetId, setInternalTargetId] = useState<number | null>(activeTargetId ?? null);
  const selectedTargetId = activeTargetId !== undefined ? activeTargetId : internalTargetId;
  const selectedTarget = targets.find((target) => target.id === selectedTargetId) || null;

  const [chatText, setChatText] = useState('对方：今天真的累死了，不太想说话。\n我：那我先不吵你，晚点给你发个好笑的。\n对方：不用啦，我可能就是有点烦。');
  const [targetName, setTargetName] = useState('');
  const [targetStrategy, setTargetStrategy] = useState(initialScenario.strategy);
  const [replyGoal, setReplyGoal] = useState(initialScenario.goal);
  const [tone, setTone] = useState(initialScenario.tone);
  const [replyLength, setReplyLength] = useState(initialScenario.length);
  const [riskLevel, setRiskLevel] = useState(initialScenario.risk);
  const [proactivity, setProactivity] = useState(initialScenario.proactivity);
  const [selectedScenarioId, setSelectedScenarioId] = useState(initialScenario.id);
  const [conversationId, setConversationId] = useState<number | null>(null);
  const [promptVersion, setPromptVersion] = useState('');
  const [candidates, setCandidates] = useState<ReplyCandidate[]>([]);
  const [selectedIndex, setSelectedIndex] = useState<number | null>(null);
  const [status, setStatus] = useState('等待输入聊天内容');
  const [generating, setGenerating] = useState(false);
  const [showScreenshotInput, setShowScreenshotInput] = useState(false);

  const bubbles = useMemo(() => parseChatBubbles(chatText), [chatText]);
  const effectiveTargetName = selectedTarget?.name || targetName || '手动对象';
  const effectiveTargetStrategy = selectedTarget?.strategy_guideline || selectedTarget?.style_summary || targetStrategy;
  const selectedScenario = replyScenarios.find((scenario) => scenario.id === selectedScenarioId);
  const targetRules = useMemo(() => buildTargetRules(selectedTarget), [selectedTarget]);
  const targetPromptSummary = useMemo(() => buildTargetPromptSummary(selectedTarget), [selectedTarget]);
  const visibleCandidates = candidates.length
    ? candidates
    : candidateLabels.map((label, index) => ({
        index,
        text:
          index === 0
            ? '那你先缓一下，别急着说也行。'
            : index === 1
              ? '感觉你今天是真的被耗住了，先别管我。'
              : '懂，别硬撑。晚点再说。',
      }));

  useEffect(() => {
    if (activeTargetId !== undefined) {
      setInternalTargetId(activeTargetId);
    }
  }, [activeTargetId]);

  function updateTargetId(nextTargetId: number | null) {
    setInternalTargetId(nextTargetId);
    onActiveTargetChange?.(nextTargetId);
  }

  function applyScenario(scenario: ReplyScenario) {
    setSelectedScenarioId(scenario.id);
    setReplyGoal(scenario.goal);
    setTone(scenario.tone);
    setReplyLength(scenario.length);
    setRiskLevel(scenario.risk);
    setProactivity(scenario.proactivity);
    setTargetStrategy(scenario.strategy);
    setStatus(`已切换场景：${scenario.label}`);
  }

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
      if (selectedTargetId !== null) {
        onTargetUsed?.(selectedTargetId);
      }
      setStatus(`生成完成，LLM Call #${result.llm_call_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '生成失败');
    } finally {
      setGenerating(false);
    }
  }

  async function handleReadClipboard() {
    try {
      const text = await navigator.clipboard.readText();
      if (!text.trim()) {
        setStatus('剪贴板里没有可用文本');
        return;
      }
      setChatText(text);
      setStatus('已读取剪贴板文本');
    } catch {
      setStatus('读取剪贴板失败，可以手动粘贴到输入框');
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

  async function handleFavorite(candidate: ReplyCandidate) {
    if (!conversationId || !candidate.text.trim()) {
      setStatus('先生成完整候选后再收藏');
      return;
    }
    try {
      const saved = await favoriteReply(conversationId, { candidate_index: candidate.index });
      setStatus(`已收藏回复 #${saved.id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '收藏失败');
    }
  }

  return (
    <>
      <section className="chat-workspace">
        <div className="chat-workspace-header">
          <div>
            <h2>当前聊天</h2>
            <p>{promptVersion || '今天 22:14'}</p>
          </div>
          <span className="chat-time">今天 22:14</span>
        </div>

        <div className="chat-thread" aria-label="当前聊天内容">
          {bubbles.length ? null : <div className="empty-state">聊天内容会显示在这里</div>}
          {bubbles.map((bubble, index) => (
            <div className={`chat-bubble ${bubble.speaker}`} key={`${bubble.speaker}-${index}-${bubble.content.slice(0, 12)}`}>
              <span>{bubble.speaker === 'me' ? '我' : bubble.speaker === 'target' ? effectiveTargetName : '上下文'}</span>
              <p>{bubble.content}</p>
            </div>
          ))}
        </div>

        <div className="composer-dock">
          <div className="pending-memory-strip">
            <div>
              <strong>待确认记忆</strong>
              <p>对方疲惫时少追问，适合给空间。</p>
            </div>
            <button type="button" className="danger">确认</button>
          </div>

          <div className="composer-chip-row">
            <button
              type="button"
              className="chip selected"
              onClick={() => {
                setSelectedScenarioId('custom');
                setReplyGoal(nextOption(replyGoals, replyGoal));
              }}
            >
              {replyGoal}
            </button>
            <button
              type="button"
              className="chip selected"
              onClick={() => {
                setSelectedScenarioId('custom');
                setTone(nextOption(toneOptions, tone));
              }}
            >
              {tone}
            </button>
            <button
              type="button"
              className="chip warning-chip"
              onClick={() => {
                setSelectedScenarioId('custom');
                setRiskLevel(nextOption(riskOptions, riskLevel));
              }}
            >
              {riskLevel}
            </button>
          </div>

          <div className="scenario-chip-row" aria-label="常用回复场景">
            {replyScenarios.map((scenario) => (
              <button
                type="button"
                key={scenario.id}
                className={`scenario-chip ${scenario.id === selectedScenarioId ? 'active' : ''}`}
                onClick={() => applyScenario(scenario)}
              >
                {scenario.label}
              </button>
            ))}
          </div>
          <p className="scenario-context">{selectedScenario?.strategy || effectiveTargetStrategy}</p>

          <div className={`target-impact-strip ${selectedTarget ? '' : 'empty'}`}>
            <div className="target-impact-heading">
              <strong>{selectedTarget ? `${effectiveTargetName} 会影响这轮回复` : '未选择对象档案'}</strong>
              <span>{selectedTarget?.relationship || '通用策略'}</span>
            </div>
            <div className="target-impact-rule-row">
              {targetRules.map((rule) => (
                <span key={`${rule.label}-${rule.text}`}>
                  <strong>{rule.label}</strong>
                  {rule.text}
                </span>
              ))}
            </div>
            <p>{targetPromptSummary}</p>
          </div>

          <div className="reply-input-row">
            <textarea
              aria-label="聊天内容或想回复的重点"
              value={chatText}
              onChange={(event) => setChatText(event.target.value)}
              placeholder="粘贴聊天内容，或写下你想回复的重点..."
            />
            <button type="button" className="secondary" onClick={() => void handleReadClipboard()}>
              读取剪贴板
            </button>
            <button type="button" className="secondary" onClick={() => setShowScreenshotInput((current) => !current)}>
              {showScreenshotInput ? '收起截图' : '截图解析'}
            </button>
            <button type="button" disabled={generating} onClick={() => void handleGenerate()}>
              {generating ? '生成中' : '生成'}
            </button>
          </div>

          {showScreenshotInput ? (
            <ImageInputPanel
              onApplyText={(nextChatText) => {
                setChatText(nextChatText);
                setStatus('已将截图解析内容写入聊天输入');
              }}
            />
          ) : null}
        </div>
      </section>

      <aside className="candidate-sidebar">
        <div className="candidate-sidebar-header">
          <div>
            <h2>候选回复</h2>
            <p>{conversationId ? `Conversation #${conversationId}` : '等待生成'}</p>
          </div>
          <span className="status-pill">{generating ? '流式中' : candidates.length ? '已生成' : '示例'}</span>
        </div>

        <div className="candidate-list">
          {visibleCandidates.map((candidate) => {
            const isPreview = candidates.length === 0;
            return (
            <article className={`candidate-card ${selectedIndex === candidate.index ? 'selected' : ''} ${isPreview ? 'preview' : ''}`} key={candidate.index}>
              <div className="candidate-meta">
                <strong>{candidateLabels[candidate.index] || `候选 ${candidate.index + 1}`}</strong>
                <span>{riskLevel}</span>
              </div>
              <p>{candidate.text || '生成中...'}</p>
              <small className="candidate-reason">{getCandidateReason(candidate.index, selectedScenario, replyGoal, tone, riskLevel)}</small>
              <div className="candidate-actions">
                <button type="button" className="secondary" onClick={() => void handleCopy(candidate)} disabled={isPreview || !candidate.text.trim()}>
                  复制
                </button>
                <button type="button" onClick={() => void handleSelect(candidate)} disabled={isPreview || !conversationId || !candidate.text.trim()}>
                  选中
                </button>
                <button type="button" className="secondary" onClick={() => void handleFavorite(candidate)} disabled={isPreview || !conversationId || !candidate.text.trim()}>
                  收藏
                </button>
              </div>
            </article>
            );
          })}
        </div>

        <div className="candidate-feedback-card">
          <strong>选择反馈</strong>
          <p>复制或选中的文本会作为风格校准信号。</p>
        </div>
        <p className="reply-status">{status}</p>
      </aside>
    </>
  );
}
