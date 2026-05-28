import { useState } from 'react';
import { createDefaultProfile, StylePreset, UserProfile } from '../api';

const avoidOptions = ['不要太油', '不要太舔', '不要太正式', '不要长篇大论', '不要强行暧昧', '不要像客服', '不要像 AI'];

interface OnboardingWizardProps {
  presets: StylePreset[];
  onComplete: (profile: UserProfile) => void;
}

export function OnboardingWizard({ presets, onComplete }: OnboardingWizardProps) {
  const [selectedPresetIds, setSelectedPresetIds] = useState<number[]>([]);
  const [avoidPatterns, setAvoidPatterns] = useState<string[]>(['不要像 AI']);
  const [profileName, setProfileName] = useState('默认人设');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function togglePreset(id: number) {
    setSelectedPresetIds((current) => (current.includes(id) ? current.filter((item) => item !== id) : [...current, id]));
  }

  function toggleAvoidPattern(pattern: string) {
    setAvoidPatterns((current) =>
      current.includes(pattern) ? current.filter((item) => item !== pattern) : [...current, pattern],
    );
  }

  async function handleSave() {
    if (selectedPresetIds.length === 0) {
      setError('至少选择一个基础风格');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const profile = await createDefaultProfile({
        name: profileName,
        selected_preset_ids: selectedPresetIds,
        avoid_patterns: avoidPatterns,
      });
      onComplete(profile);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="panel onboarding-panel">
      <div className="section-heading">
        <h2>首次启动向导</h2>
        <span>本地保存，手动使用</span>
      </div>

      <div className="privacy-note">
        <strong>边界确认</strong>
        <p>应用只生成候选回复，不读取聊天软件、不自动发送消息。聊天记录、截图和人设默认保存在本机。</p>
      </div>

      <label className="profile-name">
        人设名称
        <input value={profileName} onChange={(event) => setProfileName(event.target.value)} />
      </label>

      <div className="preset-grid">
        {presets.map((preset) => (
          <button
            type="button"
            key={preset.id}
            className={`preset-card ${selectedPresetIds.includes(preset.id) ? 'selected' : ''}`}
            onClick={() => togglePreset(preset.id)}
          >
            <span>{preset.name}</span>
            <small>{preset.description}</small>
            <em>{preset.example_reply}</em>
          </button>
        ))}
      </div>

      <div className="avoid-list">
        {avoidOptions.map((pattern) => (
          <button
            type="button"
            key={pattern}
            className={`chip ${avoidPatterns.includes(pattern) ? 'selected' : ''}`}
            onClick={() => toggleAvoidPattern(pattern)}
          >
            {pattern}
          </button>
        ))}
      </div>

      {error ? <p className="error-text">{error}</p> : null}

      <button type="button" disabled={saving} onClick={() => void handleSave()}>
        {saving ? '保存中...' : '保存默认人设'}
      </button>
    </section>
  );
}
