/**
 * Chat page - main conversation view.
 *
 * Layout: left column 70% (toolbar + ProactiveMessageList + MessageList +
 * ChatInput) + right column 30% (EmotionPanel + TimelineCanvas 真挂载).
 *
 * Stage B.1.7: connected to the real /ws/chat backend.
 *  - Errors from the server or transport surface as a red bar above the
 *    message list with a "重试" button that re-sends the most recent user
 *    input. A small "心跳" tag in the toolbar indicates the health of the
 *    ping/pong heartbeat.
 *
 * Stage B.3 / B.4 真接入:
 *  - EmotionPanel 真实挂载:useEffect 拉 `GET /api/emotion/latest`,把响应的
 *    `plutchik` → `data`,`historical_max` → `historicalMax` 传入。失败时
 *    EmotionPanel 内部走骨架屏,不阻塞聊天。
 *  - TimelineCanvas 真实挂载:useEffect 拉 `GET /api/memory/timeline?days=7`,
 *    把响应 `nodes` 映射为 TopicNode(`uuid` → `id`,`topic` → `title`,
 *    `mention_count` → `mentionCount`,`category` → `category`),然后传入
 *    TimelineCanvas。失败/空响应下 TimelineCanvas 走骨架屏。
 *
 * Stage D.2.3: integrate proactive messages.
 *  - useProactiveStream subscribes to /ws/proactive.
 *  - ProactiveMessageList shows active (non-dismissed) banners above the
 *    regular message list.
 *  - When a new proactive message arrives, play a short 440Hz ding if the
 *    user has not disabled the sound (persisted to localStorage as
 *    ``enable_proactive_sound``).
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  App,
  Space,
  Button,
  Tooltip,
  Badge,
  Modal,
  Statistic,
  Row,
  Col,
  Tag,
  Switch,
  Alert,
} from 'antd';
import {
  ClearOutlined,
  BarChartOutlined,
  ReloadOutlined,
  SoundOutlined,
  SoundFilled,
  WarningOutlined,
  SyncOutlined,
  FolderOpenOutlined,
} from '@ant-design/icons';
import { useChatStream } from '../../hooks/useChatStream';
import { useProactiveStream, ProactiveMessage } from '../../hooks/useProactiveStream';
import MessageList from '../../components/MessageList';
import ChatInput from '../../components/ChatInput';
import ProactiveMessageList from '../../components/ProactiveMessageList';
import EmotionPanel, { EmotionData } from '../../components/EmotionPanel';
import TimelineCanvas, { TopicNode } from '../../components/TimelineCanvas';
import SessionSidebar from '../../components/SessionSidebar';
import {
  playProactiveDing,
  unlockProactiveAudio,
} from '../../utils/proactiveSound';

const CURRENT_SESSION_STORAGE_KEY = 'current_session_id';

const statusToBadge: Record<string, { status: any; text: string }> = {
  connecting: { status: 'processing', text: '连接中' },
  open: { status: 'success', text: '在线' },
  closed: { status: 'default', text: '未连接' },
  error: { status: 'error', text: '连接异常' },
};

const SOUND_STORAGE_KEY = 'enable_proactive_sound';

function readSoundPreference(): boolean {
  if (typeof window === 'undefined') return true;
  try {
    const raw = window.localStorage.getItem(SOUND_STORAGE_KEY);
    if (raw === null) return true; // default ON
    return raw === '1' || raw === 'true';
  } catch {
    return true;
  }
}

function writeSoundPreference(enabled: boolean): void {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(SOUND_STORAGE_KEY, enabled ? '1' : '0');
  } catch {
    /* ignore quota / private mode */
  }
}

// ============= 数据规整辅助函数 =============

/** 8 维情感默认值(全 0),用于 API 失败/字段缺失的兜底 */
const EMPTY_EMOTION: EmotionData = {
  joy: 0,
  trust: 0,
  fear: 0,
  surprise: 0,
  sadness: 0,
  disgust: 0,
  anger: 0,
  anticipation: 0,
};

/** 把后端 plutchik 字典规整为 EmotionData(任何字段缺失都用 0 兜底) */
function coerceEmotionData(raw: unknown): EmotionData {
  if (!raw || typeof raw !== 'object') return EMPTY_EMOTION;
  const r = raw as Record<string, unknown>;
  return {
    joy: Number(r.joy) || 0,
    trust: Number(r.trust) || 0,
    fear: Number(r.fear) || 0,
    surprise: Number(r.surprise) || 0,
    sadness: Number(r.sadness) || 0,
    disgust: Number(r.disgust) || 0,
    anger: Number(r.anger) || 0,
    anticipation: Number(r.anticipation) || 0,
  };
}

