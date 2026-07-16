/**
 * Knowledge 页面 mock 数据（Stage C.1 历史遗留）。
 *
 * 当前页面已切换到 /api/knowledge 真接口（见 src/api/knowledge.ts）；
 * 本文件保留 mock 数据仅供 Storybook / 离线调试使用,不再被业务页面引用。
 *
 * 类型已迁移到 src/types/knowledge.ts,这里做 re-export 以保持历史 import 路径可用。
 */

import type { Entity, EntityCategory, Relation } from '../types/knowledge';

export type { Entity, EntityCategory, Relation };

export const mockEntities: Entity[] = [
  {
    uuid: 'ent-001',
    name: '张明',
    category: 'person',
    confidence: 0.96,
    mention_count: 42,
    updated_at: '2026-07-10T08:12:00.000Z',
    description:
      '## 张明\n\n- 角色:Neo_Agent 项目的**后端主程**\n- 常用语言:Python / Go\n- 负责模块:`agent.runtime`、`memory.kb`',
    metadata: {
      email: 'zhangming@example.com',
      team: 'agent-core',
      seniority: 'senior',
    },
    related_uuids: ['ent-002', 'ent-003', 'ent-005'],
  },
  {
    uuid: 'ent-002',
    name: 'Neo_Agent',
    category: 'project',
    confidence: 0.99,
    mention_count: 88,
    updated_at: '2026-07-12T10:30:00.000Z',
    description:
      '## Neo_Agent\n\n跨桌面 / Web 的多 Agent 协作框架。当前阶段 C.1 (Knowledge) 与 C.2 (Schedule) 页面开发。\n\n### 里程碑\n- A: 原型\n- B: Web 脚手架\n- **C: 业务页面**\- D: 联调上线',
    metadata: {
      version: '0.4.0',
      repo: 'github.com/neo-agent/neo_agent',
      status: 'active',
    },
    related_uuids: ['ent-001', 'ent-003', 'ent-004', 'ent-005'],
  },
  {
    uuid: 'ent-003',
    name: 'Tkinter',
    category: 'concept',
    confidence: 0.92,
    mention_count: 27,
    updated_at: '2026-06-21T14:05:00.000Z',
    description:
      '## Tkinter\n\nPython 标准库 GUI 工具包。Neo_Agent 第一版桌面端使用 Tkinter,目前正迁移到 Web (React + antd)。',
    metadata: { language: 'python', status: 'legacy' },
    related_uuids: ['ent-002', 'ent-004'],
  },
  {
    uuid: 'ent-004',
    name: 'React',
    category: 'concept',
    confidence: 0.95,
    mention_count: 33,
    updated_at: '2026-07-05T09:48:00.000Z',
    description:
      '## React\n\nWeb 前端框架 (18.x)。配合 antd 5 / ECharts 实现 Neo_Agent Web 端的全部业务页面。',
    metadata: { version: '18.2.0', license: 'MIT' },
    related_uuids: ['ent-002', 'ent-003'],
  },
  {
    uuid: 'ent-005',
    name: '上海',
    category: 'location',
    confidence: 0.98,
    mention_count: 15,
    updated_at: '2026-07-01T03:20:00.000Z',
    description: '## 上海\n\nNeo_Agent 团队主要办公地点。',
    metadata: { country: 'CN', timezone: 'Asia/Shanghai' },
    related_uuids: ['ent-001', 'ent-002', 'ent-006'],
  },
  {
    uuid: 'ent-006',
    name: 'NeoAI Co.',
    category: 'organization',
    confidence: 0.97,
    mention_count: 19,
    updated_at: '2026-07-09T11:00:00.000Z',
    description:
      '## NeoAI Co.\n\nNeo_Agent 的运营公司,2024 年成立于上海。专注于多 Agent 协作平台。',
    metadata: { founded: 2024, employees: 42 },
    related_uuids: ['ent-005', 'ent-002'],
  },
  {
    uuid: 'ent-007',
    name: 'CPRS 2026',
    category: 'event',
    confidence: 0.89,
    mention_count: 8,
    updated_at: '2026-07-08T16:42:00.000Z',
    description:
      '## CPRS 2026\n\n中国推荐的 AI 顶会。Neo_Agent 团队拟在 Industrial Track 投递一篇 demo 论文。',
    metadata: { date: '2026-11-12', city: '杭州' },
    related_uuids: ['ent-002', 'ent-006'],
  },
  {
    uuid: 'ent-008',
    name: '王晓',
    category: 'person',
    confidence: 0.93,
    mention_count: 21,
    updated_at: '2026-07-11T07:30:00.000Z',
    description:
      '## 王晓\n\n前端工程师,负责 Neo_Agent Web 端的 Knowledge / Schedule / Chat 页面。',
    metadata: { team: 'web-frontend', seniority: 'mid' },
    related_uuids: ['ent-001', 'ent-002', 'ent-004'],
  },
];

/**
 * 实体之间的关联 (entity_related_info)。
 * 边的粗细按 mention_count 自动映射。
 * 注：后端当前未提供 /api/knowledge/relations 端点,生产中 relations 为空数组。
 */
export const mockRelations: Relation[] = [
  {
    source: 'ent-001',
    target: 'ent-002',
    relation: 'contributes_to',
    mention_count: 12,
    description: '张明是 Neo_Agent 的核心开发',
  },
  {
    source: 'ent-002',
    target: 'ent-003',
    relation: 'uses',
    mention_count: 7,
  },
  {
    source: 'ent-002',
    target: 'ent-004',
    relation: 'migrates_to',
    mention_count: 9,
    description: 'Web 化阶段改用 React',
  },
  {
    source: 'ent-001',
    target: 'ent-005',
    relation: 'works_in',
    mention_count: 4,
  },
  {
    source: 'ent-006',
    target: 'ent-005',
    relation: 'located_in',
    mention_count: 5,
  },
  {
    source: 'ent-006',
    target: 'ent-002',
    relation: 'owns',
    mention_count: 6,
  },
  {
    source: 'ent-008',
    target: 'ent-002',
    relation: 'contributes_to',
    mention_count: 8,
  },
  {
    source: 'ent-008',
    target: 'ent-001',
    relation: 'collaborates_with',
    mention_count: 5,
  },
  {
    source: 'ent-008',
    target: 'ent-004',
    relation: 'specializes_in',
    mention_count: 6,
  },
  {
    source: 'ent-007',
    target: 'ent-002',
    relation: 'targets',
    mention_count: 3,
  },
  {
    source: 'ent-007',
    target: 'ent-006',
    relation: 'organized_by',
    mention_count: 2,
  },
];
