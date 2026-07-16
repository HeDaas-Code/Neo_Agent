/**
 * ChatInput - auto-resizing textarea with send button.
 *
 * 快捷键:
 *  - Enter: 发送
 *  - Shift+Enter: 换行
 *  - Ctrl/⌘ + Enter: 发送(与 Enter 等价,便于多行输入场景)
 *  - Disabled while sending
 */

import React, { useCallback, useRef, useState } from 'react';
import { Input, Button, Tooltip } from 'antd';
import { SendOutlined, LoadingOutlined } from '@ant-design/icons';

export interface ChatInputProps {
  onSend: (text: string) => void;
  disabled?: boolean;
  placeholder?: string;
  /** Maximum rows the textarea will auto-grow to. */
  maxRows?: number;
}

const ChatInputComponent: React.FC<ChatInputProps> = ({
  onSend,
  disabled = false,
  placeholder = '按 Ctrl/⌘ + Enter 发送,Enter 发送,Shift+Enter 换行',
  maxRows = 6,
}) => {
  const [value, setValue] = useState<string>('');
  const taRef = useRef<any>(null);

  const submit = useCallback(() => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
    // refocus after sending
    requestAnimationFrame(() => {
      try {
        taRef.current?.focus?.();
      } catch {
        // ignore
      }
    });
  }, [value, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      // Ctrl/⌘ + Enter 发送
      if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        submit();
        return;
      }
      // Enter 直接发送(无 Shift)
      if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) {
        e.preventDefault();
        submit();
      }
    },
    [submit]
  );

  return (
    <div className="flex items-end gap-2 p-3 border-t border-gray-200 bg-white">
      <Input.TextArea
        ref={taRef as any}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        autoSize={{ minRows: 1, maxRows }}
        placeholder={placeholder}
        disabled={disabled}
        className="flex-1"
      />
      <Tooltip title={disabled ? '正在发送…' : '发送 (Ctrl/⌘+Enter)'}>
        <Button
          type="primary"
          icon={disabled ? <LoadingOutlined /> : <SendOutlined />}
          onClick={submit}
          disabled={disabled || value.trim().length === 0}
        >
          发送
        </Button>
      </Tooltip>
    </div>
  );
};

export const ChatInput = React.memo(ChatInputComponent);
export default ChatInput;
