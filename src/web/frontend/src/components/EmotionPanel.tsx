/**
 * EmotionPanel - Plutchik 8 维情感雷达
 *
 * 功能：
 *  - 使用 echarts-for-react 渲染 8 维雷达图（joy/trust/fear/surprise/sadness/disgust/anger/anticipation）
 *  - 显示当前实时值（实色）+ 历史最高值（淡色背景）
 *  - 配色：积极情感（joy/trust/anticipation）暖色，消极情感（fear/sadness/disgust/anger）冷色，surprise 中性色
 *  - 数据通过 props 传入；useEmotionWebSocket hook 订阅 /ws/event 过滤 type="emotion_update"
 *  - 数据变化时 ECharts 自动平滑过渡（setOption 增量更新）
 *  - 数据为空时显示骨架屏
 */

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ReactECharts from 'echarts-for-react';
import { Skeleton, Empty, Card, Tag } from 'antd';
import { useWebSocket, WebSocketStatus } from '../hooks/useWebSocket';

// ============= 类型定义 =============

/** Plutchik 8 维情感数据 */
export interface EmotionData {
  joy: number;
  trust: number;
  fear: number;
  surprise: number;
  sadness: number;
  disgust: number;
  anger: number;
  anticipation: number;
}

/** EmotionPanel 组件 Props */
export interface EmotionPanelProps {
  /** 实时情感数据（每维 0~maxValue） */
  data: EmotionData;
  /** 雷达最大值，默认 10 */
  maxValue?: number;
  /** 卡片标题 */
  title?: string;
  /** 历史最高值（淡色背景叠加），可选 */
  historicalMax?: EmotionData;
  /** 高度，默认 360 */
  height?: number;
  /** 后端 event WS 地址（可选，默认 ws://<host>/ws/event） */
  wsUrl?: string;
}

/** /ws/event 消息类型 */
export interface EmotionUpdateEvent {
  type: 'emotion_update';
  /** 当前情感数据 */
  data: EmotionData;
  /** 可选历史最高 */
  historical_max?: EmotionData;
  /** 可选时间戳 */
  timestamp?: string;
}

// ============= 常量 =============

/** 8 维情感（顺时针排列，按 Plutchik 顺序） */
export const EMOTION_KEYS = [
  'joy',
  'trust',
  'fear',
  'surprise',
  'sadness',
  'disgust',
  'anger',
  'anticipation',
] as const;

/** 中文标签 */
export const EMOTION_LABELS_CN: Record<keyof EmotionData, string> = {
  joy: '喜悦',
  trust: '信任',
  fear: '恐惧',
  surprise: '惊讶',
  sadness: '悲伤',
  disgust: '厌恶',
  anger: '愤怒',
  anticipation: '期待',
};

/**
 * 配色策略：
 *  - 积极情感（joy / trust / anticipation）→ 暖色（橙/金/桃）
 *  - 消极情感（fear / sadness / disgust / anger）→ 冷色（蓝/灰/青/紫）
 *  - surprise → 中性色
 */
const POSITIVE_COLOR = '#fa8c16';     // 暖橙
const NEUTRAL_COLOR = '#8c8c8c';      // 中性灰
const NEGATIVE_COLOR = '#1677ff';     // 冷蓝（antd 主色）

function colorForEmotion(key: keyof EmotionData): string {
  switch (key) {
    case 'joy':
    case 'trust':
    case 'anticipation':
      return POSITIVE_COLOR;
    case 'surprise':
      return NEUTRAL_COLOR;
    case 'fear':
    case 'sadness':
    case 'disgust':
    case 'anger':
      return NEGATIVE_COLOR;
    default:
      return NEUTRAL_COLOR;
  }
}

