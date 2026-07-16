/**
 * Event page - 实时事件流页面
 *
 * - 通过 useWebSocket 订阅后端 /ws/events 通道，取代旧版 setInterval 模拟
 * - 收到 event_created / chat_event / proactive_message / message 等事件时合并到列表（去重、按 uuid 更新）
 * - 收到 scheduler_tick 时刷新顶部"当日状态 / 梦境 / 日记 / 想法池"四张状态卡
 * - 标记已读 / 归档 走真实 REST：`POST /api/events/{uuid}/read`、`POST /api/events/{uuid}/archive`
 *   （后端尚未实现该路由时降级为本地状态变更，并通过 message.warning 提示）
 * - useWebSocket 内置指数退避重连，无需手动管理
 */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Card,
  Input,
  Select,
  Space,
  Button,
  Row,
  Col,
  Statistic,
  message,
  Tooltip,
  Badge,
  Tag,
} from 'antd';
import {
  SearchOutlined,
  ClearOutlined,
  WifiOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import axios from 'axios';
import EventTable from '../../components/EventTable';
import { useWebSocket, WebSocketStatus } from '../../hooks/useWebSocket';
import type { Event, EventType, EventStatus } from '../../types/event';

// ----------------------------------------------------------------------
// 常量与工具
// ----------------------------------------------------------------------

/** 本地最大缓存事件条数（避免长时间运行后内存膨胀） */
const MAX_EVENTS = 200;

/** 后端事件类型 → 前端 EventType 映射（不在白名单内时降级为 notification） */
const DEFAULT_EVENT_URL = 'ws://localhost:8000/ws/events';

const TYPE_OPTIONS: { label: string; value: 'ALL' | EventType }[] = [
  { label: 'ALL', value: 'ALL' },
  { label: 'notification', value: 'notification' },
  { label: 'task', value: 'task' },
  { label: 'system', value: 'system' },
];

const STATUS_OPTIONS: { label: string; value: 'ALL' | EventStatus }[] = [
  { label: 'ALL', value: 'ALL' },
  { label: 'pending', value: 'pending' },
  { label: 'completed', value: 'completed' },
  { label: 'failed', value: 'failed' },
];

/** WebSocket 连接状态 → Badge 展示 */
const wsStatusBadge: Record<WebSocketStatus, { status: any; text: string; color: string }> = {
  connecting: { status: 'processing', text: '连接中', color: 'gold' },
  open: { status: 'success', text: '已连接', color: 'green' },
  closed: { status: 'default', text: '已断开', color: 'default' },
  error: { status: 'error', text: '异常', color: 'red' },
};

/**
 * 根据当前环境解析 /ws/events 完整地址：
 * - 开发态走默认 localhost:8000
 * - 生产态走 window.location.host（vite dev server 已代理 /ws 到后端）
 */
function resolveEventsUrl(): string {
  const isDev = Boolean((import.meta as any)?.env?.DEV);
  if (isDev) return DEFAULT_EVENT_URL;
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/ws/events`;
  }
  return DEFAULT_EVENT_URL;
}

// ----------------------------------------------------------------------
// 类型
// ----------------------------------------------------------------------

/** 后端通过 /ws/events 推送的单条消息（参考 ws/events.py） */
interface WsEventMessage {
  type: 'event' | 'system' | 'pong';
  channel?: string;
  event_type?: string;
  payload?: Record<string, any> | null;
  message?: string;
}

/** scheduler_tick 状态卡聚合（绑定 payload 字段） */
interface SchedulerTickState {
  currentState: string; // 当日状态
  dreamCount: number; // 梦境数量（基于 latest dream_record 是否存在）
  diaryCount: number; // 日记数量（暂以 creative_project_count 代理）
  ideaCount: number; // 想法池数量（open_loop_count）
  updatedAt: string; // 最近一次 tick 时间
  running: boolean;
}

const EMPTY_SCHEDULER_STATE: SchedulerTickState = {
  currentState: '—',
  dreamCount: 0,
  diaryCount: 0,
  ideaCount: 0,
  updatedAt: '',
  running: false,
};

/**
 * 把后端 payload 规整为前端 Event。
 * - 兼容 chat_event / proactive_message / message / event_created 等多种 channel
 * - uuid 缺失时使用 event_type + timestamp 兜底，保证表格 rowKey 唯一
 */
function normalizeEvent(payload: any, fallbackType: string): Event | null {
  if (!payload || typeof payload !== 'object') return null;
  const p = payload as Record<string, any>;
  const rawType = (p.type || fallbackType || 'notification').toString();
  const type: EventType = (['notification', 'task', 'system'].includes(rawType)
    ? rawType
    : 'notification') as EventType;
  const rawStatus = (p.status || 'pending').toString();
  const status: EventStatus = (['pending', 'completed', 'failed'].includes(rawStatus)
    ? rawStatus
    : 'pending') as EventStatus;
  const uuid = (p.uuid || p.id || `${fallbackType}-${p.timestamp || Date.now()}-${Math.random().toString(36).slice(2, 8)}`)
    .toString();
  const source = (p.source || p.channel || fallbackType || 'ws').toString();
  const messageText = (p.message || p.text || p.content || `${fallbackType} 事件`).toString();
  const timestamp = (p.timestamp || p.created_at || new Date().toISOString()).toString();
  return {
    uuid,
    type,
    status,
    source,
    message: messageText,
    payload: p,
    timestamp,
  };
}

// ----------------------------------------------------------------------
// 主组件
// ----------------------------------------------------------------------

const EventPage: React.FC = () => {
  // 事件列表（WS 推送合并）
  const [events, setEvents] = useState<Event[]>([]);
  // 过滤条件
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<'ALL' | EventType>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | EventStatus>('ALL');
  // 顶部状态卡
  const [tick, setTick] = useState<SchedulerTickState>(EMPTY_SCHEDULER_STATE);

  // --------------------------------------------------------------------
  // WebSocket 消息处理：合并事件 + 更新状态卡
  // --------------------------------------------------------------------
  const handleMessage = useCallback((data: any) => {
    if (!data || typeof data !== 'object') return;
    const msg = data as WsEventMessage;
    // 只处理 type === 'event' 的业务消息（忽略 system/pong）
    if (msg.type !== 'event') return;

    const eventType = (msg.event_type || '').toString();
    const payload = (msg.payload || {}) as Record<string, any>;

    // scheduler_tick → 刷新顶部状态卡
    if (eventType === 'scheduler_tick') {
      const lifeState = (payload.life_state_snapshot || {}) as Record<string, any>;
      const dreamRecord = payload.dream_record as Record<string, any> | null;
      const openLoopCount = typeof payload.open_loop_count === 'number' ? payload.open_loop_count : 0;
      const creativeProjectCount = typeof payload.creative_project_count === 'number' ? payload.creative_project_count : 0;

      // state_title 是 LifeState 写入数据库的字段；缺失时降级为 mood/energy 拼接
      const currentState = (
        lifeState.state_title
        || lifeState.state
        || (lifeState.mood && lifeState.energy
          ? `${lifeState.mood} / 能量 ${lifeState.energy}`
          : null)
        || '—'
      ).toString();

      setTick({
        currentState,
        // 梦境：latest dream_record 存在视为 1 条；否则 0
        dreamCount: dreamRecord ? 1 : 0,
        // 日记：暂以 creative_project_count 代理（后端未单独统计 diary_count）
        diaryCount: creativeProjectCount,
        // 想法池：open_loop_count 即未关闭的开放循环
        ideaCount: openLoopCount,
        updatedAt: (payload.timestamp || new Date().toISOString()).toString(),
        running: Boolean(payload.running),
      });
      return;
    }

    // 其余事件类型（event_created / chat_event / proactive_message / message / 通配）→ 合并到列表
    if (
      eventType === 'event_created'
      || eventType === 'chat_event'
      || eventType === 'proactive_message'
      || eventType === 'message'
      || eventType === 'emotion_update'
      || (msg.channel === '*')
    ) {
      const newEvent = normalizeEvent(payload, eventType);
      if (!newEvent) return;
      setEvents((prev) => {
        // 按 uuid 去重：已存在则更新，否则前插
        const existingIdx = prev.findIndex((e) => e.uuid === newEvent.uuid);
        if (existingIdx >= 0) {
          const next = prev.slice();
          next[existingIdx] = newEvent;
          return next;
        }
        return [newEvent, ...prev].slice(0, MAX_EVENTS);
      });
    }
  }, []);

  // 订阅 /ws/events（useWebSocket 内置重连）
  const ws = useWebSocket(resolveEventsUrl(), {
    onMessage: handleMessage,
    onOpen: () => {
      // 连接成功时静默提示，避免初次进入页面连续弹窗
      // message.success('已连接事件流');
    },
    onClose: () => {
      // 重连由 hook 自动调度；此处仅给用户一个可视提示
      // message.warning('事件流已断开，正在自动重连…');
    },
    onError: () => {
      // eslint-disable-next-line no-console
      console.warn('[EventPage] /ws/events 连接异常');
    },
  });

  // 连接状态变化时通过 message 提示（仅在 closed / error 时）
  const lastStatusRef = React.useRef<WebSocketStatus>(ws.status);
  useEffect(() => {
    const prev = lastStatusRef.current;
    if (prev === ws.status) return;
    lastStatusRef.current = ws.status;
    if (ws.status === 'open' && prev !== 'connecting') {
      message.success('事件流已连接');
    } else if (ws.status === 'error' && prev !== 'error') {
      message.warning('事件流连接异常，将自动重连');
    }
  }, [ws.status]);

  // --------------------------------------------------------------------
  // 标记已读 / 归档（真实 REST 调用 + 本地乐观更新）
  // --------------------------------------------------------------------
  const handleMarkRead = useCallback(async (uuid: string) => {
    // 乐观更新：先在前端把 status 置为 completed
    setEvents((prev) => prev.map((e) => (e.uuid === uuid ? { ...e, status: 'completed' as EventStatus } : e)));
    try {
      await axios.post(`/api/events/${encodeURIComponent(uuid)}/read`, null, { timeout: 8000 });
      message.success('已标记为已读');
    } catch (err) {
      // 后端路由暂未实现时（404）降级为本地变更
      message.warning('后端记录失败（已本地标记）');
    }
  }, []);

  const handleArchive = useCallback(async (uuid: string) => {
    // 乐观更新：先从前端列表移除
    setEvents((prev) => prev.filter((e) => e.uuid !== uuid));
    try {
      await axios.post(`/api/events/${encodeURIComponent(uuid)}/archive`, null, { timeout: 8000 });
      message.success('已归档');
    } catch (err) {
      message.warning('后端归档失败（已本地移除）');
    }
  }, []);

  const handleClearAll = useCallback(() => {
    setEvents([]);
    message.success('已清空事件列表');
  }, []);

  // --------------------------------------------------------------------
  // 过滤与统计
  // --------------------------------------------------------------------
  const filtered = useMemo(() => {
    const lowerSearch = search.trim().toLowerCase();
    return events.filter((e) => {
      if (typeFilter !== 'ALL' && e.type !== typeFilter) return false;
      if (statusFilter !== 'ALL' && e.status !== statusFilter) return false;
      if (lowerSearch) {
        const haystack = `${e.message} ${e.source} ${e.uuid}`.toLowerCase();
        if (!haystack.includes(lowerSearch)) return false;
      }
      return true;
    });
  }, [events, search, typeFilter, statusFilter]);

  const localStats = useMemo(() => {
    let pending = 0;
    let failed = 0;
    let completed = 0;
    for (const e of events) {
      if (e.status === 'pending') pending += 1;
      else if (e.status === 'failed') failed += 1;
      else completed += 1;
    }
    return { total: events.length, pending, failed, completed };
  }, [events]);

  const tickTimeText = useMemo(() => {
    if (!tick.updatedAt) return '—';
    const d = new Date(tick.updatedAt);
    if (Number.isNaN(d.getTime())) return tick.updatedAt;
    const pad = (n: number) => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
  }, [tick.updatedAt]);

  // --------------------------------------------------------------------
  // 渲染
  // --------------------------------------------------------------------
  return (
    <div>
      {/* 顶部：连接状态 + scheduler_tick 状态卡 */}
      <Row gutter={12} style={{ marginBottom: 8 }} align="middle">
        <Col>
          <Tooltip title={`/ws/events 当前状态：${wsStatusBadge[ws.status].text}（useWebSocket 内置指数退避重连）`}>
            <Badge
              status={wsStatusBadge[ws.status].status}
              text={
                <span style={{ fontSize: 12 }}>
                  <WifiOutlined style={{ marginRight: 4 }} />
                  事件流 {wsStatusBadge[ws.status].text}
                </span>
              }
            />
          </Tooltip>
        </Col>
        <Col>
          <Tag color={tick.running ? 'green' : 'default'} icon={<ApiOutlined />}>
            scheduler {tick.running ? 'running' : 'idle'}
          </Tag>
        </Col>
        <Col>
          <span style={{ color: '#999', fontSize: 12 }}>最近 tick: {tickTimeText}</span>
        </Col>
      </Row>

      {/* 状态卡：当日状态 / 梦境 / 日记 / 想法池 —— 数据源 scheduler_tick.payload */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="当日状态"
              value={tick.currentState}
              valueStyle={{ color: '#1677ff', fontSize: 18 }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="梦境 (今日)"
              value={tick.dreamCount}
              valueStyle={{ color: '#722ed1' }}
              suffix="条"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="日记 (创作项目)"
              value={tick.diaryCount}
              valueStyle={{ color: '#13c2c2' }}
              suffix="篇"
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card size="small" bordered>
            <Statistic
              title="想法池 (开放循环)"
              value={tick.ideaCount}
              valueStyle={{ color: '#fa8c16' }}
              suffix="个"
            />
          </Card>
        </Col>
      </Row>

      {/* 事件列表 */}
      <Card
        title="事件列表 (Event Stream · /ws/events)"
        extra={
          <Space>
            <Tooltip title="清空前端缓存（不影响后端）">
              <Button icon={<ClearOutlined />} danger onClick={handleClearAll}>
                清空
              </Button>
            </Tooltip>
          </Space>
        }
      >
        <Row gutter={12} style={{ marginBottom: 12 }}>
          <Col xs={24} md={12} lg={10}>
            <Input
              allowClear
              prefix={<SearchOutlined />}
              placeholder="搜索消息 / 来源 / UUID"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </Col>
          <Col xs={12} md={6} lg={4}>
            <Select<'ALL' | EventType>
              style={{ width: '100%' }}
              value={typeFilter}
              onChange={setTypeFilter}
              options={TYPE_OPTIONS}
            />
          </Col>
          <Col xs={12} md={6} lg={4}>
            <Select<'ALL' | EventStatus>
              style={{ width: '100%' }}
              value={statusFilter}
              onChange={setStatusFilter}
              options={STATUS_OPTIONS}
            />
          </Col>
          <Col xs={24} md={6} lg={6}>
            <Space>
              <Tooltip title="总数 / pending / failed / completed（前端本地统计）">
                <Tag>总数 {localStats.total}</Tag>
              </Tooltip>
              <Tag color="gold">pending {localStats.pending}</Tag>
              <Tag color="red">failed {localStats.failed}</Tag>
              <Tag color="green">completed {localStats.completed}</Tag>
            </Space>
          </Col>
        </Row>

        <EventTable
          events={filtered}
          onMarkRead={handleMarkRead}
          onArchive={handleArchive}
        />
      </Card>
    </div>
  );
};

export default EventPage;
