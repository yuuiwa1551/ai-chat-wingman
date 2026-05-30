import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import {
  approveMemory,
  ChatTarget,
  createMemory,
  deleteMemory,
  listMemories,
  Memory,
  rejectMemory,
  updateMemory,
} from '../api';

interface MemoryReviewPanelProps {
  targets: ChatTarget[];
}

const memoryTypeOptions = ['preference', 'event', 'relationship', 'warning', 'fact', 'style'];

const statusLabels: Record<string, string> = {
  pending: '待确认',
  approved: '已确认',
  rejected: '已拒绝',
};

type PendingBucket = 'recommended' | 'uncertain' | 'low';

const bucketLabels: Record<PendingBucket, { title: string; description: string; action: string }> = {
  recommended: {
    title: '建议保存',
    description: '置信度较高，内容看起来能稳定影响后续回复。',
    action: '批量确认',
  },
  uncertain: {
    title: '不确定',
    description: '可能有用，但需要判断这是不是长期稳定信息。',
    action: '确认选中',
  },
  low: {
    title: '不建议保存',
    description: '置信度较低或更像一次性上下文，建议先忽略。',
    action: '批量忽略',
  },
};

export function MemoryReviewPanel({ targets }: MemoryReviewPanelProps) {
  const [selectedId, setSelectedId] = useState<number | null>(targets[0]?.id ?? null);
  const [memories, setMemories] = useState<Memory[]>([]);
  const [status, setStatus] = useState('选择一个对象查看长期记忆');
  const [loading, setLoading] = useState(false);
  const [newContent, setNewContent] = useState('');
  const [newType, setNewType] = useState('preference');
  const [busyGroup, setBusyGroup] = useState<string | null>(null);

  useEffect(() => {
    if (targets.length && selectedId == null) {
      setSelectedId(targets[0].id);
    }
  }, [targets, selectedId]);

  useEffect(() => {
    if (selectedId == null) {
      setMemories([]);
      return;
    }
    let cancelled = false;
    setLoading(true);
    listMemories(selectedId)
      .then((items) => {
        if (!cancelled) {
          setMemories(items);
          setStatus(`共 ${items.length} 条记忆`);
        }
      })
      .catch((error: Error) => !cancelled && setStatus(error.message))
      .finally(() => !cancelled && setLoading(false));
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  function replaceMemory(next: Memory) {
    setMemories((current) => current.map((memory) => (memory.id === next.id ? next : memory)));
  }

  function replaceMemories(nextItems: Memory[]) {
    const nextById = new Map(nextItems.map((memory) => [memory.id, memory]));
    setMemories((current) => current.map((memory) => nextById.get(memory.id) || memory));
  }

  async function refresh() {
    if (selectedId == null) {
      return;
    }
    const items = await listMemories(selectedId);
    setMemories(items);
    setStatus(`共 ${items.length} 条记忆`);
  }

  async function handleApprove(memory: Memory) {
    setStatus('正在确认记忆...');
    replaceMemory(await approveMemory(memory.id));
    setStatus('已确认，将进入后续生成上下文');
  }

  async function handleReject(memory: Memory) {
    setStatus('正在拒绝记忆...');
    replaceMemory(await rejectMemory(memory.id));
    setStatus('已拒绝');
  }

  async function handleBatchApprove(items: Memory[], groupId: string) {
    if (!items.length) {
      return;
    }
    setBusyGroup(groupId);
    setStatus(`正在确认 ${items.length} 条记忆...`);
    try {
      const updated = await Promise.all(items.map((memory) => approveMemory(memory.id)));
      replaceMemories(updated);
      setStatus(`已确认 ${items.length} 条记忆，将进入后续生成上下文`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '批量确认失败');
    } finally {
      setBusyGroup(null);
    }
  }

  async function handleBatchIgnore(items: Memory[], groupId: string) {
    if (!items.length) {
      return;
    }
    setBusyGroup(groupId);
    setStatus(`正在忽略 ${items.length} 条记忆...`);
    try {
      const updated = await Promise.all(items.map((memory) => rejectMemory(memory.id)));
      replaceMemories(updated);
      setStatus(`已忽略 ${items.length} 条记忆，不会进入后续生成上下文`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '批量忽略失败');
    } finally {
      setBusyGroup(null);
    }
  }

  async function handleEdit(memory: Memory) {
    const nextContent = window.prompt('编辑记忆内容', memory.content);
    if (nextContent == null) {
      return;
    }
    const trimmed = nextContent.trim();
    if (!trimmed) {
      setStatus('记忆内容不能为空');
      return;
    }
    setStatus('正在保存记忆...');
    replaceMemory(await updateMemory(memory.id, { content: trimmed }));
    setStatus('已更新记忆内容');
  }

  async function handleDelete(memory: Memory) {
    if (!window.confirm('确定删除这条记忆吗？')) {
      return;
    }
    setStatus('正在删除记忆...');
    await deleteMemory(memory.id);
    setMemories((current) => current.filter((item) => item.id !== memory.id));
    setStatus('已删除记忆');
  }

  async function handleCreate() {
    if (selectedId == null) {
      setStatus('先选择一个对象');
      return;
    }
    if (!newContent.trim()) {
      setStatus('先填写记忆内容');
      return;
    }
    setStatus('正在新增记忆...');
    await createMemory(selectedId, { content: newContent.trim(), memory_type: newType });
    setNewContent('');
    await refresh();
    setStatus('已新增待确认记忆');
  }

  const pending = memories.filter((memory) => memory.status === 'pending');
  const approved = memories.filter((memory) => memory.status === 'approved');
  const rejected = memories.filter((memory) => memory.status === 'rejected');
  const pendingBuckets = bucketPendingMemories(pending);

  if (!targets.length) {
    return (
      <section className="panel">
        <div className="section-heading">
          <h2>长期记忆</h2>
          <span>先创建聊天对象</span>
        </div>
        <p className="hint">记忆与聊天对象绑定，创建对象后即可在生成回复时自动提取与复用。</p>
      </section>
    );
  }

  return (
    <section className="panel memory-panel">
      <div className="section-heading">
        <h2>长期记忆</h2>
        <span>{loading ? '加载中...' : '生成回复后自动提取，需确认后才进入上下文'}</span>
      </div>

      <label className="memory-target-select">
        聊天对象
        <select
          value={selectedId ?? ''}
          onChange={(event) => setSelectedId(event.target.value ? Number(event.target.value) : null)}
        >
          {targets.map((target) => (
            <option key={target.id} value={target.id}>
              {target.name}
            </option>
          ))}
        </select>
      </label>

      <div className="memory-add">
        <select value={newType} onChange={(event) => setNewType(event.target.value)}>
          {memoryTypeOptions.map((option) => (
            <option key={option} value={option}>
              {option}
            </option>
          ))}
        </select>
        <input
          placeholder="手动添加一条记忆，例如：对方不喜欢被追问近况"
          value={newContent}
          onChange={(event) => setNewContent(event.target.value)}
        />
        <button type="button" onClick={() => void handleCreate()}>
          添加
        </button>
      </div>

      <div className="memory-decision-summary" aria-label="待确认记忆分类">
        {(Object.keys(bucketLabels) as PendingBucket[]).map((bucket) => (
          <div key={bucket}>
            <span>{bucketLabels[bucket].title}</span>
            <strong>{pendingBuckets[bucket].length}</strong>
          </div>
        ))}
      </div>

      {(Object.keys(bucketLabels) as PendingBucket[]).map((bucket) => (
        <MemoryDecisionGroup
          key={bucket}
          bucket={bucket}
          memories={pendingBuckets[bucket]}
          busy={busyGroup === bucket}
          onBatchApprove={() => void handleBatchApprove(pendingBuckets[bucket], bucket)}
          onBatchIgnore={() => void handleBatchIgnore(pendingBuckets[bucket], bucket)}
          renderActions={(memory) => (
            <>
              <button type="button" onClick={() => void handleApprove(memory)}>
                确认
              </button>
              <button type="button" className="secondary" onClick={() => void handleEdit(memory)}>
                编辑
              </button>
              <button type="button" className="secondary" onClick={() => void handleReject(memory)}>
                忽略
              </button>
            </>
          )}
        />
      ))}

      <MemoryGroup
        title={`已确认（${approved.length}）`}
        memories={approved}
        emptyHint="还没有确认的记忆"
        renderActions={(memory) => (
          <>
            <button type="button" className="secondary" onClick={() => void handleEdit(memory)}>
              编辑
            </button>
            <button type="button" className="secondary" onClick={() => void handleReject(memory)}>
              撤回
            </button>
            <button type="button" className="secondary" onClick={() => void handleDelete(memory)}>
              删除
            </button>
          </>
        )}
      />

      {rejected.length ? (
        <MemoryGroup
          title={`已拒绝（${rejected.length}）`}
          memories={rejected}
          emptyHint=""
          renderActions={(memory) => (
            <>
              <button type="button" className="secondary" onClick={() => void handleApprove(memory)}>
                恢复确认
              </button>
              <button type="button" className="secondary" onClick={() => void handleDelete(memory)}>
                删除
              </button>
            </>
          )}
        />
      ) : null}

      <footer className="status-line">{status}</footer>
    </section>
  );
}

function bucketPendingMemories(memories: Memory[]): Record<PendingBucket, Memory[]> {
  return memories.reduce<Record<PendingBucket, Memory[]>>(
    (groups, memory) => {
      groups[classifyPendingMemory(memory)].push(memory);
      return groups;
    },
    { recommended: [], uncertain: [], low: [] },
  );
}

function classifyPendingMemory(memory: Memory): PendingBucket {
  if (memory.confidence >= 0.78) {
    return 'recommended';
  }
  if (memory.confidence < 0.5) {
    return 'low';
  }
  return 'uncertain';
}

function memoryDecisionReason(memory: Memory): string {
  if (memory.confidence >= 0.78) {
    return '置信度较高，适合确认后用于后续回复。';
  }
  if (memory.confidence < 0.5) {
    return '置信度偏低，更适合先忽略，避免污染长期记忆。';
  }
  return '需要判断它是否稳定复用，确认前可以先编辑。';
}

function memorySourceLabel(memory: Memory): string {
  return memory.source_conversation_id ? `来自 Conversation #${memory.source_conversation_id}` : '手动添加或未绑定来源';
}

interface MemoryDecisionGroupProps {
  bucket: PendingBucket;
  memories: Memory[];
  busy: boolean;
  onBatchApprove: () => void;
  onBatchIgnore: () => void;
  renderActions: (memory: Memory) => ReactNode;
}

function MemoryDecisionGroup({ bucket, memories, busy, onBatchApprove, onBatchIgnore, renderActions }: MemoryDecisionGroupProps) {
  const meta = bucketLabels[bucket];
  const isLowBucket = bucket === 'low';
  return (
    <div className={`memory-decision-group memory-decision-${bucket}`}>
      <div className="memory-decision-heading">
        <div>
          <h3>
            {meta.title}（{memories.length}）
          </h3>
          <p>{meta.description}</p>
        </div>
        <div className="memory-batch-actions">
          <button type="button" disabled={busy || !memories.length} onClick={isLowBucket ? onBatchIgnore : onBatchApprove}>
            {busy ? '处理中...' : meta.action}
          </button>
          {!isLowBucket ? (
            <button type="button" className="secondary" disabled={busy || !memories.length} onClick={onBatchIgnore}>
              批量忽略
            </button>
          ) : null}
        </div>
      </div>
      {memories.length ? (
        <ul className="memory-list">
          {memories.map((memory) => (
            <MemoryListItem key={memory.id} memory={memory} renderActions={renderActions} />
          ))}
        </ul>
      ) : (
        <p className="hint">暂无{meta.title}记忆</p>
      )}
    </div>
  );
}

interface MemoryGroupProps {
  title: string;
  memories: Memory[];
  emptyHint: string;
  renderActions: (memory: Memory) => ReactNode;
}

function MemoryGroup({ title, memories, emptyHint, renderActions }: MemoryGroupProps) {
  return (
    <div className="memory-group">
      <h3>{title}</h3>
      {memories.length === 0 ? (
        emptyHint ? <p className="hint">{emptyHint}</p> : null
      ) : (
        <ul className="memory-list">
          {memories.map((memory) => (
            <MemoryListItem key={memory.id} memory={memory} renderActions={renderActions} />
          ))}
        </ul>
      )}
    </div>
  );
}

interface MemoryListItemProps {
  memory: Memory;
  renderActions: (memory: Memory) => ReactNode;
}

function MemoryListItem({ memory, renderActions }: MemoryListItemProps) {
  return (
    <li className={`memory-item memory-${memory.status}`}>
      <div className="memory-meta">
        <span className="memory-type">{memory.memory_type || 'fact'}</span>
        <span className="memory-confidence">置信度 {(memory.confidence * 100).toFixed(0)}%</span>
        <span className="memory-status">{statusLabels[memory.status] || memory.status}</span>
      </div>
      <p className="memory-content">{memory.content}</p>
      <div className="memory-explain">
        <span>{memoryDecisionReason(memory)}</span>
        <span>{memorySourceLabel(memory)}</span>
      </div>
      <div className="memory-actions">{renderActions(memory)}</div>
    </li>
  );
}
