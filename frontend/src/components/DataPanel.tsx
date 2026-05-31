import { useEffect, useState } from 'react';
import { BackupExportResult, DataSummary, getDataSummary, getJob, purgeAllData, startDataExport } from '../api';

function formatBytes(value: number): string {
  if (value < 1024) {
    return `${value} B`;
  }
  if (value < 1024 * 1024) {
    return `${(value / 1024).toFixed(1)} KB`;
  }
  return `${(value / 1024 / 1024).toFixed(1)} MB`;
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function DataPanel() {
  const [summary, setSummary] = useState<DataSummary | null>(null);
  const [exportResult, setExportResult] = useState<BackupExportResult | null>(null);
  const [status, setStatus] = useState('正在读取本地数据概览...');
  const [exporting, setExporting] = useState(false);
  const [purgeOpen, setPurgeOpen] = useState(false);
  const [purgeConfirmText, setPurgeConfirmText] = useState('');
  const [purgeIncludeSettings, setPurgeIncludeSettings] = useState(false);
  const [purging, setPurging] = useState(false);

  const PURGE_CONFIRM_TEXT = 'DELETE';

  useEffect(() => {
    void refreshSummary();
  }, []);

  async function refreshSummary() {
    try {
      const nextSummary = await getDataSummary();
      setSummary(nextSummary);
      setStatus('数据概览已更新');
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '读取数据概览失败');
    }
  }

  async function handleExport() {
    setExporting(true);
    setExportResult(null);
    try {
      const started = await startDataExport();
      setStatus(`备份任务 #${started.job_id} 已提交`);
      const result = await pollBackupResult(started.job_id);
      setExportResult(result);
      setStatus(`备份完成：${result.backup_path}`);
      await refreshSummary();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '备份失败');
    } finally {
      setExporting(false);
    }
  }

  async function pollBackupResult(jobId: number): Promise<BackupExportResult> {
    for (let attempt = 0; attempt < 80; attempt += 1) {
      const job = await getJob(jobId);
      setStatus(`备份任务 #${jobId}：${job.status} ${(job.progress * 100).toFixed(0)}%`);
      if (job.status === 'success') {
        if (!job.result) {
          throw new Error('备份任务完成但没有结果');
        }
        return JSON.parse(job.result) as BackupExportResult;
      }
      if (job.status === 'failed') {
        throw new Error(job.error_message || '备份任务失败');
      }
      await delay(500);
    }
    throw new Error('备份任务超时');
  }

  async function handlePurge() {
    if (purgeConfirmText !== PURGE_CONFIRM_TEXT) {
      setStatus(`请输入 ${PURGE_CONFIRM_TEXT} 以确认清空`);
      return;
    }
    setPurging(true);
    try {
      const result = await purgeAllData(purgeConfirmText, purgeIncludeSettings);
      const rows = Object.values(result.deleted_rows).reduce((sum, count) => sum + count, 0);
      setExportResult(null);
      setPurgeOpen(false);
      setPurgeConfirmText('');
      setPurgeIncludeSettings(false);
      setStatus(`已清空 ${rows} 条记录、${result.removed_files} 个文件`);
      await refreshSummary();
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '清空数据失败');
    } finally {
      setPurging(false);
    }
  }

  return (
    <section className="panel data-panel">
      <div className="section-heading">
        <h2>本地数据</h2>
        <span>Phase 8 Backup</span>
      </div>

      {summary ? (
        <div className="data-summary-grid">
          <div>
            <span>数据目录</span>
            <strong>{summary.data_path}</strong>
          </div>
          <div>
            <span>总占用</span>
            <strong>{formatBytes(summary.total_size_bytes)}</strong>
          </div>
          <div>
            <span>生成记录</span>
            <strong>{summary.table_counts.conversations || 0}</strong>
          </div>
          <div>
            <span>对象 / 记忆</span>
            <strong>
              {summary.table_counts.chat_targets || 0} / {summary.table_counts.memories || 0}
            </strong>
          </div>
          <div>
            <span>备份目录</span>
            <strong>{summary.backups_path}</strong>
          </div>
          <div>
            <span>备份占用</span>
            <strong>{formatBytes(summary.section_sizes.backups || 0)}</strong>
          </div>
        </div>
      ) : (
        <div className="empty-state compact-empty">正在加载数据概览</div>
      )}

      {exportResult ? (
        <div className="import-result">
          <p>备份文件：{exportResult.backup_path}</p>
          <p>
            大小：{formatBytes(exportResult.backup_size_bytes)} · 文件数：{exportResult.included_file_count}
          </p>
        </div>
      ) : null}

      <div className="actions">
        <button type="button" className="secondary" onClick={() => void refreshSummary()}>
          刷新概览
        </button>
        <button type="button" disabled={exporting} onClick={() => void handleExport()}>
          {exporting ? '备份中...' : '导出本地备份'}
        </button>
        <button
          type="button"
          className="secondary"
          disabled={purging}
          onClick={() => setPurgeOpen((open) => !open)}
        >
          清空全部数据
        </button>
      </div>

      {purgeOpen ? (
        <div className="purge-confirm">
          <p>
            此操作会清空本地全部对象、记忆、历史、风格测试与备份文件，不可恢复。建议先导出备份。输入
            <strong> {PURGE_CONFIRM_TEXT} </strong>
            以确认。
          </p>
          <label>
            确认词
            <input
              value={purgeConfirmText}
              onChange={(event) => setPurgeConfirmText(event.target.value)}
              placeholder={PURGE_CONFIRM_TEXT}
            />
          </label>
          <label className="purge-include-settings">
            <input
              type="checkbox"
              checked={purgeIncludeSettings}
              onChange={(event) => setPurgeIncludeSettings(event.target.checked)}
            />
            同时清除 Provider 配置（默认保留）
          </label>
          <div className="actions">
            <button
              type="button"
              className="secondary"
              onClick={() => {
                setPurgeOpen(false);
                setPurgeConfirmText('');
                setPurgeIncludeSettings(false);
              }}
            >
              取消
            </button>
            <button
              type="button"
              className="danger"
              disabled={purging || purgeConfirmText !== PURGE_CONFIRM_TEXT}
              onClick={() => void handlePurge()}
            >
              {purging ? '清空中...' : '确认清空'}
            </button>
          </div>
        </div>
      ) : null}

      <p className="reply-status">{status}</p>
    </section>
  );
}
