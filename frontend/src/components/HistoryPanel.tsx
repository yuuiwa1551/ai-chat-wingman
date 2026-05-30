import { useState } from 'react';
import { ChatTarget, ConversationRecord, deleteSavedReply, listConversations, listSavedReplies, SavedReply } from '../api';

interface HistoryPanelProps {
  targets: ChatTarget[];
}

function preview(value: string | null, fallback = '无内容'): string {
  const cleaned = (value || '').trim();
  if (!cleaned) {
    return fallback;
  }
  return cleaned.length > 160 ? `${cleaned.slice(0, 160)}...` : cleaned;
}

export function HistoryPanel({ targets }: HistoryPanelProps) {
  const [query, setQuery] = useState('');
  const [targetId, setTargetId] = useState<number | null>(null);
  const [conversations, setConversations] = useState<ConversationRecord[]>([]);
  const [favorites, setFavorites] = useState<SavedReply[]>([]);
  const [status, setStatus] = useState('搜索历史记录或查看收藏回复');
  const [loading, setLoading] = useState(false);

  async function handleSearch() {
    setLoading(true);
    try {
      const [nextConversations, nextFavorites] = await Promise.all([
        listConversations({ query, target_id: targetId, limit: 12 }),
        listSavedReplies({ query, target_id: targetId, limit: 12 }),
      ]);
      setConversations(nextConversations);
      setFavorites(nextFavorites);
      setStatus(`找到 ${nextConversations.length} 条历史，${nextFavorites.length} 条收藏`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '搜索失败');
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(text: string) {
    try {
      await navigator.clipboard.writeText(text);
      setStatus('已复制收藏回复');
    } catch {
      setStatus('复制失败，可以手动选中文本复制');
    }
  }

  async function handleDelete(saved: SavedReply) {
    setStatus('正在移除收藏...');
    await deleteSavedReply(saved.id);
    setFavorites((current) => current.filter((item) => item.id !== saved.id));
    setStatus('已移除收藏');
  }

  return (
    <section className="panel history-panel">
      <div className="section-heading">
        <h2>历史与收藏</h2>
        <span>Phase 8 Search</span>
      </div>

      <div className="history-search-row">
        <input placeholder="搜索聊天内容、候选回复或收藏备注" value={query} onChange={(event) => setQuery(event.target.value)} />
        <select value={targetId ?? ''} onChange={(event) => setTargetId(event.target.value ? Number(event.target.value) : null)}>
          <option value="">全部对象</option>
          {targets.map((target) => (
            <option key={target.id} value={target.id}>
              {target.name}
            </option>
          ))}
        </select>
        <button type="button" disabled={loading} onClick={() => void handleSearch()}>
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      <div className="history-columns">
        <div>
          <h3>最近历史</h3>
          <div className="history-list">
            {conversations.length === 0 ? <div className="empty-state compact-empty">暂无历史结果</div> : null}
            {conversations.map((conversation) => (
              <article className="history-item" key={conversation.id}>
                <div className="memory-meta">
                  <span>Conversation #{conversation.id}</span>
                  <span>{conversation.target_name || '未命名对象'}</span>
                </div>
                <p>{preview(conversation.input_text)}</p>
                <small>{preview(conversation.selected_reply || conversation.generated_replies, '尚未选择回复')}</small>
              </article>
            ))}
          </div>
        </div>

        <div>
          <h3>收藏回复</h3>
          <div className="history-list">
            {favorites.length === 0 ? <div className="empty-state compact-empty">暂无收藏结果</div> : null}
            {favorites.map((favorite) => (
              <article className="history-item favorite-item" key={favorite.id}>
                <div className="memory-meta">
                  <span>Favorite #{favorite.id}</span>
                  {favorite.note ? <span>{favorite.note}</span> : null}
                </div>
                <p>{favorite.text}</p>
                <div className="memory-actions">
                  <button type="button" className="secondary" onClick={() => void handleCopy(favorite.text)}>
                    复制
                  </button>
                  <button type="button" className="secondary" onClick={() => void handleDelete(favorite)}>
                    移除
                  </button>
                </div>
              </article>
            ))}
          </div>
        </div>
      </div>

      <p className="reply-status">{status}</p>
    </section>
  );
}
