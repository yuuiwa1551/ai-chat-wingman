import { useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import type { ChatTarget } from '../api';
import { DataPanel } from './DataPanel';
import { HistoryPanel } from './HistoryPanel';
import { MemoryReviewPanel } from './MemoryReviewPanel';
import { QQImportPanel } from './QQImportPanel';
import { ReplyGenerator } from './ReplyGenerator';
import { StyleTestPanel } from './StyleTestPanel';
import { TargetManager } from './TargetManager';

type WorkspacePanel = 'reply' | 'targets' | 'import' | 'memory' | 'history' | 'data' | 'style' | 'settings';

interface FloatingWorkspaceProps {
  targets: ChatTarget[];
  providerCount: number;
  status: string;
  providerSettings: ReactNode;
  onTargetsChange: (targets: ChatTarget[]) => void;
  onTargetImported: (target: ChatTarget) => void;
}

const navItems: Array<{ id: WorkspacePanel; label: string; mark: string }> = [
  { id: 'reply', label: '回复', mark: '聊' },
  { id: 'targets', label: '对象', mark: '人' },
  { id: 'memory', label: '记忆', mark: '记' },
];

export function FloatingWorkspace({
  targets,
  providerCount,
  status,
  providerSettings,
  onTargetsChange,
  onTargetImported,
}: FloatingWorkspaceProps) {
  const [activePanel, setActivePanel] = useState<WorkspacePanel>('reply');
  const [activeTargetId, setActiveTargetId] = useState<number | null>(targets[0]?.id ?? null);

  const activeTarget = useMemo(
    () => targets.find((target) => target.id === activeTargetId) || targets[0] || null,
    [activeTargetId, targets],
  );

  function handleTargetUsed(targetId: number) {
    const used = targets.find((target) => target.id === targetId);
    if (used) {
      onTargetsChange([used, ...targets.filter((target) => target.id !== targetId)]);
    }
  }

  return (
    <main className="window-shell workspace-shell">
      <header className="workspace-topbar">
        <div>
          <h1>AI Chat Wingman</h1>
          <p>只生成候选回复，不自动发送</p>
        </div>
        <div className="workspace-topbar-actions">
          <span className="status-pill">{activeTarget ? activeTarget.name : '未选择对象'}</span>
          <span className="status-pill">{providerCount ? `${providerCount} Providers` : 'Mock Ready'}</span>
          <button type="button" className="secondary" onClick={() => setActivePanel('settings')}>
            设置
          </button>
          <button type="button">收起窗口</button>
        </div>
      </header>

      <div className="workspace-grid">
        <nav className="workspace-rail" aria-label="工作区导航">
          {navItems.map((item) => (
            <button
              type="button"
              key={item.id}
              className={activePanel === item.id ? 'rail-item active' : 'rail-item'}
              onClick={() => setActivePanel(item.id)}
              title={item.label}
            >
              <span>{item.mark}</span>
              <small>{item.label}</small>
            </button>
          ))}
        </nav>

        {activePanel === 'reply' ? (
          <>
            <TargetSidebar
              targets={targets}
              activeTargetId={activeTarget?.id ?? null}
              onActiveTargetChange={setActiveTargetId}
              onCreateTarget={() => setActivePanel('targets')}
            />
            <ReplyGenerator
              targets={targets}
              activeTargetId={activeTarget?.id ?? null}
              onActiveTargetChange={setActiveTargetId}
              onTargetUsed={handleTargetUsed}
            />
          </>
        ) : (
          <section className="workspace-secondary">
            <SecondaryPanel
              panel={activePanel}
              targets={targets}
              providerSettings={providerSettings}
              onTargetsChange={onTargetsChange}
              onTargetImported={onTargetImported}
            />
          </section>
        )}
      </div>

      <footer className="workspace-status">{status}</footer>
    </main>
  );
}

interface TargetSidebarProps {
  targets: ChatTarget[];
  activeTargetId: number | null;
  onActiveTargetChange: (targetId: number | null) => void;
  onCreateTarget: () => void;
}

function TargetSidebar({ targets, activeTargetId, onActiveTargetChange, onCreateTarget }: TargetSidebarProps) {
  const activeTarget = targets.find((target) => target.id === activeTargetId) || targets[0] || null;

  return (
    <aside className="target-sidebar">
      <div className="target-sidebar-heading">
        <h2>对象</h2>
        <button type="button" className="secondary compact-button" onClick={onCreateTarget}>
          新建
        </button>
      </div>
      <input className="target-search" placeholder="搜索对象或标签" readOnly />

      <div className="target-sidebar-list">
        {targets.length ? null : <p className="hint">暂无对象，可先手动填写对象名称生成回复。</p>}
        {targets.map((target) => (
          <button
            type="button"
            key={target.id}
            className={target.id === activeTarget?.id ? 'target-sidebar-card active' : 'target-sidebar-card'}
            onClick={() => onActiveTargetChange(target.id)}
          >
            <span className="target-avatar">{target.name.slice(0, 1) || '?'}</span>
            <span>
              <strong>{target.name}</strong>
              <small>{target.relationship || target.style_summary || '未填写关系'}</small>
            </span>
          </button>
        ))}
      </div>

      <div className="target-tip-card">
        <h3>对象提示</h3>
        <p>{activeTarget?.strategy_guideline || activeTarget?.style_summary || 'AI 会根据你与 Ta 的关系、偏好和禁忌组织回复。'}</p>
      </div>

      <div className="local-status-card">
        <h3>本地状态</h3>
        <p>长期记忆待确认，截图和导入文件只保存在本机。</p>
      </div>
    </aside>
  );
}

interface SecondaryPanelProps {
  panel: WorkspacePanel;
  targets: ChatTarget[];
  providerSettings: ReactNode;
  onTargetsChange: (targets: ChatTarget[]) => void;
  onTargetImported: (target: ChatTarget) => void;
}

function SecondaryPanel({ panel, targets, providerSettings, onTargetsChange, onTargetImported }: SecondaryPanelProps) {
  if (panel === 'targets') {
    return <TargetManager targets={targets} onTargetsChange={onTargetsChange} />;
  }
  if (panel === 'import') {
    return <QQImportPanel targets={targets} onTargetImported={onTargetImported} />;
  }
  if (panel === 'memory') {
    return <MemoryReviewPanel targets={targets} />;
  }
  if (panel === 'history') {
    return <HistoryPanel targets={targets} />;
  }
  if (panel === 'data') {
    return <DataPanel />;
  }
  if (panel === 'style') {
    return <StyleTestPanel />;
  }
  return <>{providerSettings}</>;
}
