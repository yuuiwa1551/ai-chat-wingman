export interface TargetInsightSource {
  name?: string | null;
  relationship?: string | null;
  style_summary?: string | null;
  preferences?: string | null;
  taboos?: string | null;
  strategy_guideline?: string | null;
}

export interface TargetRule {
  label: string;
  text: string;
}

export function buildTargetRules(target: TargetInsightSource | null): TargetRule[] {
  if (!target) {
    return [
      { label: '通用', text: '未选择对象时，只按当前聊天和回复场景生成。' },
      { label: '建议', text: '新建对象后，可以把偏好、禁忌和关系状态带入回复。' },
    ];
  }

  const rules: TargetRule[] = [];
  addRule(rules, '策略', target.strategy_guideline);
  addRule(rules, '偏好', target.preferences);
  addRule(rules, '避开', target.taboos);
  addRule(rules, '语气', target.style_summary);

  if (rules.length === 0) {
    rules.push(
      { label: '对象', text: `${target.name || '这个对象'} 的档案还很少，当前只使用名称作为上下文。` },
      { label: '建议', text: '补充偏好、禁忌或回复策略后，候选会更贴近这个对象。' },
    );
  }

  return rules.slice(0, 3);
}

export function buildTargetPromptSummary(target: TargetInsightSource | null): string {
  if (!target) {
    return '未选择对象档案：不会套用对象偏好、禁忌或长期关系状态。';
  }

  const parts = [
    target.relationship ? `关系：${cleanText(target.relationship)}` : '',
    target.style_summary ? `摘要：${cleanText(target.style_summary)}` : '',
    target.preferences ? `偏好：${cleanText(target.preferences)}` : '',
    target.taboos ? `禁忌：${cleanText(target.taboos)}` : '',
    target.strategy_guideline ? `策略：${cleanText(target.strategy_guideline)}` : '',
  ].filter(Boolean);

  return parts.length ? parts.join('；') : '对象档案只有名称，回复时不会额外套用偏好或禁忌。';
}

function addRule(rules: TargetRule[], label: string, value: string | null | undefined) {
  const text = firstMeaningfulLine(value);
  if (text) {
    rules.push({ label, text });
  }
}

function firstMeaningfulLine(value: string | null | undefined): string {
  if (!value) {
    return '';
  }
  const first = value
    .split(/[\n。；;]+/)
    .map((part) => cleanText(part))
    .find(Boolean);
  return first || '';
}

function cleanText(value: string): string {
  return value.trim().replace(/\s+/g, ' ');
}
