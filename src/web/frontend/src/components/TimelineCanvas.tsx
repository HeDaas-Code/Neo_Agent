/**
 * TimelineCanvas - 7 天话题时间线
 *
 * 功能：
 *  - 使用 echarts-for-react 渲染话题节点（X 轴：日期 7 天；Y 轴：分类）
 *  - 分类：家庭 / 工作 / 兴趣 / 朋友 / 其他
 *  - 节点：圆点，hover 显示话题标题 + 提及次数
 *  - 节点点击 → fetch `/api/memory/loop/{uuid}/context` 获取关联上下文
 *    → 把响应存入 state → Drawer 显示
 *  - 数据通过 props 传入；useTimelineWebSocket hook 订阅 /ws/event 过滤 type="topic_update"
 *  - 数据变化时 ECharts 自动平滑过渡
 *  - 数据为空时显示骨架屏
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Skeleton, Empty, Card, Tag, Drawer, Descriptions, Spin, message } from 'antd';
import { useWebSocket, WebSocketStatus } from '../hooks/useWebSocket';

// ============= 类型定义 =============

/** 话题上下文条目(对应后端 LoopContextItem) */
export interface LoopContextItem {
  role: string;
  content: string;
  timestamp?: string | null;
  source?: string;
}

/** 话题上下文响应(对应后端 LoopContextResponse) */
export interface LoopContextResponse {
  uuid: string;
  topic: string;
  status: string;
  items: LoopContextItem[];
  total: number;
}

/** 话题节点 */
export interface TopicNode {
  /** 唯一 ID */
  id: string;
  /** 话题标题 */
  title: string;
  /** 话题分类（家庭/工作/兴趣/朋友/其他） */
  category: string;
  /** 出现的日期（ISO 字符串，YYYY-MM-DD） */
  date: string;
  /** 提及次数 */
  mentionCount: number;
  /** 相关对话上下文（可选） */
  relatedContext?: string;
}

/** TimelineCanvas 组件 Props */
export interface TimelineCanvasProps {
  /** 话题列表 */
  topics: TopicNode[];
  /** 节点点击回调（弹窗/抽屉显示详情） */
  onTopicClick?: (id: string) => void;
  /** 卡片标题 */
  title?: string;
  /** 高度，默认 420 */
  height?: number;
  /** 是否在内部启用 Drawer 显示详情（默认 true） */
  showDetailDrawer?: boolean;
  /** WebSocket URL（可选，传入则启用实时订阅） */
  wsUrl?: string;
}

/** /ws/event topic_update 消息 */
export interface TopicUpdateEvent {
  type: 'topic_update';
  /** 一次推送的话题节点（增量） */
  topics: TopicNode[];
  /** 可选：替换模式（true 表示替换全部，否则为合并） */
  replace?: boolean;
  timestamp?: string;
}

// ============= 常量 =============

/** Y 轴分类（自下而上） */
export const TOPIC_CATEGORIES = ['其他', '朋友', '兴趣', '工作', '家庭'] as const;
export type TopicCategory = (typeof TOPIC_CATEGORIES)[number];

/** 中文分类标签 */
export const CATEGORY_LABELS_CN: Record<string, string> = {
  家庭: '家庭',
  工作: '工作',
  兴趣: '兴趣',
  朋友: '朋友',
  其他: '其他',
};

const DEFAULT_WS_URL = (() => {
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/event';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.hostname}:8000/ws/event`;
})();

const DEFAULT_HEIGHT = 420;

/** antd 主色（蓝） */
const PRIMARY = '#1677ff';
/** 分类颜色映射 */
const CATEGORY_COLORS: Record<string, string> = {
  家庭: '#fa541c',     // 暖橙
  工作: '#1677ff',     // 蓝
  兴趣: '#52c41a',     // 绿
  朋友: '#13c2c2',     // 青
  其他: '#8c8c8c',     // 灰
};

function colorForCategory(category: string): string {
  return CATEGORY_COLORS[category] ?? PRIMARY;
}

// ============= 工具函数 =============

/** 获取最近 7 天的日期数组（含今天），从最早到今天 */
function last7Days(today: Date = new Date()): string[] {
  const result: string[] = [];
  for (let i = 6; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    result.push(toDateString(d));
  }
  return result;
}

function toDateString(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}

function normalizeCategory(raw: string | undefined | null): string {
  if (!raw) return '其他';
  const trimmed = String(raw).trim();
  if ((TOPIC_CATEGORIES as readonly string[]).includes(trimmed)) {
    return trimmed;
  }
  // 兼容中英别名
  const alias: Record<string, string> = {
    family: '家庭',
    work: '工作',
    hobby: '兴趣',
    interest: '兴趣',
    friend: '朋友',
    friends: '朋友',
    other: '其他',
  };
  return alias[trimmed.toLowerCase()] ?? '其他';
}

