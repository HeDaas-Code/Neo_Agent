/**
 * NPS 前端 API 客户端。
 * 对接后端 /api/nps 路由：
 *   GET    /api/nps           列出已注册 NPS
 *   POST   /api/nps/register  注册新 NPS
 *   POST   /api/nps/invoke    调用 NPS
 *
 * 字段命名约定：
 *   后端使用 `parameters` (Record<string, any>) 与 `registered_at`；
 *   前端页面使用 `params` (NPSParam[]) 与 `created_at`。
 *   在此模块内做映射，避免污染页面层。
 */

import axios, { AxiosError, AxiosResponse } from 'axios';
import type { NPS, NPSParam, NPSType, NPSConfigFormValues } from '../types/nps';

// =====================================================================
// 后端契约类型
// =====================================================================

/** 后端 NPS 条目形状（GET /api/nps / POST /api/nps/register 的响应）。 */
export interface NpsEntry {
  uuid: string;
  name: string;
  description: string;
  version: string;
  parameters: Record<string, any>;
  registered_at: string;
  // 可选：UI 需要的扩展字段（后端可能返回）
  enabled?: boolean;
  nps_type?: NPSType;
  call_count?: number;
  last_called_at?: string | null;
}

/** 注册 NPS 的请求体（POST /api/nps/register）。 */
export interface NpsRegisterPayload {
  name: string;
  description: string;
  parameters: Record<string, any>;
  version?: string;
  enabled?: boolean;
  nps_type?: NPSType;
}

/** 调用 NPS 的请求体（POST /api/nps/invoke）。 */
export interface NpsInvokePayload {
  uuid: string;
  args: Record<string, any>;
}

/** 调用 NPS 的响应（POST /api/nps/invoke）。 */
export interface NpsInvokeResponse {
  result: unknown;
  status: string;
  executed_at: string;
}

/** 注册 NPS 的入参（页面 → API 模块）。 */
export type NpsRegisterInput = NPSConfigFormValues;

// =====================================================================
// axios 实例
// =====================================================================

// 走 vite proxy：/api → http://localhost:8000
const http = axios.create({
  baseURL: '/api',
  timeout: 15000,
});

// =====================================================================
// 内部工具：字段映射
// =====================================================================

/**
 * 把后端 NpsEntry 映射为前端 NPS 形状。
 * 后端 parameters (dict) → 前端 params (NPSParam[])。
 */
export function toFrontendNps(entry: NpsEntry): NPS {
  const params: NPSParam[] = Object.entries(entry.parameters ?? {}).map(
    ([key, value]) => ({
      key,
      // 复杂值序列化为字符串，避免丢信息
      value:
        typeof value === 'string'
          ? value
          : value == null
            ? ''
            : JSON.stringify(value),
    }),
  );
  return {
    uuid: entry.uuid,
    name: entry.name,
    description: entry.description ?? '',
    nps_type: (entry.nps_type ?? 'function') as NPSType,
    params,
    enabled: entry.enabled ?? true,
    call_count: entry.call_count ?? 0,
    last_called_at: entry.last_called_at ?? null,
    created_at: entry.registered_at ?? new Date().toISOString(),
  };
}

/**
 * 把前端 NPSParam[] 转换回后端 parameters (dict)。
 * 过滤掉 key 为空的项。
 */
function paramsToParameters(
  params: NPSParam[] | undefined,
): Record<string, any> {
  if (!params) return {};
  const out: Record<string, any> = {};
  for (const p of params) {
    const k = (p.key ?? '').trim();
    if (!k) continue;
    out[k] = p.value ?? '';
  }
  return out;
}

/** 兼容多种列表响应形态（数组 / {results} / {items} / {data}）。 */
function unwrapList(payload: unknown): NpsEntry[] {
  if (Array.isArray(payload)) return payload as NpsEntry[];
  if (payload && typeof payload === 'object') {
    const obj = payload as Record<string, unknown>;
    for (const key of ['results', 'items', 'data', 'list']) {
      const v = obj[key];
      if (Array.isArray(v)) return v as NpsEntry[];
    }
  }
  return [];
}

/**
 * 解析 axios 错误，提取可读中文消息。
 */
function extractErrorMessage(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const axErr = err as AxiosError<{ error?: string; detail?: string; message?: string }>;
    if (axErr.response?.data) {
      const data = axErr.response.data;
      if (typeof data === 'string') return data;
      if (typeof data === 'object' && data !== null) {
        return (
          data.error ||
          data.detail ||
          data.message ||
          axErr.message ||
          fallback
        );
      }
    }
    return axErr.message || fallback;
  }
  if (err instanceof Error) return err.message || fallback;
  return fallback;
}

// =====================================================================
// 公开 API
// =====================================================================

/**
 * 列出已注册的 NPS。
 * 失败时抛 Error（message 为可读中文），由调用方捕获后 message.error 显示。
 */
export async function listNps(): Promise<NPS[]> {
  try {
    const resp: AxiosResponse<unknown> = await http.get('/nps');
    const raw = unwrapList(resp.data);
    return raw.map(toFrontendNps);
  } catch (err) {
    throw new Error(extractErrorMessage(err, '获取 NPS 列表失败'));
  }
}

/**
 * 注册新 NPS。
 * 入参使用页面表单形状；内部转换为后端契约。
 */
export async function registerNps(
  payload: NpsRegisterInput,
): Promise<NPS> {
  try {
    const body: NpsRegisterPayload = {
      name: payload.name,
      description: payload.description ?? '',
      parameters: paramsToParameters(payload.params),
      enabled: payload.enabled,
      nps_type: payload.nps_type,
      version: '1.0.0',
    };
    const resp = await http.post<NpsEntry>('/nps/register', body);
    if (!resp.data || !resp.data.uuid) {
      throw new Error('注册响应缺少 uuid');
    }
    return toFrontendNps(resp.data);
  } catch (err) {
    throw new Error(extractErrorMessage(err, '注册 NPS 失败'));
  }
}

/**
 * 调用已注册的 NPS。
 * 失败时抛 Error，由调用方处理。
 */
export async function invokeNps(
  payload: NpsInvokePayload,
): Promise<NpsInvokeResponse> {
  try {
    const resp = await http.post<NpsInvokeResponse>('/nps/invoke', payload);
    if (!resp.data || typeof resp.data !== 'object') {
      throw new Error('调用响应格式异常');
    }
    return resp.data;
  } catch (err) {
    throw new Error(extractErrorMessage(err, '调用 NPS 失败'));
  }
}

// 兼容命名空间导入：import * as npsApi from '../../api/nps'
export default {
  listNps,
  registerNps,
  invokeNps,
  toFrontendNps,
};
