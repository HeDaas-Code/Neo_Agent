/**
 * Knowledge REST API 客户端（Stage C.1）。
 *
 * 端点契约（对应后端 src/web/backend/api/knowledge.py）：
 *   GET    /api/knowledge/search?q=&limit=        关键词搜索
 *   GET    /api/knowledge?limit=                  列出所有实体
 *   POST   /api/knowledge                         新增实体
 *   DELETE /api/knowledge/{uuid}                  删除实体
 *
 * 设计要点：
 * 1. 基于 axios（package.json 已声明 ^1.6.7），通过 Vite dev proxy 转发到 :8000。
 * 2. 所有方法返回后端原始 JSON；Entity 字段补全由 toEntity() 适配。
 * 3. 错误统一通过 antd message.error 提示，并向上抛出供调用方决定是否继续。
 * 4. 搜索关键词为空时回退到 listEntities，避免后端 q min_length=1 校验失败。
 */

import axios, { AxiosError } from 'axios';
import { message } from 'antd';
import {
  KNOWN_ENTITY_CATEGORIES,
  type Entity,
  type EntityCategory,
  type KnowledgeEntityRow,
} from '../types/knowledge';

const API_BASE = '/api/knowledge';

/**
 * 把后端返回的任意字符串归一化到 EntityCategory 枚举。
 * 不在白名单时回落到 'concept'，保证 UI 渲染不崩。
 */
function normalizeCategory(input: string | undefined | null): EntityCategory {
  if (!input) return 'concept';
  const value = input.trim().toLowerCase();
  if ((KNOWN_ENTITY_CATEGORIES as readonly string[]).includes(value)) {
    return value as EntityCategory;
  }
  return 'concept';
}

/**
 * 把后端 KnowledgeEntityRow 适配为前端 UI 使用的 Entity。
 * 后端 entities 表本身只含 uuid/name/normalized_name/created_at/updated_at；
 * category/description 由 search_knowledge() 通过 definition 表补齐；
 * confidence/mention_count/metadata/related_uuids 后端暂无直接字段，使用默认值。
 */
export function toEntity(row: KnowledgeEntityRow): Entity {
  return {
    uuid: String(row.uuid ?? ''),
    name: String(row.name ?? ''),
    category: normalizeCategory(row.category),
    // 后端暂未提供 confidence，UI 期望 0-1，这里给中性默认值 0.5
    confidence: 0.5,
    // 后端暂未提供 mention_count，前端用 0 占位
    mention_count: 0,
    updated_at: row.updated_at || row.created_at || new Date().toISOString(),
    description: row.description ?? '',
    metadata: {},
    related_uuids: [],
  };
}

export interface SearchResponsePayload {
  results: KnowledgeEntityRow[];
  total: number;
}

export interface CreateResponsePayload {
  uuid: string;
  entity_name: string;
  created: boolean;
}

export interface DeleteResponsePayload {
  uuid: string;
  deleted: boolean;
}

/** 提取后端错误信息：优先用 {"error": "..."}，否则用 axios message。 */
function extractErrorMessage(err: unknown, fallback: string): string {
  const ax = err as AxiosError<{ error?: string; detail?: string }>;
  const data = ax?.response?.data as { error?: string; detail?: string } | undefined;
  if (data?.error) return data.error;
  if (data?.detail) return data.detail;
  if (ax?.message) return ax.message;
  return fallback;
}

/**
 * 搜索实体。
 *  - q 为空字符串时回退到 listEntities()（后端 search 要求 q.min_length=1）。
 *  - 默认 limit 50 足以覆盖演示场景。
 */
export async function searchEntities(q: string = '', limit: number = 50): Promise<Entity[]> {
  const keyword = (q ?? '').trim();
  if (!keyword) {
    return listEntities(limit);
  }
  try {
    const { data } = await axios.get<SearchResponsePayload>(`${API_BASE}/search`, {
      params: { q: keyword, limit },
    });
    const rows = Array.isArray(data?.results) ? data.results : [];
    return rows.map(toEntity);
  } catch (err) {
    const msg = extractErrorMessage(err, '搜索知识库失败');
    message.error(`搜索失败:${msg}`);
    throw err;
  }
}

/**
 * 列出所有实体。
 * 后端 /api/knowledge?limit= 仅返回 entities 行，不含 definition 字段，
 * 所以 description/category 会落默认值。
 */
export async function listEntities(limit: number = 50): Promise<Entity[]> {
  try {
    const { data } = await axios.get<SearchResponsePayload>(API_BASE, {
      params: { limit },
    });
    const rows = Array.isArray(data?.results) ? data.results : [];
    return rows.map(toEntity);
  } catch (err) {
    const msg = extractErrorMessage(err, '列出知识库失败');
    message.error(`列出失败:${msg}`);
    throw err;
  }
}

export interface CreateEntityPayload {
  name: string;
  category: EntityCategory;
  description?: string;
  related_info?: Record<string, unknown>;
}

/**
 * 新增实体。
 * 前端表单字段 {name, category, description} 映射到后端
 * {entity_name, category, description, related_info}。
 */
export async function createEntity(
  payload: CreateEntityPayload,
): Promise<CreateResponsePayload> {
  try {
    const { data } = await axios.post<CreateResponsePayload>(API_BASE, {
      entity_name: payload.name,
      category: payload.category,
      description: payload.description ?? '',
      related_info: payload.related_info,
    });
    message.success(`已新增实体:${data?.entity_name ?? payload.name}`);
    return data;
  } catch (err) {
    const msg = extractErrorMessage(err, '创建实体失败');
    message.error(`创建失败:${msg}`);
    throw err;
  }
}

/** 删除实体,后端返回 {uuid, deleted: true}。 */
export async function deleteEntity(uuid: string): Promise<DeleteResponsePayload> {
  try {
    const { data } = await axios.delete<DeleteResponsePayload>(
      `${API_BASE}/${encodeURIComponent(uuid)}`,
    );
    message.success(`已删除实体:${uuid}`);
    return data;
  } catch (err) {
    const msg = extractErrorMessage(err, '删除实体失败');
    message.error(`删除失败:${msg}`);
    throw err;
  }
}
