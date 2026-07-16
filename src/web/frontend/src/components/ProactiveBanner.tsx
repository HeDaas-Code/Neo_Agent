/**
 * ProactiveBanner - sticky banner shown for a single proactive message.
 *
 * Visual spec (Stage D.2.3):
 *   - Top-edge sticker style
 *   - Light yellow background, soft border
 *   - Left: bell icon + reason tag
 *   - Center: content (multiline friendly)
 *   - Right: relative timestamp + close button
 *   - Clicking the body (outside the close button) navigates to context
 *     when ``message.related_uuid`` is present. If the host page doesn't
 *     supply an onNavigate callback, the click is a no-op.
 */

import React, { useCallback, useMemo } from 'react';
import { Tooltip, Typography } from 'antd';
import { BellOutlined, CloseOutlined, LinkOutlined } from '@ant-design/icons';
import type { ProactiveMessage } from '../hooks/useProactiveStream';

const { Text } = Typography;

export interface ProactiveBannerProps {
  message: ProactiveMessage;
  onDismiss: (uuid: string) => void;
  /**
   * Optional navigation handler triggered when the body is clicked AND
   * ``message.related_uuid`` is set. If omitted, the body click is a no-op.
   */
  onNavigate?: (relatedUuid: string, message: ProactiveMessage) => void;
  /**
   * Override the relative-time formatter. Defaults to a small client-side
   * helper that mirrors ChatBubble's behavior.
   */
  formatTime?: (iso: string) => string;
}

const REASON_LABEL_CN: Record<string, string> = {
  habit_care: '习惯关怀',
  open_loop_recall: '未完话题',
  creative_share: '创作分享',
  weather_note: '天气提醒',
};

const PRIORITY_COLOR: Record<string, string> = {
  high: 'red',
  normal: 'blue',
  low: 'default',
};

function defaultFormatTime(iso: string): string {
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

const ProactiveBannerComponent: React.FC<ProactiveBannerProps> = ({
  message,
  onDismiss,
  onNavigate,
  formatTime,
}) => {
  const handleDismiss = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation();
      onDismiss(message.uuid);
    },
    [onDismiss, message.uuid]
  );

  const handleBodyClick = useCallback(() => {
    if (message.related_uuid && onNavigate) {
      onNavigate(message.related_uuid, message);
    }
  }, [message, onNavigate]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleBodyClick();
      }
    },
    [handleBodyClick]
  );

  const reasonLabel = useMemo(() => {
    if (!message.reason) return '主动消息';
    return REASON_LABEL_CN[message.reason] ?? message.reason;
  }, [message.reason]);

  const timeText = (formatTime ?? defaultFormatTime)(message.timestamp);
  const priorityColor =
    PRIORITY_COLOR[message.priority] ?? PRIORITY_COLOR.normal;
  const canNavigate = Boolean(message.related_uuid && onNavigate);

  return (
    <div
      role={canNavigate ? 'button' : undefined}
      tabIndex={canNavigate ? 0 : undefined}
      onClick={canNavigate ? handleBodyClick : undefined}
      onKeyDown={canNavigate ? handleKeyDown : undefined}
      className={[
        'flex items-start gap-3 px-4 py-2 border border-amber-200',
        'bg-amber-50 text-amber-900 rounded-md shadow-sm',
        canNavigate ? 'cursor-pointer hover:bg-amber-100' : '',
      ].join(' ')}
      data-testid="proactive-banner"
      data-uuid={message.uuid}
    >
      <div className="flex-shrink-0 mt-0.5 text-amber-500">
        <BellOutlined style={{ fontSize: 18 }} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <Text strong className="text-sm text-amber-700">
            {reasonLabel}
          </Text>
          <Text type="warning" className="text-xs">
            {priorityColor === 'red'
              ? '高优先级'
              : priorityColor === 'default'
                ? '低优先级'
                : '普通'}
          </Text>
          {canNavigate ? (
            <Tooltip title="点击跳转到相关上下文">
              <LinkOutlined className="text-amber-500" />
            </Tooltip>
          ) : null}
        </div>
        <div className="mt-0.5 text-sm text-amber-900 whitespace-pre-wrap break-words">
          {message.content}
        </div>
      </div>
      <div className="flex-shrink-0 flex flex-col items-end gap-1">
        {timeText ? (
          <Text type="secondary" className="text-xs">
            {timeText}
          </Text>
        ) : null}
        <Tooltip title="关闭此条主动消息">
          <button
            type="button"
            aria-label="dismiss proactive message"
            onClick={handleDismiss}
            className="text-amber-500 hover:text-amber-700 hover:bg-amber-200/60 rounded p-1 leading-none"
          >
            <CloseOutlined style={{ fontSize: 14 }} />
          </button>
        </Tooltip>
      </div>
    </div>
  );
};

export const ProactiveBanner = React.memo(ProactiveBannerComponent);
export default ProactiveBanner;