const DEFAULT_WS_URL = (() => {
  if (typeof window === 'undefined') return 'ws://localhost:8000/ws/event';
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.hostname}:8000/ws/event`;
})();

const DEFAULT_MAX = 10;
const DEFAULT_HEIGHT = 360;

// ============= 工具函数 =============

function clamp(value: number, min: number, max: number): number {
  if (Number.isNaN(value)) return min;
  return Math.max(min, Math.min(max, value));
}

function safeNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function normalizeData(data: Partial<EmotionData> | null | undefined): EmotionData {
  return {
    joy: safeNumber(data?.joy),
    trust: safeNumber(data?.trust),
    fear: safeNumber(data?.fear),
    surprise: safeNumber(data?.surprise),
    sadness: safeNumber(data?.sadness),
    disgust: safeNumber(data?.disgust),
    anger: safeNumber(data?.anger),
    anticipation: safeNumber(data?.anticipation),
  };
}

function isEmotionDataEmpty(data: EmotionData): boolean {
  return EMOTION_KEYS.every((k) => data[k] === 0);
}

// ============= Hook: useEmotionWebSocket =============

export interface UseEmotionWebSocketResult {
  /** 最新一次 emotion_update 携带的实时数据 */
  data: EmotionData | null;
  /** 历史最高（来自后端） */
  historicalMax: EmotionData | null;
  /** WebSocket 连接状态 */
  status: WebSocketStatus;
  /** 收到的全部 emotion_update 事件（按时间顺序） */
  events: EmotionUpdateEvent[];
  /** 手动重连 */
  reconnect: () => void;
}

/**
 * useEmotionWebSocket - 订阅 /ws/event，过滤 type="emotion_update" 消息。
 *
 * 任何 WebSocket 消息只要 type === "emotion_update" 即被解析为 EmotionUpdateEvent；
 * 不符合的消息会被忽略，组件不会因此重渲染。
 */
export function useEmotionWebSocket(
  url: string = DEFAULT_WS_URL
): UseEmotionWebSocketResult {
  const [data, setData] = useState<EmotionData | null>(null);
  const [historicalMax, setHistoricalMax] = useState<EmotionData | null>(null);
  const [events, setEvents] = useState<EmotionUpdateEvent[]>([]);

  const handleMessage = useCallback((parsed: unknown) => {
    if (!parsed || typeof parsed !== 'object') return;
    const msg = parsed as Record<string, unknown>;
    if (msg.type !== 'emotion_update') return;
    if (!msg.data || typeof msg.data !== 'object') return;

    const next: EmotionUpdateEvent = {
      type: 'emotion_update',
      data: normalizeData(msg.data as Partial<EmotionData>),
      historical_max: msg.historical_max
        ? normalizeData(msg.historical_max as Partial<EmotionData>)
        : undefined,
      timestamp: typeof msg.timestamp === 'string' ? msg.timestamp : undefined,
    };

    setData(next.data);
    if (next.historical_max) {
      setHistoricalMax(next.historical_max);
    }
    setEvents((prev) => [...prev, next]);
  }, []);

  const { status, reconnectNow } = useWebSocket<unknown>(url, {
    onMessage: handleMessage,
  });

  return { data, historicalMax, status, events, reconnect: reconnectNow };
}

// ============= 主组件 =============

const EmotionPanel: React.FC<EmotionPanelProps> = ({
  data,
  maxValue = DEFAULT_MAX,
  title = '情感雷达（Plutchik 8 维）',
  historicalMax,
  height = DEFAULT_HEIGHT,
  wsUrl,
}) => {
  // 可选：组件内部订阅 WS（仅在显式传入 wsUrl 时启用）
  // 传入空字符串时 useWebSocket 会直接进入 error 状态，不会发起连接
  const { data: wsData, historicalMax: wsHistoricalMax, status } = useEmotionWebSocket(
    wsUrl ?? ''
  );

  // 优先使用 props 传入的数据；否则回退到 WS 推送的数据
  const liveData = useMemo<EmotionData>(() => {
    if (data && !isEmotionDataEmpty(data)) return normalizeData(data);
    if (wsData) return wsData;
    return normalizeData(data);
  }, [data, wsData]);

  const maxData = useMemo<EmotionData | null>(() => {
    if (historicalMax) return normalizeData(historicalMax);
    if (wsHistoricalMax) return wsHistoricalMax;
    return null;
  }, [historicalMax, wsHistoricalMax]);

  // ============= ECharts 配置 =============

  const indicator = useMemo(
    () =>
      EMOTION_KEYS.map((key) => ({
        name: EMOTION_LABELS_CN[key],
        max: maxValue,
      })),
    [maxValue]
  );

  const option = useMemo(() => {
    const currentValues = EMOTION_KEYS.map((k) => clamp(liveData[k], 0, maxValue));
    const maxValues = maxData
      ? EMOTION_KEYS.map((k) => clamp(maxData[k], 0, maxValue))
      : currentValues;

    return {
      // 全局动画（平滑过渡）
      animationDuration: 600,
      animationEasing: 'cubicOut' as const,
      animationDurationUpdate: 600,
      animationEasingUpdate: 'cubicOut' as const,

      color: [...EMOTION_KEYS.map((k) => colorForEmotion(k))],

      title: {
        text: title,
        left: 'center',
        top: 4,
        textStyle: {
          fontSize: 14,
          fontWeight: 500,
          color: '#262626',
        },
      },

      tooltip: {
        trigger: 'item',
        confine: true,
        formatter: (params: any) => {
          const idx = params?.dataIndex ?? 0;
          const key = EMOTION_KEYS[idx];
          const val = currentValues[idx];
          const max = maxValues[idx];
          return `<div style="font-size:12px">
            <div style="font-weight:600;margin-bottom:4px">${EMOTION_LABELS_CN[key]}（${key}）</div>
            <div>当前值：<b style="color:${colorForEmotion(key)}">${val.toFixed(2)}</b></div>
            <div>历史最高：${max.toFixed(2)}</div>
          </div>`;
        },
      },

      legend: {
        show: true,
        bottom: 0,
        data: ['当前值', '历史最高'],
        textStyle: { color: '#595959' },
      },

      radar: {
        indicator,
        shape: 'polygon' as const,
        radius: '65%',
        center: ['50%', '54%'],
        splitNumber: 4,
        axisName: {
          color: '#262626',
          fontSize: 12,
        },
        splitLine: {
          lineStyle: { color: '#d9d9d9' },
        },
        splitArea: {
          areaStyle: {
            color: ['rgba(250, 250, 250, 0.4)', 'rgba(250, 250, 250, 0.7)'],
          },
        },
        axisLine: {
          lineStyle: { color: '#bfbfbf' },
        },
      },

      series: [
        // 历史最高（淡色背景）
        ...(maxData
          ? [
              {
                name: '历史最高',
                type: 'radar' as const,
                symbol: 'circle' as const,
                symbolSize: 4,
                lineStyle: {
                  color: '#bfbfbf',
                  width: 1,
                  type: 'dashed' as const,
                },
                areaStyle: {
                  color: 'rgba(191, 191, 191, 0.15)',
                },
                itemStyle: { color: '#bfbfbf' },
                data: [
                  {
                    value: maxValues,
                    name: '历史最高',
                  },
                ],
              },
            ]
          : []),
        // 当前值（实色）
        {
          name: '当前值',
          type: 'radar' as const,
          symbol: 'circle' as const,
          symbolSize: 6,
          lineStyle: {
            color: '#1677ff',
            width: 2,
          },
          areaStyle: {
            color: 'rgba(22, 119, 255, 0.25)',
          },
          itemStyle: { color: '#1677ff' },
          data: [
            {
              value: currentValues,
              name: '当前值',
            },
          ],
        },
      ],
    };
  }, [indicator, liveData, maxData, maxValue, title]);

  // 强制 useEffect + setOption 平滑过渡
  const echartsRef = useRef<ReactECharts | null>(null);
  useEffect(() => {
    const inst = echartsRef.current?.getEchartsInstance?.();
    if (!inst) return;
    inst.setOption(option, { notMerge: false, lazyUpdate: true });
  }, [option]);

  const noData =
    isEmotionDataEmpty(liveData) &&
    (maxData === null || isEmotionDataEmpty(maxData));

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
    <Card
      title={title}
      size="small"
      extra={wsUrl ? statusTag : null}
      styles={{ body: { padding: 8 } }}
    >
      {noData ? (
        <Skeleton active paragraph={{ rows: 4 }} style={{ padding: 16 }} />
      ) : (
        <ReactECharts
          ref={(e) => {
            echartsRef.current = e;
          }}
          option={option}
          notMerge={false}
          lazyUpdate
          style={{ height, width: '100%' }}
          opts={{ renderer: 'canvas' }}
        />
      )}
      {noData && (
        <Empty
          image={Empty.PRESENTED_IMAGE_SIMPLE}
          description="暂无情感数据"
          style={{ marginTop: -120 }}
        />
      )}
    </Card>
  );
};

export default EmotionPanel;
