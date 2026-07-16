/**
 * Knowledge 页面共享类型定义。
 *
 * 与后端 /api/knowledge/* 端点契约对齐：
 *   - KnowledgeEntityRow：数据库原始行（仅含 entities 表字段，必要时附 definition）
 *   - Entity：前端 UI 期望的展示模型（含 confidence/mention_count/metadata/related_uuids
 *     等后端暂未直接返回的字段，由适配函数填默认值）
 *
 * 后端 schema 详见：src/web/backend/schemas/knowledge.py
 */

export type EntityCategory =
  | 'person'
  | 'project'
  | 'concept'
  | 'location'
  | 'organization'
  | 'event';

/** 后端返回的实体原始行（entities 表 + 可选 definition 字段） */
export interface KnowledgeEntityRow {
  uuid: string;
  name: string;
  normalized_name?: string;
  created_at?: string;
  updated_at?: string;
  /** 从 entity_definitions.type 透传；不在白名单时视为 'concept' */
  category?: string;
  /** 从 entity_definitions.content 透传 */
  description?: string;
}

/** 前端 UI 期望的实体展示模型 */
export interface Entity {
  /** 节点唯一 ID,前端选中态用此字段 */
  uuid: string;
  name: string;
  category: EntityCategory;
  /** 0-1,实体被识别时的置信度（后端暂未返回，使用默认 0.5） */
  confidence: number;
  /** 在对话/记忆中出现的次数（后端暂未返回，使用默认 0） */
  mention_count: number;
  /** 最近一次更新时间 ISO 字符串 */
  updated_at: string;
  /** Markdown 形式的详情描述 */
  description: string;
  /** 自由形式元数据 (来源、标签 等) */
  metadata: Record<string, string | number | boolean>;
  /** 与该实体直接相关的其他实体 uuid */
  related_uuids: string[];
}

export interface Relation {
  /** 源实体 uuid */
  source: string;
  /** 目标实体 uuid */
  target: string;
  /** 关系名称,例如 "works_on" / "located_in" / "knows" */
  relation: string;
  /** 关系在文本中出现的次数,用于决定线宽 */
  mention_count: number;
  /** 可选描述 */
  description?: string;
}

/** 后端允许的分类白名单，用于把任意字符串归一化到已知枚举 */
export const KNOWN_ENTITY_CATEGORIES: readonly EntityCategory[] = [
  'person',
  'project',
  'concept',
  'location',
  'organization',
  'event',
];