/** 把后端 timeline 节点数组映射为 TimelineCanvas 所需的 TopicNode */
function coerceTimelineNodes(raw: unknown): TopicNode[] {
  if (!Array.isArray(raw)) return [];
  const result: TopicNode[] = [];
  for (const item of raw) {
    if (!item || typeof item !== 'object') continue;
    const r = item as Record<string, unknown>;
    const id = String(r.uuid ?? r.id ?? '').trim();
    if (!id) continue;
    const title = String(r.topic ?? r.title ?? '未命名话题');
    const category = String(r.category ?? '其他');
    const date = String(r.date ?? '');
    const mentionCount = Number(r.mention_count ?? r.mentionCount ?? 0) || 0;
    result.push({ id, title, category, date, mentionCount });
  }
  return result;
}

export default function ChatPage() {
  const {
    messages,
    status,
    connId,
    sessionId,
    sendMessage,
    retryLast,
    clearMessages,
    clearError,
    isStreaming,
    error,
    lastPongAt,
    switchSession,
  } = useChatStream({
    welcomeMessage: '欢迎使用 Neo Agent 聊天助手，向我发送消息开始对话吧。',
  });

  const [sidebarOpen, setSidebarOpen] = useState<boolean>(false);

  // Stage 3.4.2: mount 时检查 localStorage `current_session_id`,有则自动恢复
  useEffect(() => {
    if (typeof window === 'undefined') return;
    try {
      const raw = window.localStorage.getItem(CURRENT_SESSION_STORAGE_KEY);
      if (raw && raw.length > 0) {
        const id = Number(raw);
        if (Number.isFinite(id) && id > 0) {
          void switchSession(id);
        }
      }
    } catch {
      /* ignore */
    }
  // switchSession is stable across renders; run only on mount.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Stage D.2.3: subscribe to /ws/proactive.
  const [soundEnabled, setSoundEnabled] = useState<boolean>(() => readSoundPreference());
  const { message: appMessage } = App.useApp();

  // First-interaction unlock for Web Audio. Modern browsers require a user
  // gesture before audio plays; we hook the first click/keydown anywhere in
  // the page to call resume() on the shared AudioContext. Idempotent.
  useEffect(() => {
    if (typeof window === 'undefined') return;
    const handler = () => {
      unlockProactiveAudio();
      window.removeEventListener('pointerdown', handler);
      window.removeEventListener('keydown', handler);
    };
    window.addEventListener('pointerdown', handler, { once: true });
    window.addEventListener('keydown', handler, { once: true });
    return () => {
      window.removeEventListener('pointerdown', handler);
      window.removeEventListener('keydown', handler);
    };
  }, []);

  const onProactive = useCallback(
    (_msg: ProactiveMessage) => {
      if (!soundEnabled) return;
      const result = playProactiveDing();
      if (!result.ok) {
        // Visual fallback: subtle toast.
        try {
          appMessage.info({
            content: '收到一条主动消息（音频未启用）',
            duration: 2,
          });
        } catch {
          /* ignore */
        }
      }
    },
    [soundEnabled, appMessage]
  );

  const {
    proactiveMessages,
    status: proactiveStatus,
    clearProactive,
    clearAll: clearProactiveAll,
  } = useProactiveStream({ onProactive });

  const onToggleSound = useCallback((next: boolean) => {
    setSoundEnabled(next);
    writeSoundPreference(next);
    if (next) {
      // Best-effort unlock immediately when the user enables sound.
      unlockProactiveAudio();
    }
  }, []);

  const [statsOpen, setStatsOpen] = useState<boolean>(false);

  const stats = useMemo(() => {
    const total = messages.length;
    let userCount = 0;
    let assistantCount = 0;
    let systemCount = 0;
    let assistantChars = 0;
    for (const m of messages) {
      if (m.role === 'user') userCount += 1;
      else if (m.role === 'assistant') {
        assistantCount += 1;
        assistantChars += m.content.length;
      } else if (m.role === 'system') {
        systemCount += 1;
      }
    }
    return { total, userCount, assistantCount, systemCount, assistantChars };
  }, [messages]);

  const onConfirmClear = useCallback(() => {
    Modal.confirm({
      title: '清空当前对话?',
      content: '将删除所有本地消息，且无法恢复。',
      okText: '清空',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        clearMessages();
      },
    });
  }, [clearMessages]);

  const onConfirmClearProactive = useCallback(() => {
    if (proactiveMessages.length === 0) return;
    Modal.confirm({
      title: '清空所有主动消息?',
      content: `将关闭当前 ${proactiveMessages.length} 条主动消息横幅。`,
      okText: '清空',
      cancelText: '取消',
      okButtonProps: { danger: true },
      onOk: () => {
        clearProactiveAll();
      },
    });
  }, [clearProactiveAll, proactiveMessages.length]);

  // Stage B.1.7: wrap sendMessage so we can react to send failures (e.g. socket
  // not open). The hook also surfaces transport / server errors through
  // `error`, which renders as the red bar below the toolbar.
  const onSend = useCallback(
    (text: string) => {
      const ok = sendMessage(text);
      if (!ok) {
        // The hook will already have surfaced this through `error` for
        // mid-stream disconnects. For an immediate send failure we log for
        // visibility in dev tools.
        // eslint-disable-next-line no-console
        console.warn('[ChatPage] sendMessage returned false (socket not open)');
      }
    },
    [sendMessage]
  );

  const onRetry = useCallback(() => {
    clearError();
    const ok = retryLast();
    if (!ok) {
      // eslint-disable-next-line no-console
      console.warn('[ChatPage] retryLast returned false (no last input or socket not open)');
    }
  }, [retryLast, clearError]);

  const badge = statusToBadge[status] ?? statusToBadge.closed;
  const proactiveBadge =
    statusToBadge[proactiveStatus] ?? statusToBadge.closed;

  // ============= Stage B.3 / B.4 真接入 =============
  // 1) 情感雷达:useEffect 拉 `GET /api/emotion/latest`
  const [emotionData, setEmotionData] = useState<EmotionData>(EMPTY_EMOTION);
  const [emotionHistorical, setEmotionHistorical] = useState<EmotionData | undefined>(
    undefined
  );
  useEffect(() => {
    let aborted = false;
    const loadEmotion = async () => {
      try {
        const resp = await fetch('/api/emotion/latest?user_id=default');
        if (!resp.ok) {
          // 失败:保持空数据,EmotionPanel 内部走骨架屏,不阻塞聊天
          return;
        }
        const data = await resp.json();
        if (aborted) return;
        setEmotionData(coerceEmotionData(data?.plutchik));
        if (data?.historical_max) {
          setEmotionHistorical(coerceEmotionData(data.historical_max));
        }
      } catch {
        /* 静默:雷达图走骨架屏即可 */
      }
    };
    void loadEmotion();
    return () => {
      aborted = true;
    };
  }, []);

  // 2) 话题时间线:useEffect 拉 `GET /api/memory/timeline?days=7`
  const [timelineTopics, setTimelineTopics] = useState<TopicNode[]>([]);
  useEffect(() => {
    let aborted = false;
    const loadTimeline = async () => {
      try {
        const resp = await fetch('/api/memory/timeline?days=7');
        if (!resp.ok) {
          // 失败:保持空数组,TimelineCanvas 内部走骨架屏
          return;
        }
        const data = await resp.json();
        if (aborted) return;
        setTimelineTopics(coerceTimelineNodes(data?.nodes));
      } catch {
        /* 静默 */
      }
    };
    void loadTimeline();
    return () => {
      aborted = true;
    };
  }, []);

  // Healthy = either heartbeat not yet received (we don't know yet) or last
  // pong is within 90s (3x the 30s heartbeat). The `lastPongAt` re-render is
  // driven by the ping/pong cycle inside useWebSocket.
  const heartbeatHealthy = useMemo(() => {
    if (lastPongAt === null) return true;
    return Date.now() - lastPongAt < 90_000;
  }, [lastPongAt]);

  return (
    <div className="h-[calc(100vh-120px)] flex gap-3">
      {/* Left: chat column 70% */}
      <div className="flex-[7] flex flex-col bg-white rounded shadow-sm overflow-hidden min-w-0">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-3 py-2 border-b border-gray-100">
          <Space wrap>
            <Badge status={badge.status} text={badge.text} />
            {connId ? (
              <Tooltip title="Connection ID">
                <Tag color="geekblue" className="font-mono text-xs">
                  {connId.slice(0, 12)}
                </Tag>
              </Tooltip>
            ) : null}
            {isStreaming ? <Tag color="processing">正在生成…</Tag> : null}
            <Tooltip title="主动消息通道状态">
              <Badge
                status={proactiveBadge.status}
                text={`主动:${proactiveBadge.text}`}
              />
            </Tooltip>
            <Tooltip title="心跳健康状态（每 30s 一次 ping/pong）">
              <Tag color={heartbeatHealthy ? 'green' : 'orange'}>
                {heartbeatHealthy ? '心跳正常' : '心跳异常'}
              </Tag>
            </Tooltip>
            {proactiveMessages.length > 0 ? (
              <Tag color="warning" className="font-mono text-xs">
                待处理 {proactiveMessages.length}
              </Tag>
            ) : null}
          </Space>
          <Space wrap>
            <Tooltip title="会话管理（切换/新建/删除）">
              <Button
                size="small"
                type="text"
                icon={<FolderOpenOutlined />}
                onClick={() => setSidebarOpen(true)}
                aria-label="open session sidebar"
              >
                会话
              </Button>
            </Tooltip>
            <Tooltip title={soundEnabled ? '关闭通知音' : '开启通知音'}>
              <span className="inline-flex items-center gap-1 text-xs text-gray-500">
                {soundEnabled ? <SoundFilled /> : <SoundOutlined />}
                <Switch
                  size="small"
                  checked={soundEnabled}
                  onChange={onToggleSound}
                  aria-label="toggle proactive sound"
                />
              </span>
            </Tooltip>
            <Tooltip title="清空主动消息">
              <Button
                size="small"
                icon={<ClearOutlined />}
                onClick={onConfirmClearProactive}
                disabled={proactiveMessages.length === 0}
              >
                清空主动
              </Button>
            </Tooltip>
            <Tooltip title="对话统计">
              <Button
                size="small"
                icon={<BarChartOutlined />}
                onClick={() => setStatsOpen(true)}
              >
                统计
              </Button>
            </Tooltip>
            <Tooltip title="清空对话">
              <Button
                size="small"
                danger
                icon={<ClearOutlined />}
                onClick={onConfirmClear}
              >
                清空
              </Button>
            </Tooltip>
            <Tooltip title="刷新页面">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => window.location.reload()}
              />
            </Tooltip>
          </Space>
        </div>

        {/* Stage B.1.7: error bar - shown when the chat hook reports an error
            (transport-level disconnect or server-side { type: "error" }). The
            "重试" button resends the most recent user input; "忽略" dismisses. */}
        {error ? (
          <Alert
            type="error"
            showIcon
            icon={<WarningOutlined />}
            className="rounded-none border-x-0"
            message={
              <span className="flex items-center justify-between gap-2">
                <span className="truncate">
                  {status === 'closed' || status === 'error'
                    ? '与服务器连接已断开，正在尝试重连…'
                    : '服务器返回错误'}
                  {error ? `：${error}` : ''}
                </span>
                <Space size="small">
                  <Button
                    size="small"
                    type="primary"
                    danger
                    icon={<SyncOutlined />}
                    onClick={onRetry}
                    disabled={status !== 'open'}
                  >
                    重试
                  </Button>
                  <Button size="small" onClick={clearError}>
                    忽略
                  </Button>
                </Space>
              </span>
            }
          />
        ) : null}

        {/* Proactive banners (top-贴边) */}
        {proactiveMessages.length > 0 ? (
          <div className="px-3 pt-2 bg-amber-50/40 border-b border-amber-100">
            <ProactiveMessageList
              messages={proactiveMessages}
              onDismiss={clearProactive}
              hideWhenEmpty
              header={false}
            />
          </div>
        ) : null}

        {/* Message list */}
        <div className="flex-1 min-h-0 bg-gray-50">
          <MessageList messages={messages} />
        </div>

        {/* Input */}
        <ChatInput onSend={onSend} disabled={status !== 'open' || isStreaming} />
      </div>

      {/* Right: sidebar 30% */}
      <div className="flex-[3] flex flex-col gap-3 min-w-[260px]">
        <EmotionPanel
          data={emotionData}
          historicalMax={emotionHistorical}
          title="情感雷达（Plutchik 8 维）"
        />
        <TimelineCanvas topics={timelineTopics} />
      </div>

      <Modal
        title="对话统计"
        open={statsOpen}
        footer={null}
        onCancel={() => setStatsOpen(false)}
      >
        <Row gutter={[16, 16]}>
          <Col span={12}>
            <Statistic title="消息总数" value={stats.total} />
          </Col>
          <Col span={12}>
            <Statistic title="用户消息" value={stats.userCount} />
          </Col>
          <Col span={12}>
            <Statistic title="助手消息" value={stats.assistantCount} />
          </Col>
          <Col span={12}>
            <Statistic title="系统消息" value={stats.systemCount} />
          </Col>
          <Col span={24}>
            <Statistic title="助手累计字符" value={stats.assistantChars} />
          </Col>
        </Row>
      </Modal>

      <SessionSidebar
        open={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        currentSessionId={sessionId}
        onSelect={(id) => {
          void switchSession(id);
          setSidebarOpen(false);
        }}
        onCreated={(id) => {
          void switchSession(id);
          setSidebarOpen(false);
        }}
        onDeleted={(id) => {
          if (sessionId === id) {
            // 当前 session 被删除,清空本地标记
            void switchSession(null);
          }
        }}
      />
    </div>
  );
}
