import { useEffect, useRef, useState } from 'react';
import { ChatTarget, pollJobResult, QQImportResult, startQQJsonImport } from '../api';

interface QQImportPanelProps {
  targets: ChatTarget[];
  onTargetImported: (target: ChatTarget) => void;
  onImportComplete?: (result: QQImportResult) => void;
}

function splitAliases(value: string): string[] {
  return value
    .split(/[，,\n]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function QQImportPanel({ targets, onTargetImported, onImportComplete }: QQImportPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [meSpeakers, setMeSpeakers] = useState('我');
  const [targetName, setTargetName] = useState('');
  const [targetId, setTargetId] = useState<number | null>(null);
  const [status, setStatus] = useState('选择 QQ JSON 后开始导入');
  const [importing, setImporting] = useState(false);
  const [result, setResult] = useState<QQImportResult | null>(null);
  const cancelledRef = useRef(false);

  useEffect(() => {
    cancelledRef.current = false;
    return () => {
      cancelledRef.current = true;
    };
  }, []);

  async function handleImport() {
    if (!file) {
      setStatus('先选择一份 QQ JSON 文件');
      return;
    }
    const aliases = splitAliases(meSpeakers);
    if (!aliases.length) {
      setStatus('至少填写一个“我”的昵称或账号');
      return;
    }

    setImporting(true);
    setResult(null);
    try {
      setStatus('正在读取本地 JSON...');
      const rawText = await file.text();
      const rawJson = JSON.parse(rawText) as unknown;
      const started = await startQQJsonImport({
        filename: file.name,
        raw_json: rawJson,
        me_speakers: aliases,
        target_id: targetId,
        target_name: targetId ? null : targetName || null,
      });
      setStatus(`导入任务 #${started.job_id} 已提交`);
      const imported = await pollImportResult(started.job_id);
      setResult(imported);
      onTargetImported(imported.target);
      onImportComplete?.(imported);
      setStatus(`导入完成：${imported.message_count} 条消息，已生成 ${imported.profile.name} 与 ${imported.target.name} 档案`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '导入失败');
    } finally {
      setImporting(false);
    }
  }

  async function pollImportResult(jobId: number): Promise<QQImportResult> {
    return pollJobResult<QQImportResult>(jobId, {
      shouldCancel: () => cancelledRef.current,
      onProgress: (job) => setStatus(`导入任务 #${jobId}：${job.status} ${(job.progress * 100).toFixed(0)}%`),
    });
  }

  return (
    <section className="panel import-panel">
      <div className="section-heading">
        <h2>QQ JSON 导入</h2>
        <span>Phase 6 · 本地文件手动导入</span>
      </div>

      <div className="form-grid">
        <label className="wide">
          QQ JSON 文件
          <input type="file" accept="application/json,.json" onChange={(event) => setFile(event.target.files?.[0] || null)} />
        </label>
        <label>
          哪些发送者算“我”
          <input value={meSpeakers} onChange={(event) => setMeSpeakers(event.target.value)} placeholder="我，QQ号，昵称" />
        </label>
        <label>
          更新已有对象
          <select value={targetId ?? ''} onChange={(event) => setTargetId(event.target.value ? Number(event.target.value) : null)}>
            <option value="">导入时新建对象</option>
            {targets.map((target) => (
              <option key={target.id} value={target.id}>
                {target.name}
              </option>
            ))}
          </select>
        </label>
        {!targetId ? (
          <label className="wide">
            对方名称（可选）
            <input value={targetName} onChange={(event) => setTargetName(event.target.value)} placeholder="留空则使用 JSON 里的第一个对方昵称" />
          </label>
        ) : null}
      </div>

      <div className="actions">
        <button type="button" disabled={importing || !file} onClick={() => void handleImport()}>
          {importing ? '导入中...' : '开始导入'}
        </button>
      </div>

      {result ? (
        <div className="import-result">
          <p>
            消息：{result.message_count} 条 · 我：{result.user_message_count} 条 · 对方：{result.target_message_count} 条
          </p>
          <p>对象档案：{result.target.name}</p>
          <p>用户风格：{result.analysis.user.style_summary}</p>
        </div>
      ) : null}

      <p className="reply-status">{status}</p>
    </section>
  );
}
