/**
 * ChatBubble - visual representation of a single chat message.
 *
 * - user: right-aligned, blue background
 * - assistant: left-aligned, white background, markdown rendered
 * - system: centered, gray
 *
 * Streaming assistant messages show a blinking caret at the end.
 */

import React, { useMemo } from 'react';
import { Typography } from 'antd';
import type { ChatMessage } from '../hooks/useChatStream';

const { Text } = Typography;

export interface ChatBubbleProps {
  message: ChatMessage;
  /** Optional render function for markdown; defaults to a simple per-line renderer */
  renderMarkdown?: (content: string) => React.ReactNode;
}

function formatRelativeTime(iso: string): string {
  try {
    const then = new Date(iso).getTime();
    if (Number.isNaN(then)) return '';
    const diff = Date.now() - then;
    if (diff < 0) return '刚刚';
    const sec = Math.floor(diff / 1000);
    if (sec < 10) return '刚刚';
    if (sec < 60) return `${sec}秒前`;
    const min = Math.floor(sec / 60);
    if (min < 60) return `${min}分钟前`;
    const hr = Math.floor(min / 60);
    if (hr < 24) return `${hr}小时前`;
    const day = Math.floor(hr / 24);
    if (day < 30) return `${day}天前`;
    return new Date(iso).toLocaleDateString();
  } catch {
    return '';
  }
}

function defaultMarkdown(content: string): React.ReactNode {
  // Lightweight renderer: split by newlines, keep it simple.
  return content.split('\n').map((line, idx) => (
    <React.Fragment key={idx}>
      {line}
      {idx < content.split('\n').length - 1 ? <br /> : null}
    </React.Fragment>
  ));
}

const baseBubble =
  'inline-block max-w-[80%] px-3 py-2 rounded-lg shadow-sm break-words whitespace-pre-wrap leading-relaxed text-sm';

const stylesByRole: Record<ChatMessage['role'], { wrap: string; bubble: string; text: string; align: string; }> = {
  user: {
    wrap: 'flex justify-end',
    bubble: `${baseBubble} bg-blue-500 text-white rounded-tr-sm`,
    text: 'text-white',
    align: 'items-end',
  },
  assistant: {
    wrap: 'flex justify-start',
    bubble: `${baseBubble} bg-white text-gray-800 border border-gray-200 rounded-tl-sm`,
    text: 'text-gray-800',
    align: 'items-start',
  },
  system: {
    wrap: 'flex justify-center',
    bubble: `${baseBubble} bg-gray-100 text-gray-500 italic rounded-full px-4 py-1 text-xs`,
    text: 'text-gray-500',
    align: 'items-center',
  },
};

const ChatBubbleComponent: React.FC<ChatBubbleProps> = ({ message, renderMarkdown }) => {
  const { role, content, timestamp, done } = message;
  const style = stylesByRole[role] ?? stylesByRole.system;
  const isStreaming = role === 'assistant' && done === false;

  const renderedContent = useMemo(() => {
    if (role === 'system') return content;
    const fn = renderMarkdown ?? defaultMarkdown;
    return fn(content);
  }, [role, content, renderMarkdown]);

  if (role === 'system') {
    return (
      <div className={style.wrap}>
        <div className="flex flex-col items-center gap-1 my-2">
          <div className={style.bubble}>
            <span className={style.text}>{content}</span>
          </div>
          {timestamp ? (
            <Text type="secondary" className="text-xs">
              {formatRelativeTime(timestamp)}
            </Text>
          ) : null}
        </div>
      </div>
    );
  }

  return (
    <div className={`${style.wrap} ${style.align} gap-2 my-2`}>
      <div className="flex flex-col max-w-[80%]">
        <div className={style.bubble}>
          <div className={style.text}>{renderedContent}</div>
          {isStreaming ? (
            <span className="inline-block ml-0.5 animate-pulse text-blue-400">▍</span>
          ) : null}
        </div>
        {timestamp ? (
          <Text
            type="secondary"
            className={`text-xs mt-1 ${role === 'user' ? 'text-right' : 'text-left'}`}
          >
            {formatRelativeTime(timestamp)}
          </Text>
        ) : null}
      </div>
    </div>
  );
};

export const ChatBubble = React.memo(ChatBubbleComponent);
export default ChatBubble;