function safeTopic(raw: any): TopicNode | null {
  if (!raw || typeof raw !== 'object') return null;
  const id = String(raw.id ?? '').trim();
  if (!id) return null;
  const title = String(raw.title ?? raw.topic ?? '未命名话题');
  const category = normalizeCategory(raw.category);
  const dateStr = String(raw.date ?? '').trim() || toDateString(new Date());
  const mentionCount = Math.max(0, Number(raw.mentionCount ?? raw.mentions ?? 0) || 0);
  const relatedContext =
    typeof raw.relatedContext === 'string'
      ? raw.relatedContext
      : typeof raw.context === 'string'
        ? raw.context
        : undefined;
  return { id, title, category, date: dateStr, mentionCount, relatedContext };
}

// ============= Hook: useTimelineWebSocket =============

export interface UseTimelineWebSocketResult {
  /** 累积的话题列表 */
  topics: TopicNode[];
  /** 收到的全部 topic_update 事件 */
  events: TopicUpdateEvent[];
  /** WebSocket 连接状态 */
  status: WebSocketStatus;
  /** 手动清空 */
  clear: () => void;
  /** 手动重连 */
  reconnect: () => void;
}

/**
 * useTimelineWebSocket - 订阅 /ws/event，过滤 type="topic_update" 消息。
 *
 *  - 默认合并（replace=undefined/false 时把新话题合并到现有列表）
 *  - replace=true 时替换整个列表
 */
export function useTimelineWebSocket(
  url: string = DEFAULT_WS_URL
): UseTimelineWebSocketResult {
  const [topics, setTopics] = useState<TopicNode[]>([]);
  const [events, setEvents] = useState<TopicUpdateEvent[]>([]);

  const handleMessage = useCallback((parsed: unknown) => {
    if (!parsed || typeof parsed !== 'object') return;
    const msg = parsed as Record<string, unknown>;
    if (msg.type !== 'topic_update') return;
    const rawTopics = Array.isArray(msg.topics) ? msg.topics : [];
    const normalized = rawTopics
      .map(safeTopic)
      .filter((t): t is TopicNode => t !== null);

    const evt: TopicUpdateEvent = {
      type: 'topic_update',
      topics: normalized,
      replace: Boolean(msg.replace),
      timestamp: typeof msg.timestamp === 'string' ? msg.timestamp : undefined,
    };

    setEvents((prev) => [...prev, evt]);
    setTopics((prev) => {
      if (evt.replace) return normalized;
      // 合并：按 id 去重，新数据覆盖旧数据
      const map = new Map<string, TopicNode>();
      for (const t of prev) map.set(t.id, t);
      for (const t of normalized) map.set(t.id, t);
      return Array.from(map.values());
    });
  }, []);

  const { status, reconnectNow, clearMessages } = useWebSocket<unknown>(url, {
    onMessage: handleMessage,
  });

  const clear = useCallback(() => {
    setTopics([]);
    setEvents([]);
    clearMessages();
  }, [clearMessages]);

  return { topics, events, status, clear, reconnect: reconnectNow };
}

// ============= 主组件 =============

