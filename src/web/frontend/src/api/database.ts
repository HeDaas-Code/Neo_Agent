// Database API 客户端
// 包装 `/api/database/*` 三个端点：tables 列表、单表分页查询、按 uuid 删除（带 X-Confirm 二次确认头）。
// 与后端 schemas/database.py 契约对齐。

import axios, { AxiosError } from 'axios';
import type { Row } from '@/types/database';

// ----------------------------------------------------------------------
// 类型契约（与后端 Pydantic v2 模型对齐）
// ----------------------------------------------------------------------

/** `GET /api/database/tables` 响应 */
export interface TablesListResponse {
  tables: string[];
  total: number;
}

/** `GET /api/database/{table}?limit=&offset=` 响应 */
export interface TableDataResponse {
  table: string;
  rows: Row[];
  total: number;
}

/** `DELETE /api/database/{table}/{uuid}` 响应 */
export interface DeleteResponse {
  table: string;
  uuid: string;
  deleted: boolean;
}

/** 后端统一错误响应：`{"error": "..."}` */
export interface ApiErrorBody {
  error: string;
}

// ----------------------------------------------------------------------
// axios 实例：走 vite dev server 的 `/api` 代理，无需写 baseURL
// ----------------------------------------------------------------------

const http = axios.create({
  timeout: 15000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// ----------------------------------------------------------------------
// 错误处理工具
// ----------------------------------------------------------------------

/**
 * 把 axios 错误规整为「中文用户可读」的字符串。
 * 优先使用后端 `{"error": "..."}` 字段（项目硬约束：所有 4xx 响应都是这个格式）。
 */
export const formatApiError = (err: unknown): string => {
  if (axios.isAxiosError(err)) {
    const axErr = err as AxiosError<ApiErrorBody>;
    const backendMsg = axErr.response?.data?.error;
    if (backendMsg) return backendMsg;
    if (axErr.response?.status === 400) {
      return '请求参数错误（400）';
    }
    if (axErr.response?.status === 404) {
      return '未找到对应记录（404）';
    }
    if (axErr.code === 'ECONNABORTED') {
      return '请求超时，请检查后端服务';
    }
    if (axErr.message) return axErr.message;
  }
  if (err instanceof Error) return err.message;
  return '未知错误';
};

// ----------------------------------------------------------------------
// 1) GET /api/database/tables
// ----------------------------------------------------------------------

/**
 * 列出白名单中实际存在的业务表。
 * @returns 表名列表 + total
 */
export const listTables = async (): Promise<TablesListResponse> => {
  const res = await http.get<TablesListResponse>('/api/database/tables');
  return res.data;
};

// ----------------------------------------------------------------------
// 2) GET /api/database/{table}?limit=100&offset=0
// ----------------------------------------------------------------------

/**
 * 分页查询指定表的数据。
 * @param table 表名（必须命中后端白名单，否则 400）
 * @param limit 每页行数，默认 100
 * @param offset 偏移量，默认 0
 */
export const getTableData = async (
  table: string,
  limit = 100,
  offset = 0,
): Promise<TableDataResponse> => {
  const res = await http.get<TableDataResponse>(
    `/api/database/${encodeURIComponent(table)}`,
    {
      params: { limit, offset },
    },
  );
  return res.data;
};

// ----------------------------------------------------------------------
// 3) DELETE /api/database/{table}/{uuid}  ——  必须带 X-Confirm: true
// ----------------------------------------------------------------------

/**
 * 按 uuid 删除单条记录。
 * 注意：后端硬约束要求请求头 `X-Confirm: true`，缺失 → 400。
 * @param table 表名
 * @param uuid 记录 uuid
 */
export const deleteRecord = async (
  table: string,
  uuid: string,
): Promise<DeleteResponse> => {
  const res = await http.delete<DeleteResponse>(
    `/api/database/${encodeURIComponent(table)}/${encodeURIComponent(uuid)}`,
    {
      // 必须显式声明二次确认头；缺失或非 "true" → 后端 400
      headers: {
        'X-Confirm': 'true',
      },
    },
  );
  return res.data;
};
