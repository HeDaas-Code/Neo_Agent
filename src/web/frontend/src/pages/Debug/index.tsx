/**
 * Debug page - live log viewer backed by /ws/debug.
 *
 * - Subscribes to /ws/debug via the generic useWebSocket hook (independent
 *   instance from the chat page).
 * - Filtering UI is delegated to <LogFilterBar /> (level multi-select,
 *   module substring, time range). All filtering is in-memory on the
 *   `logs` state — no round-trips to the backend.
 * - Export UI is delegated to <LogExporter /> (TXT + NDJSON). Exports use
 *   the *filtered* view so "what you see is what you export".
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Card,
  List,
  Tag,
  Space,
  Button,
  Tooltip,
  Empty,
  Badge,
  message as antdMessage,
} from 'antd';
import {
  ClearOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useWebSocket, WebSocketStatus } from '../../hooks/useWebSocket';
import LogFilterBar, {
  LogFilterValue,
  LogLevelOption,
} from '../../components/Debug/LogFilterBar';
import LogExporter from '../../components/Debug/LogExporter';
import type { LogEntry } from '../../components/Debug/types';

// Re-export so existing consumers (tests, storybook, etc.) can keep
// importing `LogEntry` from the page module.
export type { LogEntry } from '../../components/Debug/types';

interface RawLogPayload {
  timestamp?: string;
  level?: string;
  module?: string;
  message?: string;
  // alternate field names some backends may use
  time?: string;
  logger?: string;
  msg?: string;
  text?: string;
}

const DEFAULT_DEBUG_URL = 'ws://localhost:8000/ws/debug';

function resolveDebugUrl(override?: string): string {
  if (override) return override;
  const isDev = Boolean((import.meta as any)?.env?.DEV);
  if (isDev) return DEFAULT_DEBUG_URL;
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/ws/debug`;
  }
  return DEFAULT_DEBUG_URL;
}

let _logCounter = 0;
function genId(): string {
  _logCounter += 1;
  return `log-${Date.now().toString(36)}-${_logCounter.toString(36)}`;
}

function normalizeLog(payload: any): LogEntry | null {
  if (!payload || typeof payload !== 'object') return null;
  const p = payload as RawLogPayload;
  const timestamp = p.timestamp ?? p.time ?? new Date().toISOString();
  const level = (p.level ?? 'INFO').toString().toUpperCase();
  const moduleName = p.module ?? p.logger ?? 'app';
  const message = p.message ?? p.msg ?? p.text ?? '';
  return {
    id: genId(),
    timestamp,
    level,
    module: moduleName,
    message,
  };
}

const levelColor: Record<string, string> = {
  INFO: 'blue',
  WARN: 'orange',
  WARNING: 'orange',
  ERROR: 'red',
  DEBUG: 'default',
  TRACE: 'default',
};

const statusBadge: Record<WebSocketStatus, { status: any; text: string }> = {
  connecting: { status: 'processing', text: '连接中' },
  open: { status: 'success', text: '已连接' },
  closed: { status: 'default', text: '未连接' },
  error: { status: 'error', text: '异常' },
};

const EMPTY_FILTER: LogFilterValue = {
  levels: [],
  module: '',
  range: null,
};

const DebugPage: React.FC = () => {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [filter, setFilter] = useState<LogFilterValue>(EMPTY_FILTER);
  const [autoScroll, setAutoScroll] = useState<boolean>(true);
  const listRef = useRef<HTMLDivElement | null>(null);

  const handleMessage = useCallback((data: any) => {
    // Some backends send { type: "log", payload: {...} } or array of logs.
    if (Array.isArray(data)) {
      const entries: LogEntry[] = [];
      for (const item of data) {
        const e = normalizeLog(item);
        if (e) entries.push(e);
      }
      if (entries.length > 0) {
        setLogs((prev) => [...entries.reverse(), ...prev]);
      }
      return;
    }
    if (data && typeof data === 'object') {
      if ((data as any).type === 'log' && (data as any).payload) {
        const e = normalizeLog((data as any).payload);
        if (e) {
          setLogs((prev) => [e, ...prev]);
        }
        return;
      }
      if ((data as any).type === 'logs' && Array.isArray((data as any).payload)) {
        const entries: LogEntry[] = [];
        for (const item of (data as any).payload) {
          const e = normalizeLog(item);
          if (e) entries.push(e);
        }
        if (entries.length > 0) {
          setLogs((prev) => [...entries.reverse(), ...prev]);
        }
        return;
      }
    }
    const e = normalizeLog(data);
    if (e) {
      setLogs((prev) => [e, ...prev]);
    }
  }, []);

  const ws = useWebSocket(resolveDebugUrl(), { onMessage: handleMessage });

  // Known module list for filter suggestions (passed down to LogFilterBar).
  const moduleOptions = useMemo(() => {
    const set = new Set<string>();
    for (const l of logs) set.add(l.module);
    return Array.from(set).sort();
  }, [logs]);

  // In-memory filtering: pure function of (logs, filter). No backend hop.
  // - levels: empty array = no level filter (match all)
  // - module: case-insensitive substring match (empty string = no filter)
  // - range:  [from, to]; either bound may be null
  const filtered = useMemo(() => {
    const { levels, module: mod, range } = filter;
    const levelSet = new Set<LogLevelOption>(levels);
    const modQ = mod.trim().toLowerCase();
    return logs.filter((l) => {
      if (levelSet.size > 0 && !levelSet.has(l.level as LogLevelOption)) {
        return false;
      }
      if (modQ && !l.module.toLowerCase().includes(modQ)) {
        return false;
      }
      if (range) {
        const [start, end] = range;
        const t = dayjs(l.timestamp);
        if (start && t.isBefore(start)) return false;
        if (end && t.isAfter(end)) return false;
      }
      return true;
    });
  }, [logs, filter]);

  // Auto-scroll to top so the newest log is visible
  useEffect(() => {
    if (!autoScroll) return;
    const el = listRef.current;
    if (!el) return;
    el.scrollTop = 0;
  }, [filtered.length, autoScroll]);

  const onClear = useCallback(() => {
    setLogs([]);
    antdMessage.success('已清空日志');
  }, []);

  const badge = statusBadge[ws.status] ?? statusBadge.closed;

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {/* Toolbar */}
      <Card
        size="small"
        className="mb-3"
        title={
          <Space>
            <span>实时日志</span>
            <Badge status={badge.status} text={badge.text} />
            <Tag>{filtered.length} / {logs.length}</Tag>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="自动滚动到顶部">
              <Button
                size="small"
                type={autoScroll ? 'primary' : 'default'}
                onClick={() => setAutoScroll((v) => !v)}
              >
                自动滚动
              </Button>
            </Tooltip>
            <LogExporter logs={filtered} />
            <Button
              size="small"
              danger
              icon={<ClearOutlined />}
              onClick={onClear}
            >
              清空
            </Button>
            <Tooltip title="重新连接">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={() => ws.reconnectNow()}
              />
            </Tooltip>
          </Space>
        }
      >
        <LogFilterBar
          value={filter}
          onChange={setFilter}
          moduleOptions={moduleOptions}
        />
      </Card>

      {/* Log list */}
      <Card size="small" className="flex-1 min-h-0 overflow-hidden" bodyStyle={{ padding: 0, height: '100%' }}>
        <div ref={listRef} className="h-full overflow-y-auto bg-gray-50">
          {filtered.length === 0 ? (
            <div className="flex items-center justify-center h-full">
              <Empty description="暂无日志" />
            </div>
          ) : (
            <List
              itemLayout="vertical"
              dataSource={filtered}
              size="small"
              renderItem={(item) => (
                <List.Item
                  key={item.id}
                  className="!px-3 !py-2 border-b border-gray-100 hover:bg-white"
                >
                  <Space size="small" wrap>
                    <span className="font-mono text-xs text-gray-500">
                      {dayjs(item.timestamp).format('YYYY-MM-DD HH:mm:ss.SSS')}
                    </span>
                    <Tag color={levelColor[item.level] ?? 'default'}>{item.level}</Tag>
                    <Tag color="geekblue">{item.module}</Tag>
                    <span className="text-sm text-gray-800 break-all">
                      {item.message}
                    </span>
                  </Space>
                </List.Item>
              )}
            />
          )}
        </div>
      </Card>
    </div>
  );
};

export default DebugPage;
