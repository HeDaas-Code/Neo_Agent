/**
 * ProactiveMessageList - render the active (non-dismissed) proactive
 * messages as a vertical stack of ProactiveBanners. Designed to be placed
 * at the top of the chat column, just above (or in place of) the
 * MessageList header.
 *
 * The list is a pure presentation component: it never opens a WebSocket on
 * its own. Consumers are expected to wire it to ``useProactiveStream`` and
 * forward ``clearProactive``. This keeps the component trivially testable.
 */

import React, { useCallback } from 'react';
import { Empty } from 'antd';
import { ThunderboltOutlined } from '@ant-design/icons';
import type { ProactiveMessage } from '../hooks/useProactiveStream';
import { ProactiveBanner } from './ProactiveBanner';

export interface ProactiveMessageListProps {
  messages: ProactiveMessage[];
  onDismiss: (uuid: string) => void;
  onNavigate?: (relatedUuid: string, message: ProactiveMessage) => void;
  /**
   * Optional label for the header row. Set to ``false`` to hide the header
   * (e.g. when the parent already has its own visual heading).
   */
  header?: React.ReactNode | false;
  /** When true, render nothing if there are no messages. Default false. */
  hideWhenEmpty?: boolean;
  /** Optional className for the wrapper. */
  className?: string;
}

const ProactiveMessageListComponent: React.FC<ProactiveMessageListProps> = ({
  messages,
  onDismiss,
  onNavigate,
  header,
  hideWhenEmpty = false,
  className,
}) => {
  const handleDismiss = useCallback(
    (uuid: string) => {
      onDismiss(uuid);
    },
    [onDismiss]
  );

  if (messages.length === 0 && hideWhenEmpty) {
    return null;
  }

  return (
    <div
      className={`flex flex-col gap-2 ${className ?? ''}`}
      data-testid="proactive-message-list"
    >
      {header !== false ? (
        <div className="flex items-center gap-1 text-xs text-amber-700 font-medium">
          <ThunderboltOutlined />
          {header ?? (
            <span>
              主动消息
              {messages.length > 0 ? `（${messages.length}）` : ''}
            </span>
          )}
        </div>
      ) : null}
      {messages.length === 0 ? (
        <div className="px-2 py-1">
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="暂无主动消息"
            className="py-1"
          />
        </div>
      ) : (
        messages.map((m) => (
          <ProactiveBanner
            key={m.uuid}
            message={m}
            onDismiss={handleDismiss}
            onNavigate={onNavigate}
          />
        ))
      )}
    </div>
  );
};

export const ProactiveMessageList = React.memo(ProactiveMessageListComponent);
export default ProactiveMessageList;
