import { useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import type { Entity, EntityCategory, Relation } from '../types/knowledge';

/**
 * KnowledgeGraph —— 用 ECharts 渲染的实体关系图。
 *
 * 设计要点:
 * - 节点 = Entity,边 = Relation
 * - 节点颜色按 category 映射 (固定调色板)
 * - 边宽度按 mention_count 线性映射
 * - 节点点击通过 onNodeClick 回调把 uuid 抛给父组件
 * - 使用力导向布局 (force / repulsion)
 */

export interface KnowledgeGraphProps {
  entities: Entity[];
  relations: Relation[];
  /** 当前高亮的实体 uuid(用于给节点加边框) */
  selectedUuid?: string;
  onNodeClick?: (uuid: string) => void;
  /** 容器高度,默认 480 */
  height?: number;
}

const CATEGORY_COLORS: Record<EntityCategory, string> = {
  person: '#1677ff',
  project: '#722ed1',
  concept: '#13c2c2',
  location: '#52c41a',
  organization: '#fa8c16',
  event: '#eb2f96',
};

const CATEGORY_LABELS: Record<EntityCategory, string> = {
  person: '人物',
  project: '项目',
  concept: '概念',
  location: '地点',
  organization: '组织',
  event: '事件',
};

/**
 * 把 mention_count 映射为 ECharts edge 线宽 (1 ~ 8 px)。
 * mention_count 越大线越粗,直观体现关联强度。
 */
function widthForMention(count: number, maxCount: number): number {
  if (maxCount <= 0) return 1;
  const ratio = count / maxCount;
  return Math.max(1, Math.min(8, 1 + ratio * 7));
}

export default function KnowledgeGraph({
  entities,
  relations,
  selectedUuid,
  onNodeClick,
  height = 480,
}: KnowledgeGraphProps): JSX.Element {
  const option = useMemo(() => {
    const maxMention = relations.reduce(
      (m, r) => Math.max(m, r.mention_count),
      0,
    );

    const nodes = entities.map((e) => ({
      id: e.uuid,
      name: e.name,
      symbolSize: Math.max(20, Math.min(60, 20 + e.mention_count * 0.4)),
      category: e.category,
      // 用 itemStyle 同时表达"分类色"和"选中高亮"
      itemStyle: {
        color: CATEGORY_COLORS[e.category],
        borderColor: selectedUuid === e.uuid ? '#000' : '#fff',
        borderWidth: selectedUuid === e.uuid ? 3 : 1.5,
        shadowBlur: 6,
        shadowColor: 'rgba(0,0,0,0.15)',
      },
      label: { show: true, fontSize: 12 },
      value: e.confidence,
    }));

    const links = relations.map((r) => ({
      source: r.source,
      target: r.target,
      name: r.relation,
      lineStyle: {
        width: widthForMention(r.mention_count, maxMention),
        color: '#bfbfbf',
        curveness: 0.1,
      },
      value: r.mention_count,
    }));

    return {
      tooltip: {
        trigger: 'item',
        formatter: (params: { dataType?: string; data?: Record<string, unknown> }) => {
          if (params.dataType === 'node' && params.data) {
            const d = params.data as { name: string; category: EntityCategory; value: number };
            return `<b>${d.name}</b><br/>类型: ${CATEGORY_LABELS[d.category]}<br/>置信度: ${(
              d.value * 100
            ).toFixed(0)}%`;
          }
          if (params.dataType === 'edge' && params.data) {
            const d = params.data as { name: string; value: number };
            return `关系: <b>${d.name}</b><br/>提及次数: ${d.value}`;
          }
          return '';
        },
      },
      legend: [
        {
          data: Object.keys(CATEGORY_LABELS).map((k) => ({
            name: CATEGORY_LABELS[k as EntityCategory],
            icon: 'circle',
          })),
          textStyle: { fontSize: 11 },
          top: 0,
        },
      ],
      series: [
        {
          type: 'graph',
          layout: 'force',
          roam: true,
          draggable: true,
          animation: true,
          data: nodes,
          links,
          categories: Object.keys(CATEGORY_COLORS).map((k) => ({
            name: CATEGORY_LABELS[k as EntityCategory],
            itemStyle: { color: CATEGORY_COLORS[k as EntityCategory] },
          })),
          force: {
            repulsion: 260,
            edgeLength: [60, 140],
            gravity: 0.05,
            friction: 0.2,
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: { width: 4 },
          },
        },
      ],
    } as Record<string, unknown>;
  }, [entities, relations, selectedUuid]);

  const onEvents = useMemo(
    () => ({
      click: (event: { dataType?: string; data?: { id?: string } }) => {
        if (event.dataType === 'node' && event.data?.id && onNodeClick) {
          onNodeClick(event.data.id);
        }
      },
    }),
    [onNodeClick],
  );

  return (
    <ReactECharts
      option={option}
      onEvents={onEvents}
      style={{ height, width: '100%' }}
      notMerge
      lazyUpdate
    />
  );
}