const TimelineCanvas: React.FC<TimelineCanvasProps> = ({
  topics,
  onTopicClick,
  title = '话题时间线（近 7 天）',
  height = DEFAULT_HEIGHT,
  showDetailDrawer = true,
  wsUrl,
}) => {
  // 可选 WS 订阅（传入空 URL 时 useWebSocket 直接进入 error 状态，不发起连接）
  const { topics: wsTopics, status, reconnect } = useTimelineWebSocket(
    wsUrl ?? ''
  );

  // 优先使用 props 传入的话题
  const allTopics = useMemo<TopicNode[]>(() => {
    if (topics && topics.length > 0) return topics;
    return wsTopics;
  }, [topics, wsTopics]);

  // 仅保留最近 7 天的话题
  const dates = useMemo(() => last7Days(), []);
  const dateSet = useMemo(() => new Set(dates), [dates]);

  const recentTopics = useMemo(
    () => allTopics.filter((t) => dateSet.has(t.date)),
    [allTopics, dateSet]
  );

  // 详情抽屉 + 上下文加载
  const [detail, setDetail] = useState<TopicNode | null>(null);
  // contextLoading:fetch 期间为 true;context:后端返回的上下文;contextError:fetch 错误
  const [contextLoading, setContextLoading] = useState<boolean>(false);
  const [context, setContext] = useState<LoopContextResponse | null>(null);
  const [contextError, setContextError] = useState<string | null>(null);

  // 节点点击:设置 detail,触发 /api/memory/loop/{uuid}/context fetch
  const handleClick = useCallback(
    async (id: string) => {
      const t = recentTopics.find((x) => x.id === id) ?? null;
      // 先把当前节点写入 detail,Drawer 立刻可见,内部显示 loading
      setDetail(t);
      setContext(null);
      setContextError(null);
      setContextLoading(true);
      try {
        // 调用后端上下文接口
        const resp = await fetch(`/api/memory/loop/${encodeURIComponent(id)}/context`);
        if (!resp.ok) {
          throw new Error(`HTTP ${resp.status}`);
        }
        const data = (await resp.json()) as LoopContextResponse;
        setContext(data);
      } catch (err) {
        // 不阻塞聊天,仅在 Drawer 内显示错误信息
        const msgText = err instanceof Error ? err.message : String(err);
        setContextError(msgText);
        try {
          message.warning(`加载话题上下文失败:${msgText}`);
        } catch {
          /* ignore */
        }
      } finally {
        setContextLoading(false);
      }
      onTopicClick?.(id);
    },
    [recentTopics, onTopicClick]
  );

  // 按分类聚合散点数据
  const series = useMemo(() => {
    // 用单系列 + 分类颜色（symbol 着色）实现
    return [
      {
        name: '话题节点',
        type: 'scatter' as const,
        symbol: 'circle' as const,
        symbolSize: (val: any) => {
          const count = Number(val?.[2] ?? 0);
          // 提及次数 1~50 映射到 10~32 像素
          return Math.max(10, Math.min(32, 10 + Math.log2(count + 1) * 4));
        },
        itemStyle: {
          color: (params: any) => colorForCategory(params.data?.[3]),
          borderColor: '#ffffff',
          borderWidth: 1.5,
          opacity: 0.85,
        },
        emphasis: {
          focus: 'series' as const,
          itemStyle: {
            opacity: 1,
            borderColor: PRIMARY,
            borderWidth: 2,
          },
        },
        data: recentTopics.map((t) => [
          t.date,
          t.category,
          t.mentionCount,
          t.category,
          t.id,
          t.title,
        ]),
      },
    ];
  }, [recentTopics]);

  const option = useMemo(
    () => ({
      // 全局动画
      animationDuration: 500,
      animationEasingUpdate: 'cubicOut' as const,

      title: {
        text: title,
        left: 'center',
        top: 4,
        textStyle: { fontSize: 14, fontWeight: 500, color: '#262626' },
      },

      grid: {
        left: 60,
        right: 24,
        top: 48,
        bottom: 60,
        containLabel: true,
      },

      tooltip: {
        trigger: 'item' as const,
        confine: true,
        formatter: (params: any) => {
          const v = params?.data ?? [];
          // [date, category, mentionCount, category, id, title]
          const dateStr = v[0];
          const category = v[1];
          const count = v[2];
          const title = v[5] ?? '(未命名)';
          return `<div style="font-size:12px">
            <div style="font-weight:600;margin-bottom:4px">${title}</div>
            <div>日期：${dateStr}</div>
            <div>分类：<span style="color:${colorForCategory(category)}">${category}</span></div>
            <div>提及次数：<b>${count}</b></div>
          </div>`;
        },
      },

      xAxis: {
        type: 'category' as const,
        data: dates,
        name: '日期',
        nameLocation: 'middle' as const,
        nameGap: 28,
        nameTextStyle: { color: '#595959' },
        axisLine: { lineStyle: { color: '#d9d9d9' } },
        axisLabel: { color: '#595959' },
        splitLine: { show: false },
        boundaryGap: true,
      },

      yAxis: {
        type: 'category' as const,
        data: [...TOPIC_CATEGORIES],
        name: '话题分类',
        nameLocation: 'middle' as const,
        nameGap: 42,
        nameTextStyle: { color: '#595959' },
        axisLine: { lineStyle: { color: '#d9d9d9' } },
        axisLabel: {
          color: (val: string) => colorForCategory(val),
          fontWeight: 500,
        },
        splitLine: { show: true, lineStyle: { color: '#f0f0f0' } },
      },

      legend: {
        show: true,
        bottom: 0,
        data: [...TOPIC_CATEGORIES],
        textStyle: { color: '#595959' },
        icon: 'circle',
        itemWidth: 8,
        itemHeight: 8,
      },

      toolbox: {
        right: 12,
        top: 8,
        feature: {
          dataZoom: { yAxisIndex: 'none' },
          restore: {},
        },
        iconStyle: { borderColor: '#8c8c8c' },
      },

      series,
    }),
    [dates, series, title]
  );

  // useEffect + setOption 平滑过渡
  const echartsRef = useRef<ReactECharts | null>(null);
  const onEvents = useMemo(
    () => ({
      click: (params: any) => {
        const id = params?.data?.[4];
        if (typeof id === 'string' && id.length > 0) {
          handleClick(id);
        }
      },
    }),
    [handleClick]
  );

  useEffect(() => {
    const inst = echartsRef.current?.getEchartsInstance?.();
    if (!inst) return;
    inst.setOption(option, { notMerge: false, lazyUpdate: true });
  }, [option]);

  const isEmpty = recentTopics.length === 0;

  const statusTag = (() => {
    switch (status) {
      case 'open':
        return <Tag color="green">WS 已连接</Tag>;
      case 'connecting':
        return <Tag color="blue">连接中</Tag>;
      case 'closed':
        return <Tag color="default">已断开</Tag>;
      case 'error':
        return <Tag color="red">错误</Tag>;
      default:
        return null;
    }
  })();

  return (
    <>
      <Card
        title={title}
        size="small"
        extra={
          <span style={{ display: 'inline-flex', gap: 8, alignItems: 'center' }}>
            {wsUrl ? statusTag : null}
            {wsUrl && status !== 'open' ? (
              <a onClick={reconnect} style={{ fontSize: 12 }}>
                重连
              </a>
            ) : null}
          </span>
        }
        styles={{ body: { padding: 8 } }}
      >
        {isEmpty ? (
          <Skeleton active paragraph={{ rows: 5 }} style={{ padding: 16 }} />
        ) : (
          <ReactECharts
            ref={(e) => {
              echartsRef.current = e;
            }}
            option={option}
            notMerge={false}
            lazyUpdate
            onEvents={onEvents}
            style={{ height, width: '100%' }}
            opts={{ renderer: 'canvas' }}
          />
        )}
        {isEmpty && (
          <Empty
            image={Empty.PRESENTED_IMAGE_SIMPLE}
            description="近 7 天暂无话题"
            style={{ marginTop: -180 }}
          />
        )}
      </Card>

      {showDetailDrawer && (
        <Drawer
          title={detail?.title ?? '话题详情'}
          open={!!detail}
          onClose={() => {
            setDetail(null);
            setContext(null);
            setContextError(null);
            setContextLoading(false);
          }}
          width={480}
          destroyOnClose
        >
          {detail && (
            <Descriptions
              column={1}
              size="small"
              bordered
              labelStyle={{ width: 96, color: '#595959' }}
            >
              <Descriptions.Item label="ID">
                <code>{detail.id}</code>
              </Descriptions.Item>
              <Descriptions.Item label="标题">
                {detail.title}
              </Descriptions.Item>
              <Descriptions.Item label="分类">
                <Tag color={colorForCategory(detail.category)}>
                  {detail.category}
                </Tag>
              </Descriptions.Item>
              <Descriptions.Item label="日期">
                {detail.date}
              </Descriptions.Item>
              <Descriptions.Item label="提及次数">
                {detail.mentionCount}
              </Descriptions.Item>
              {detail.relatedContext && (
                <Descriptions.Item label="缓存上下文">
                  <div
                    style={{
                      whiteSpace: 'pre-wrap',
                      wordBreak: 'break-word',
                      color: '#262626',
                    }}
                  >
                    {detail.relatedContext}
                  </div>
                </Descriptions.Item>
              )}
            </Descriptions>
          )}

          {/* 节点点击 → 远程加载关联上下文(从 /api/memory/loop/{uuid}/context) */}
          <div className="mt-4">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-semibold text-gray-700">
                关联上下文
              </span>
              {contextLoading ? <Spin size="small" /> : null}
            </div>
            {contextLoading ? (
              <Skeleton active paragraph={{ rows: 3 }} />
            ) : contextError ? (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description={`加载失败:${contextError}`}
              />
            ) : context ? (
              context.items.length === 0 ? (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description="暂无关联上下文"
                />
              ) : (
                <div className="space-y-2 max-h-[40vh] overflow-y-auto">
                  {context.items.map((it, idx) => (
                    <div
                      key={`${it.source ?? 'ctx'}-${idx}`}
                      className="border border-gray-200 rounded p-2 bg-gray-50"
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Tag
                          color={
                            it.role === 'user'
                              ? 'blue'
                              : it.role === 'assistant'
                                ? 'geekblue'
                                : 'default'
                          }
                        >
                          {it.role}
                        </Tag>
                        {it.source ? (
                          <Tag color="purple" className="text-xs">
                            {it.source}
                          </Tag>
                        ) : null}
                        {it.timestamp ? (
                          <span className="text-xs text-gray-500">
                            {it.timestamp}
                          </span>
                        ) : null}
                      </div>
                      <div className="text-sm text-gray-800 whitespace-pre-wrap break-words">
                        {it.content}
                      </div>
                    </div>
                  ))}
                </div>
              )
            ) : (
              <Empty
                image={Empty.PRESENTED_IMAGE_SIMPLE}
                description="点击节点加载上下文"
              />
            )}
          </div>
        </Drawer>
      )}
    </>
  );
};

export default TimelineCanvas;
