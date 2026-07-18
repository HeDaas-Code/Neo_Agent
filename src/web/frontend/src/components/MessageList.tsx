/**
 * MessageList - 虚拟滚动消息列表
 *
 * Stage B.1 升级:
 *  - 使用 react-window FixedSizeList 渲染,可承载 1000+ 条消息而不卡顿
 *  - 保留所有原 props 接口(messages / renderItem / renderMarkdown / autoScroll /
 *    className / emptyText),确保调用方零侵入
 *  - 通过 ResizeObserver 自动测量容器高度
 *  - 自动滚动到底部:autoScroll=true 时,新消息或最后一条消息变化时,RAF 内
 *    调用 listRef.scrollToItem(messages.length - 1)
 *  - 消息行高 80px(由 ChatBubble 内容决定,溢出由 ChatBubble 内部处理)
 */

import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Empty } from 'antd';
import { FixedSizeList, ListChildComponentProps } from 'react-window';
import type { ChatMessage } from '../hooks/useChatStream';
import { ChatBubble, ChatBubbleProps } from './ChatBubble';

export interface MessageListProps {
  messages: ChatMessage[];
  /** Optional custom renderer; defaults to ChatBubble */
  renderItem?: (message: ChatMessage) => React.ReactNode;
  /** Optional markdown render fn passed through to ChatBubble */
  renderMarkdown?: ChatBubbleProps['renderMarkdown'];
  /** Auto-scroll to bottom on new messages; default true */
  autoScroll?: boolean;
  /** Optional className for the scroll container */
  className?: string;
  /** Placeholder shown when messages is empty */
  emptyText?: string;
  /** 单条消息行高(px),默认 80。ChatBubble 高度可能大于该值时由 ChatBubble 内部滚动 */
  itemSize?: number;
}

const DEFAULT_ITEM_SIZE = 80;

const MessageListComponent: React.FC<MessageListProps> = ({
  messages,
  renderItem,
  renderMarkdown,
  autoScroll = true,
  className,
  emptyText = '还没有对话，开始聊点什么吧…',
  itemSize = DEFAULT_ITEM_SIZE,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const listRef = useRef<FixedSizeList>(null);
  const prevCountRef = useRef<number>(messages.length);
  const prevLastIdRef = useRef<string | null>(null);

  // 用 ResizeObserver 动态获取容器高度,作为 FixedSizeList 的 height
  const [containerHeight, setContainerHeight] = useState<number>(400);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    // 初始化一次
    setContainerHeight(el.clientHeight || 400);
    if (typeof ResizeObserver === 'undefined') {
      // 兜底:监听 window resize
      const handler = () => setContainerHeight(el.clientHeight || 400);
      window.addEventListener('resize', handler);
      return () => window.removeEventListener('resize', handler);
    }
    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const h = entry.contentRect.height;
        if (h > 0) setContainerHeight(h);
      }
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Determine the id of the last message (for "follow streaming" behaviour).
  const lastId = useMemo(() => {
    if (messages.length === 0) return null;
    return messages[messages.length - 1].id;
  }, [messages]);

  // 自动滚动到底部:仅在消息数量变化或最后一条消息 id 变化时触发
  useEffect(() => {
    if (!autoScroll) return;
    if (messages.length === 0) return;
    const isNewMessage = messages.length !== prevCountRef.current;
    const isLastChanged = lastId !== prevLastIdRef.current;
    if (isNewMessage || isLastChanged) {
      // 下一帧让 DOM 先行渲染,再滚到末尾
      requestAnimationFrame(() => {
        try {
          listRef.current?.scrollToItem(messages.length - 1, 'end');
        } catch {
          /* 忽略 scrollToItem 边界异常 */
        }
      });
    }
    prevCountRef.current = messages.length;
    prevLastIdRef.current = lastId;
  }, [messages.length, lastId, autoScroll, messages]);

  if (messages.length === 0) {
    return (
      <div
        ref={containerRef}
        className={`h-full flex items-center justify-center ${className ?? ''}`}
      >
        <Empty description={emptyText} />
      </div>
    );
  }

  // react-window 行渲染器:每行用 ChatBubble 渲染当前消息
  const Row: React.FC<ListChildComponentProps> = ({ index, style }) => {
    const msg = messages[index];
    return (
      <div style={style}>
        {renderItem ? (
          renderItem(msg)
        ) : (
          <ChatBubble message={msg} renderMarkdown={renderMarkdown} />
        )}
      </div>
    );
  };

  return (
    <div
      ref={containerRef}
      className={`h-full w-full ${className ?? ''}`}
    >
      <FixedSizeList
        ref={listRef}
        height={containerHeight}
        width="100%"
        itemCount={messages.length}
        itemSize={itemSize}
        overscanCount={4}
      >
        {Row}
      </FixedSizeList>
    </div>
  );
};

export const MessageList = React.memo(MessageListComponent);
export default MessageList;
