import { useState } from 'react';
import { ChatTarget, createTarget, deleteTarget, organizeTarget, updateTarget } from '../api';

const emptyDraft = {
  name: '',
  relationship: '',
  style_summary: '',
  preferences: '',
  taboos: '',
  strategy_guideline: '',
};

type TargetDraft = typeof emptyDraft;

interface TargetManagerProps {
  targets: ChatTarget[];
  onTargetsChange: (targets: ChatTarget[]) => void;
}

function draftFromTarget(target: ChatTarget | null): TargetDraft {
  if (!target) {
    return emptyDraft;
  }
  return {
    name: target.name,
    relationship: target.relationship || '',
    style_summary: target.style_summary || '',
    preferences: target.preferences || '',
    taboos: target.taboos || '',
    strategy_guideline: target.strategy_guideline || '',
  };
}

export function TargetManager({ targets, onTargetsChange }: TargetManagerProps) {
  const [selectedId, setSelectedId] = useState<number | null>(targets[0]?.id ?? null);
  const selectedTarget = targets.find((target) => target.id === selectedId) || null;
  const [draft, setDraft] = useState<TargetDraft>(draftFromTarget(selectedTarget));
  const [notes, setNotes] = useState('她压力大时不喜欢被催回复，更喜欢低压力、短一点的关心。');
  const [status, setStatus] = useState('等待创建或选择对象档案');
  const [saving, setSaving] = useState(false);

  function replaceTarget(nextTarget: ChatTarget) {
    const exists = targets.some((target) => target.id === nextTarget.id);
    const nextTargets = exists ? targets.map((target) => (target.id === nextTarget.id ? nextTarget : target)) : [nextTarget, ...targets];
    onTargetsChange(nextTargets);
    setSelectedId(nextTarget.id);
    setDraft(draftFromTarget(nextTarget));
  }

  function handleSelect(targetId: number | null) {
    const target = targets.find((item) => item.id === targetId) || null;
    setSelectedId(target?.id ?? null);
    setDraft(draftFromTarget(target));
    setStatus(target ? `正在编辑 ${target.name}` : '准备创建新对象');
  }

  async function handleSave() {
    if (!draft.name.trim()) {
      setStatus('先填写对象名称');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: draft.name,
        relationship: draft.relationship || null,
        style_summary: draft.style_summary || null,
        preferences: draft.preferences || null,
        taboos: draft.taboos || null,
        strategy_guideline: draft.strategy_guideline || null,
      };
      const target = selectedTarget ? await updateTarget(selectedTarget.id, payload) : await createTarget(payload);
      replaceTarget(target);
      setStatus(`已保存对象档案：${target.name}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '保存对象失败');
    } finally {
      setSaving(false);
    }
  }

  async function handleOrganize() {
    if (!selectedTarget) {
      setStatus('先保存对象后再整理');
      return;
    }
    setSaving(true);
    try {
      const result = await organizeTarget(selectedTarget.id, notes);
      replaceTarget(result.target);
      setStatus(`AI 已整理档案，LLM Call #${result.llm_call_id}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : 'AI 整理失败');
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!selectedTarget) {
      return;
    }
    setSaving(true);
    try {
      await deleteTarget(selectedTarget.id);
      const nextTargets = targets.filter((target) => target.id !== selectedTarget.id);
      onTargetsChange(nextTargets);
      handleSelect(nextTargets[0]?.id ?? null);
      setStatus('已删除对象档案');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '删除失败');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel target-panel">
      <div className="section-heading">
        <h2>聊天对象档案</h2>
        <span>{targets.length} targets</span>
      </div>

      <div className="target-layout">
        <div className="target-list">
          <button type="button" className={!selectedTarget ? 'chip selected' : 'chip'} onClick={() => handleSelect(null)}>
            新建对象
          </button>
          {targets.map((target) => (
            <button
              type="button"
              key={target.id}
              className={selectedId === target.id ? 'chip selected' : 'chip'}
              onClick={() => handleSelect(target.id)}
            >
              {target.name}
            </button>
          ))}
        </div>

        <div className="form-grid target-form">
          <label>
            名称
            <input value={draft.name} onChange={(event) => setDraft({ ...draft, name: event.target.value })} />
          </label>
          <label>
            关系
            <input value={draft.relationship} onChange={(event) => setDraft({ ...draft, relationship: event.target.value })} />
          </label>
          <label className="wide">
            对象摘要
            <textarea value={draft.style_summary} onChange={(event) => setDraft({ ...draft, style_summary: event.target.value })} />
          </label>
          <label>
            偏好
            <textarea value={draft.preferences} onChange={(event) => setDraft({ ...draft, preferences: event.target.value })} />
          </label>
          <label>
            禁忌
            <textarea value={draft.taboos} onChange={(event) => setDraft({ ...draft, taboos: event.target.value })} />
          </label>
          <label className="wide">
            回复策略
            <textarea value={draft.strategy_guideline} onChange={(event) => setDraft({ ...draft, strategy_guideline: event.target.value })} />
          </label>
        </div>
      </div>

      <label className="organize-notes">
        AI 整理笔记
        <textarea value={notes} onChange={(event) => setNotes(event.target.value)} />
      </label>

      <div className="actions">
        <button type="button" disabled={saving} onClick={() => void handleSave()}>
          {saving ? '保存中...' : '保存对象'}
        </button>
        <button type="button" className="secondary" disabled={saving || !selectedTarget} onClick={() => void handleOrganize()}>
          AI 整理
        </button>
        <button type="button" className="secondary" disabled={saving || !selectedTarget} onClick={() => void handleDelete()}>
          删除
        </button>
      </div>

      <p className="reply-status">{status}</p>
    </section>
  );
}