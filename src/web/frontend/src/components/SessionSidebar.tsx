/**
 * SessionSidebar - 左侧会话抽屉 - v3.1.0
 * ======================================
 *
 * - Antd Drawer (placement="left", width=320) 弹出
 * - 顶部 "+ 新建会话" 按钮
 * - 列表项: title + 描述 ("N 条 · 相对时间") + hover 删除按钮
 * - 当前 session 用 type="primary" 背景高亮
 * - open === true 时调 listSessions 拉取
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import {
  Drawer,
  Button,
  List,
  Popconfirm,
  Empty,
  message,
  Spin,
  Tag,
  Tooltip,
} from 'antd';
import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  listSessions,
  createSession,
  deleteSession,
  type ChatSession,
} from '../api/chatSessions';

export interface SessionSidebarProps {
  open: boolean;
  onClose: () => void;
  currentSessionId: number | null;
  onSelect: (id: number) => void;
  onCreated: (id: number) => void;
  onDeleted: (id: number) => void;
  userId?: string;
}

/** 把 epoch seconds 转为 "刚刚/N 分钟前/N 小时前/N 天前" 相对时间 */
function relativeTime(updatedAt: number): string {
  if (!updatedAt) return '刚刚';
  const now = Date.now() / 1000;
  const diff = Math.max(0, now - updatedAt);
  if (diff < 60) return '刚刚';
  if (diff < 3600) return `${Math.floor(diff / 60)} 分钟前`;
  if (diff < 86400) return `${Math.floor(diff / 3600)} 小时前`;
  if (diff < 86400 * 30) return `${Math.floor(diff / 86400)} 天前`;
  return new Date(updatedAt * 1000).toLocaleDateString();
}

export default function SessionSidebar(props: SessionSidebarProps) {
  const {
    open,
    onClose,
    currentSessionId,
    onSelect,
    onCreated,
    onDeleted,
    userId = 'default',
  } = props;

  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [creating, setCreating] = useState<boolean>(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const result = await listSessions(userId, 50, 0);
      setSessions(result.items || []);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[SessionSidebar] listSessions failed', err);
      message.error(`加载会话列表失败: ${(err as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [userId]);

  // 抽屉打开时刷新
  useEffect(() => {
    if (open) {
      void refresh();
    }
  }, [open, refresh]);

  const handleCreate = useCallback(async () => {
    setCreating(true);
    try {
      const session = await createSession(userId, '新会话');
      message.success('已创建新会话');
      onCreated(session.id);
      // 立即插入到列表头部并刷新
      setSessions((prev) => [session, ...prev.filter((s) => s.id !== session.id)]);
    } catch (err) {
      message.error(`创建会话失败: ${(err as Error).message}`);
    } finally {
      setCreating(false);
    }
  }, [userId, onCreated]);

  const handleDelete = useCallback(
    async (session: ChatSession) => {
      try {
        await deleteSession(session.id);
        message.success('已删除会话');
        setSessions((prev) => prev.filter((s) => s.id !== session.id));
        onDeleted(session.id);
      } catch (err) {
        message.error(`删除失败: ${(err as Error).message}`);
      }
    },
    [onDeleted],
  );

  const handleSelect = useCallback(
    (session: ChatSession) => {
      onSelect(session.id);
    },
    [onSelect],
  );

  const renderItem = useCallback(
    (item: ChatSession) => {
      const active = item.id === currentSessionId;
      return (
        <List.Item
          key={item.id}
          className={`!px-3 !py-2 cursor-pointer rounded transition-colors ${
            active ? 'bg-blue-500/10 border-l-4 border-blue-500' : 'hover:bg-gray-100'
          }`}
          onClick={() => handleSelect(item)}
          actions={[
            <Popconfirm
              key="del"
              title="删除该会话？"
              description="将永久删除该会话及其所有消息，无法恢复。"
              okText="删除"
              cancelText="取消"
              okButtonProps={{ danger: true }}
              onConfirm={(e) => {
                e?.stopPropagation();
                void handleDelete(item);
              }}
              onCancel={(e) => {
                e?.stopPropagation();
              }}
            >
              <Button
                type="text"
                size="small"
                danger
                icon={<DeleteOutlined />}
                onClick={(e) => e.stopPropagation()}
                aria-label="删除会话"
              />
            </Popconfirm>,
          ]}
        >
          <List.Item.Meta
            avatar={
              <MessageOutlined
                style={{ color: active ? '#1677ff' : '#999', fontSize: 16 }}
              />
            }
            title={
              <div className="flex items-center gap-2">
                <span
                  className={`truncate ${active ? 'font-semibold text-blue-600' : ''}`}
                  title={item.title}
                >
                  {item.title || '新会话'}
                </span>
                {active ? <Tag color="processing" className="!text-xs">当前</Tag> : null}
              </div>
            }
            description={
              <span className="text-xs text-gray-500">
                {item.message_count ?? 0} 条 · {relativeTime(item.updated_at)}
              </span>
            }
          />
        </List.Item>
      );
    },
    [currentSessionId, handleSelect, handleDelete],
  );

  const headerNode = useMemo(
    () => (
      <div className="flex items-center justify-between">
        <span className="font-semibold">会话列表</span>
        <Tooltip title="刷新">
          <Button
            type="text"
            size="small"
            icon={<ReloadOutlined />}
            onClick={() => void refresh()}
            loading={loading}
          />
        </Tooltip>
      </div>
    ),
    [loading, refresh],
  );

  return (
    <Drawer
      title={headerNode}
      placement="left"
      width={320}
      open={open}
      onClose={onClose}
      destroyOnClose={false}
      styles={{ body: { padding: 0 } }}
    >
      <div className="flex flex-col h-full">
        <div className="p-3 border-b border-gray-100">
          <Button
            type="primary"
            block
            icon={<PlusOutlined />}
            onClick={handleCreate}
            loading={creating}
          >
            新建会话
          </Button>
        </div>
        <div className="flex-1 overflow-y-auto p-2">
          {loading && sessions.length === 0 ? (
            <div className="flex items-center justify-center py-8">
              <Spin />
            </div>
          ) : sessions.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="暂无会话"
              className="py-8"
            />
          ) : (
            <List
              dataSource={sessions}
              renderItem={renderItem}
              size="small"
              split={false}
            />
          )}
        </div>
      </div>
    </Drawer>
  );
}
