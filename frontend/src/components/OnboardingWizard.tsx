import { useState } from 'react';
import type { ReactNode } from 'react';
import type { ChatTarget, QQImportResult, StylePreset, UserProfile } from '../api';
import { QQImportPanel } from './QQImportPanel';

type OnboardingStep = 'provider' | 'json-import';

interface OnboardingWizardProps {
  presets: StylePreset[];
  targets?: ChatTarget[];
  providerSettings: ReactNode;
  providerReady: boolean;
  providerStatus: string;
  onTargetImported?: (target: ChatTarget) => void;
  onComplete: (profile: UserProfile) => void;
}

export function OnboardingWizard({
  presets,
  targets = [],
  providerSettings,
  providerReady,
  providerStatus,
  onTargetImported,
  onComplete,
}: OnboardingWizardProps) {
  const [step, setStep] = useState<OnboardingStep>('provider');

  if (step === 'json-import') {
    return (
      <main className="onboarding-shell">
        <OnboardingSide currentStep="导入聊天记录" step="json-import" />
        <section className="onboarding-content">
          <div className="onboarding-header">
            <button type="button" className="secondary compact-button" onClick={() => setStep('provider')}>
              返回模型配置
            </button>
            <div>
              <h1>导入聊天记录后才能进入主工作台</h1>
              <p>导入会生成默认表达风格和对象档案。当前版本不提供跳过入口，避免在没有上下文的情况下生成低质量回复。</p>
            </div>
          </div>
          <QQImportPanel
            targets={targets}
            onTargetImported={(target) => onTargetImported?.(target)}
            onImportComplete={(result: QQImportResult) => onComplete(result.profile)}
          />
        </section>
      </main>
    );
  }

  return (
    <main className="onboarding-shell">
      <OnboardingSide currentStep="连接真实模型" step="provider" />
      <section className="onboarding-content">
        <div className="onboarding-header">
          <div>
            <h1>先连接你的模型 Provider</h1>
            <p>
              首次使用需要填写 API URL、API Key 和模型名，并通过连通测试。导入聊天记录和后续回复都会走你本地保存的 Provider 配置。
            </p>
          </div>
        </div>

        <div className="onboarding-note">
          <strong>为什么这一步放在最前面</strong>
          <p>
            没有真实 Provider 时只能跑 Mock 流程，无法判断回复质量。API Key 只保存到本机设置或环境变量，不写进仓库。
          </p>
        </div>

        <div className="onboarding-provider-panel">{providerSettings}</div>

        <div className="onboarding-actions locked">
          <button type="button" disabled={!providerReady} onClick={() => setStep('json-import')}>
            进入导入
          </button>
          <span>{providerReady ? '连通测试已通过，可以导入聊天记录。' : providerStatus || '请先保存配置并测试连通。'}</span>
        </div>

        {presets.length === 0 ? <p className="error-text">风格预设尚未加载完成，但当前流程会优先使用导入记录生成默认人设。</p> : null}
      </section>
    </main>
  );
}

interface OnboardingSideProps {
  currentStep: string;
  step: OnboardingStep;
}

function OnboardingSide({ currentStep, step }: OnboardingSideProps) {
  return (
    <aside className="onboarding-side">
      <h2>首次使用</h2>
      <p>先接入真实模型，再导入聊天记录。完成这两步后才进入主工作台。</p>
      <ol>
        <li className={step === 'provider' ? 'active' : 'done'}>
          <span>1</span>
          <strong>连接 Provider</strong>
        </li>
        <li className={step === 'json-import' ? 'active' : ''}>
          <span>2</span>
          <strong>{currentStep === '导入聊天记录' ? currentStep : '导入聊天记录'}</strong>
        </li>
        <li>
          <span>3</span>
          <strong>进入主工作台</strong>
        </li>
      </ol>
      <div className="privacy-note compact">
        <strong>边界确认</strong>
        <p>不会自动读取聊天软件，不会自动发送消息。导入文件、截图和数据库默认保存在本机。</p>
      </div>
    </aside>
  );
}
