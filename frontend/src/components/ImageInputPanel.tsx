import { useState } from 'react';
import { parseChatScreenshot, ParsedChatMessage, ParsedSpeaker } from '../api';

const speakerLabels: Record<ParsedSpeaker, string> = {
  me: '我',
  target: '对方',
  unknown: '未知',
};

interface ImageInputPanelProps {
  onApplyText: (chatText: string) => void;
}

function messagesToChatText(messages: ParsedChatMessage[]): string {
  return messages
    .filter((message) => message.content.trim())
    .map((message) => `${speakerLabels[message.speaker]}: ${message.content.trim()}`)
    .join('\n');
}

export function ImageInputPanel({ onApplyText }: ImageInputPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [messages, setMessages] = useState<ParsedChatMessage[]>([]);
  const [summary, setSummary] = useState('');
  const [uncertainParts, setUncertainParts] = useState<string[]>([]);
  const [promptVersion, setPromptVersion] = useState('');
  const [llmCallId, setLlmCallId] = useState<number | null>(null);
  const [status, setStatus] = useState('等待上传截图');
  const [parsing, setParsing] = useState(false);

  async function handleParse() {
    if (!file) {
      setStatus('先选择一张聊天截图');
      return;
    }
    setParsing(true);
    setStatus('正在解析截图...');
    try {
      const result = await parseChatScreenshot(file);
      setMessages(result.messages);
      setSummary(result.summary);
      setUncertainParts(result.uncertain_parts);
      setPromptVersion(result.prompt_version);
      setLlmCallId(result.llm_call_id);
      setStatus(`解析完成：${result.stored_image_path}`);
    } catch (error) {
      setStatus(error instanceof Error ? error.message : '截图解析失败');
    } finally {
      setParsing(false);
    }
  }

  function updateMessage(index: number, nextMessage: ParsedChatMessage) {
    setMessages((current) => current.map((message, messageIndex) => (messageIndex === index ? nextMessage : message)));
  }

  function handleApply() {
    const chatText = messagesToChatText(messages);
    if (!chatText) {
      setStatus('没有可写入的聊天内容');
      return;
    }
    onApplyText(chatText);
    setStatus('已写入当前聊天内容');
  }

  return (
    <div className="image-input-panel">
      <div className="section-heading compact-heading">
        <h2>截图解析</h2>
        <span>{promptVersion || 'Phase 5 Multimodal'}</span>
      </div>

      <div className="image-upload-row">
        <label>
          聊天截图
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(event) => setFile(event.target.files?.[0] || null)}
          />
        </label>
        <button type="button" disabled={parsing || !file} onClick={() => void handleParse()}>
          {parsing ? '解析中...' : '解析截图'}
        </button>
      </div>

      {messages.length > 0 ? (
        <div className="parsed-chat-box">
          <label>
            摘要
            <textarea value={summary} onChange={(event) => setSummary(event.target.value)} />
          </label>

          <div className="parsed-message-list">
            {messages.map((message, index) => (
              <div className="parsed-message" key={`${message.speaker}-${index}`}>
                <select value={message.speaker} onChange={(event) => updateMessage(index, { ...message, speaker: event.target.value as ParsedSpeaker })}>
                  <option value="me">我</option>
                  <option value="target">对方</option>
                  <option value="unknown">未知</option>
                </select>
                <input value={message.time} onChange={(event) => updateMessage(index, { ...message, time: event.target.value })} />
                <textarea value={message.content} onChange={(event) => updateMessage(index, { ...message, content: event.target.value })} />
              </div>
            ))}
          </div>

          {uncertainParts.length > 0 ? <p className="uncertain-text">不确定：{uncertainParts.join('；')}</p> : null}

          <div className="actions compact-actions">
            <button type="button" onClick={handleApply}>
              写入聊天内容
            </button>
            <button
              type="button"
              className="secondary"
              onClick={() => setMessages((current) => [...current, { speaker: 'unknown', content: '', time: 'unknown' }])}
            >
              增加一条
            </button>
          </div>
        </div>
      ) : null}

      <p className="reply-status">{llmCallId ? `${status} · LLM Call #${llmCallId}` : status}</p>
    </div>
  );
}