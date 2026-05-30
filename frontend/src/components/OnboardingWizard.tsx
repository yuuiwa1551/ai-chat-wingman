import { useState } from 'react';
import { createDefaultProfile } from '../api';
import type { ChatTarget, StylePreset, UserProfile } from '../api';
import { QQImportPanel } from './QQImportPanel';
import { StyleTestPanel } from './StyleTestPanel';

const avoidOptions = ['不要太油', '不要太舔', '不要太正式', '不要长篇大论', '不要强行暧昧', '不要像客服', '不要像 AI'];

type OnboardingStep = 'choice' | 'json-import' | 'style-test' | 'preset-profile';

interface OnboardingWizardProps {
  presets: StylePreset[];
  targets?: ChatTarget[];
  onTargetImported?: (target: ChatTarget) => void;
  onComplete: (profile: UserProfile) => void;
}

export function OnboardingWizard({ presets, targets = [], onTargetImported, onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState<OnboardingStep>('choice');
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

  async function saveProfile(nextPresetIds: number[], nextProfileName = profileName) {
    if (nextPresetIds.length === 0) {
      setError('至少需要一个基础风格预设。若正在加载，请稍后再试。');
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const profile = await createDefaultProfile({
        name: nextProfileName,
        selected_preset_ids: nextPresetIds,
        avoid_patterns: avoidPatterns,
      });
      onComplete(profile);
    } catch (nextError) {
      setError(nextError instanceof Error ? nextError.message : '保存失败');
    } finally {
      setSaving(false);
    }
  }

  async function handleSave() {
    await saveProfile(selectedPresetIds);
  }

  async function handleSkip() {
    if (!presets[0]) {
      setError('风格预设还没有加载完成，暂时不能跳过校准。');
      return;
    }
    await saveProfile([presets[0].id], '默认人设');
  }

  if (step === 'json-import') {
    return (
      <main className="onboarding-shell">
        <OnboardingSide currentStep="导入聊天记录" />
        <section className="onboarding-content">
          <button type="button" className="secondary compact-button" onClick={() => setStep('choice')}>
            返回
          </button>
          <QQImportPanel
            targets={targets}
            onTargetImported={(target) => onTargetImported?.(target)}
            onImportComplete={(result) => onComplete(result.profile)}
          />
        </section>
      </main>
    );
  }

  if (step === 'style-test') {
    return (
      <main className="onboarding-shell">
        <OnboardingSide currentStep="模拟聊天校准" />
        <section className="onboarding-content">
          <button type="button" className="secondary compact-button" onClick={() => setStep('choice')}>
            返回
          </button>
          <StyleTestPanel onProfileSaved={onComplete} />
        </section>
      </main>
    );
  }

  if (step === 'preset-profile') {
    return (
      <main className="onboarding-shell">
        <OnboardingSide currentStep="基础风格" />
        <section className="onboarding-content">
          <div className="onboarding-header">
            <button type="button" className="secondary compact-button" onClick={() => setStep('choice')}>
              返回
            </button>
            <div>
              <h1>选择一个接近你的聊天底色</h1>
              <p>后续可以通过模拟聊天和历史记录继续校准，不需要一开始就完全准确。</p>
            </div>
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
      </main>
    );
  }

  return (
    <main className="onboarding-shell">
      <OnboardingSide currentStep="导入或校准" />
      <section className="onboarding-content">
        <div className="onboarding-header">
          <div>
            <h1>开始前，先选择校准方式</h1>
            <p>导入或校准用于让回复更贴近你的真实说话风格。也可以跳过，之后在设置里再补。</p>
          </div>
        </div>

        <div className="onboarding-choice-grid">
          <button type="button" className="onboarding-choice-card primary" onClick={() => setStep('json-import')}>
            <span>JSON</span>
            <strong>导入聊天 JSON</strong>
            <small>适合已有 QQ JSON 或其他导出记录。AI 系统会识别哪一方是你，再提炼你的风格和对象档案。</small>
            <em className="choice-action">选择文件</em>
          </button>

          <button type="button" className="onboarding-choice-card" onClick={() => setStep('style-test')}>
            <span>聊</span>
            <strong>通过模拟聊天校准</strong>
            <small>没有导出记录也可以通过几轮自然对话校准。只分析句子长短、共情、主动程度和禁区。</small>
            <em className="choice-action secondary-action">开始模拟</em>
          </button>
        </div>

        <div className="onboarding-note">
          <strong>隐私说明</strong>
          <p>导入文件只保存在本机用户数据目录。只有调用 LLM 时，必要上下文才会发给你配置的 provider。</p>
        </div>

        <div className="onboarding-actions">
          <button type="button" className="secondary" disabled={saving} onClick={() => void handleSkip()}>
            Skip
          </button>
          <span>跳过校准，直接进入主界面，后续可重新校准。</span>
        </div>

        {error ? <p className="error-text">{error}</p> : null}
      </section>
    </main>
  );
}

interface OnboardingSideProps {
  currentStep: string;
}

function OnboardingSide({ currentStep }: OnboardingSideProps) {
  return (
    <aside className="onboarding-side">
      <h2>首次使用</h2>
      <p>先选择是否导入或校准。认清边界后可以直接开始。</p>
      <ol>
        <li className="active">
          <span>1</span>
          <strong>{currentStep}</strong>
        </li>
        <li>
          <span>2</span>
          <strong>确认表达风格</strong>
        </li>
        <li>
          <span>3</span>
          <strong>进入主工作台</strong>
        </li>
      </ol>
      <div className="privacy-note compact">
        <strong>边界确认</strong>
        <p>不会自动读取聊天软件，不会自动发送消息。聊天记录、截图和人设默认保存在本机。</p>
      </div>
    </aside>
  );
}
