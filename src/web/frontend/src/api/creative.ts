// Creative REST API 客户端。
// 对应后端路由：src/web/backend/api/creative.py
// - GET    /api/creative/projects?status=...&limit=50
// - GET    /api/creative/projects/{uuid}
// - POST   /api/creative/projects
// - POST   /api/creative/projects/{uuid}/advance
// - DELETE /api/creative/projects/{uuid}
//
// 类型与 src/web/backend/schemas/creative.py 的 Pydantic v2 模型对齐：
// - CreativeProject / CreativeProjectListResponse
// - CreativeProjectCreate
// - AdvanceRequest / AdvanceResponse
// Vite dev server 已将 /api 代理到后端 8000 端口（vite.config.ts）。

import type { CreativeProject } from '@/types/creative';

// 重新导出常用类型，保持单点导入（其他类型由调用方按需直接从 '@/types/creative' 取）。
export type {
  CreativeProject,
  StoryBible,
  Chapter,
  Character,
  CreativeProjectStatus,
} from '@/types/creative';

// 列表接口的响应包：与后端 CreativeProjectListResponse 对齐
export interface CreativeProjectListResponse {
  projects: CreativeProject[];
  total: number;
}

// 续写请求体：与后端 AdvanceRequest 对齐
export interface AdvanceRequest {
  user?: string;
  hint?: string;
  advance_async?: boolean;
}

// 续写响应：与后端 AdvanceResponse 对齐
export interface AdvanceResponse {
  project_uuid: string;
  task_id: string;
  status: string;
  last_advanced_at?: string | null;
  project_status: string;
  message: string;
}

// 创建项目请求体：与后端 CreativeProjectCreate 对齐
export interface CreativeProjectCreate {
  title: string;
  work_type?: string;
  premise?: string;
  tone?: string;
  point_of_view?: string;
  target_chars?: number;
  inspiration_source?: string;
  outline?: string[];
  characters?: Record<string, unknown>[];
}

// 自定义错误：包含后端 detail 和 HTTP 状态码
export class CreativeApiError extends Error {
  status: number;
  detail: string;
  constructor(status: number, detail: string) {
    super(`Creative API error ${status}: ${detail}`);
    this.name = 'CreativeApiError';
    this.status = status;
    this.detail = detail;
  }
}

const DEFAULT_TIMEOUT_MS = 15_000;

/**
 * 统一 fetch 封装：
 * - 解析 JSON 响应
 * - 非 2xx 抛出 CreativeApiError
 * - 自动拼接 query string
 * - 支持 AbortController 超时
 */
async function request<T>(
  path: string,
  init: RequestInit = {},
  query?: Record<string, string | number | undefined>,
): Promise<T> {
  let url = path;
  if (query) {
    const params = new URLSearchParams();
    Object.entries(query).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') {
        params.append(k, String(v));
      }
    });
    const qs = params.toString();
    if (qs) url += (url.includes('?') ? '&' : '?') + qs;
  }

  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), DEFAULT_TIMEOUT_MS);

  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      signal: controller.signal,
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
        ...(init.headers || {}),
      },
    });
  } catch (err) {
    clearTimeout(timer);
    if ((err as Error).name === 'AbortError') {
      throw new CreativeApiError(0, `请求超时：${url}`);
    }
    throw new CreativeApiError(0, `网络错误：${(err as Error).message}`);
  }
  clearTimeout(timer);

  // 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  let payload: unknown = null;
  const text = await res.text();
  if (text) {
    try {
      payload = JSON.parse(text);
    } catch {
      payload = { detail: text };
    }
  }

  if (!res.ok) {
    const detail =
      (payload && typeof payload === 'object' && 'detail' in payload
        ? String((payload as { detail: unknown }).detail)
        : null) || `HTTP ${res.status}`;
    throw new CreativeApiError(res.status, detail);
  }

  return payload as T;
}

// =====================================================================
// 对外 API
// =====================================================================

/**
 * 列出创作项目。
 * GET /api/creative/projects?status=...&limit=50
 * @param status 可选过滤条件：active / paused / completed / drafting / finished
 * @param limit 返回上限（1-200），默认 50
 */
export async function listProjects(
  status?: string,
  limit: number = 50,
): Promise<CreativeProjectListResponse> {
  return request<CreativeProjectListResponse>(
    '/api/creative/projects',
    { method: 'GET' },
    { status, limit },
  );
}

/**
 * 读取项目详情（含 Story Bible）。
 * GET /api/creative/projects/{uuid}
 * 404 时抛 CreativeApiError(404, ...)。
 */
export async function getProject(uuid: string): Promise<CreativeProject> {
  if (!uuid) {
    throw new CreativeApiError(400, 'project uuid is required');
  }
  return request<CreativeProject>(
    `/api/creative/projects/${encodeURIComponent(uuid)}`,
    { method: 'GET' },
  );
}

/**
 * 创建创作项目。
 * POST /api/creative/projects
 * 返回 201 + CreativeProject。
 */
export async function createProject(
  payload: CreativeProjectCreate,
): Promise<CreativeProject> {
  return request<CreativeProject>('/api/creative/projects', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * 触发续写。默认异步模式：返回 task_id，进度通过 /ws/events 的
 * 'creative_progress' 事件推送。
 * POST /api/creative/projects/{uuid}/advance
 * 404 时抛 CreativeApiError(404, ...)。
 */
export async function advanceProject(
  uuid: string,
  payload: AdvanceRequest = {},
): Promise<AdvanceResponse> {
  if (!uuid) {
    throw new CreativeApiError(400, 'project uuid is required');
  }
  return request<AdvanceResponse>(
    `/api/creative/projects/${encodeURIComponent(uuid)}/advance`,
    {
      method: 'POST',
      // body 可缺省；后端会使用 AdvanceRequest() 默认值
      body: JSON.stringify(payload),
    },
  );
}

/**
 * 删除项目。
 * DELETE /api/creative/projects/{uuid}
 * 成功返回 204 No Content。
 */
export async function deleteProject(uuid: string): Promise<void> {
  if (!uuid) {
    throw new CreativeApiError(400, 'project uuid is required');
  }
  await request<void>(
    `/api/creative/projects/${encodeURIComponent(uuid)}`,
    { method: 'DELETE' },
  );
}
