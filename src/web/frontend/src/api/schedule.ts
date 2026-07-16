/**
 * Schedule API 客户端
 *
 * 与后端 `src/web/backend/api/schedule.py` 对齐:
 * - GET    /api/schedule?date=YYYY-MM-DD
 * - GET    /api/schedule?from=YYYY-MM-DD&to=YYYY-MM-DD
 * - POST   /api/schedule
 * - PUT    /api/schedule/{id}
 * - DELETE /api/schedule/{id}
 * - POST   /api/schedule/{id}/confirm?confirmed=true
 *
 * 设计要点:
 * - 失败统一抛 Error(message=后端 detail 或 axios message),由调用方决定是否弹 message.error
 * - 字段映射:后端 `id`(int) → 前端 `uuid`(string)
 * - 协作字段后端 DTO 未暴露,默认 false/undefined(后续若 backend 扩展可自动读取)
 */

import axios, { type AxiosError } from 'axios';

export type SchedulePriority = 'low' | 'normal' | 'high';
export type ScheduleType = 'personal' | 'work' | 'family';
export type ScheduleStatus = 'pending' | 'confirmed' | 'done' | 'cancelled';
export type CollaboratorStatus = 'confirmed' | 'pending' | 'declined';

/** 前端 UI 使用的日程视图(字段超集,后端未给的协作字段给默认值) */
export interface Schedule {
  /** 数据库主键(后端 int) */
  id?: number;
  /** 字符串形式的主键,UI 列表的 rowKey */
  uuid: string;
  title: string;
  description: string;
  /** ISO 字符串 */
  start_time: string;
  /** ISO 字符串 */
  end_time: string;
  priority: SchedulePriority;
  schedule_type: ScheduleType;
  status: ScheduleStatus;
  /** 是否协作日程 */
  is_collaborative: boolean;
  /** 协作方状态 */
  collaborator_status?: CollaboratorStatus;
  /** 协作人名称 */
  collaborator_name?: string;
}

/** 新建日程请求体(对应后端 ScheduleCreate) */
export interface ScheduleCreatePayload {
  title: string;
  description?: string;
  start_time: string;
  end_time: string;
  priority?: SchedulePriority;
  schedule_type?: ScheduleType;
}

/** 更新日程请求体(对应后端 ScheduleUpdate) */
export interface ScheduleUpdatePayload {
  title?: string;
  description?: string;
  start_time?: string;
  end_time?: string;
  priority?: SchedulePriority;
  status?: ScheduleStatus;
}

const client = axios.create({ baseURL: '/api' });

/** 后端原始 DTO 行(容忍空字段) */
interface RawScheduleRow {
  id?: number | string;
  uuid?: string;
  title?: string;
  description?: string | null;
  start_time?: string;
  end_time?: string | null;
  priority?: string;
  status?: string;
  schedule_type?: string;
  is_collaborative?: number | boolean | null;
  collaborator_status?: string | null;
  collaborator_name?: string | null;
  confirmed?: number | boolean | null;
}

function normalizePriority(v?: string | null): SchedulePriority {
  if (v === 'low' || v === 'high') return v;
  return 'normal';
}

function normalizeType(v?: string | null): ScheduleType {
  if (v === 'work' || v === 'family') return v;
  return 'personal';
}

function normalizeStatus(v?: string | null): ScheduleStatus {
  if (v === 'confirmed' || v === 'done' || v === 'cancelled') return v;
  return 'pending';
}

function normalizeCollaboratorStatus(
  v?: string | null,
): CollaboratorStatus | undefined {
  if (v === 'confirmed' || v === 'declined') return v;
  if (v === 'pending') return 'pending';
  return undefined;
}

/** 后端 DTO 行 → 前端 Schedule */
function mapRow(row: RawScheduleRow): Schedule {
  const idNum =
    row.id !== undefined && row.id !== null ? Number(row.id) : undefined;
  const safeId = idNum !== undefined && Number.isFinite(idNum) ? idNum : undefined;
  return {
    id: safeId,
    uuid: String(row.uuid || safeId || ''),
    title: String(row.title || ''),
    description: row.description ?? '',
    start_time: String(row.start_time || ''),
    end_time: row.end_time ? String(row.end_time) : '',
    priority: normalizePriority(row.priority),
    schedule_type: normalizeType(row.schedule_type),
    status: normalizeStatus(row.status),
    is_collaborative: Boolean(row.is_collaborative),
    collaborator_status: normalizeCollaboratorStatus(row.collaborator_status),
    collaborator_name: row.collaborator_name ?? undefined,
  };
}

/** 提取后端错误信息(优先 detail) */
function unwrapError(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const ax = err as AxiosError<{ detail?: string | unknown[] }>;
    const detail = ax.response?.data?.detail;
    if (typeof detail === 'string' && detail) return detail;
    if (Array.isArray(detail)) {
      const joined = detail
        .map((d) =>
          typeof d === 'object' ? JSON.stringify(d) : String(d),
        )
        .join('; ');
      if (joined) return joined;
    }
    return ax.message || fallback;
  }
  if (err instanceof Error && err.message) return err.message;
  return fallback;
}

/**
 * 按日期查询日程。
 * @param date YYYY-MM-DD
 */
export async function listByDate(date: string): Promise<Schedule[]> {
  try {
    const { data } = await client.get<{ items?: RawScheduleRow[] }>('/schedule', {
      params: { date },
    });
    return (data.items || []).map(mapRow);
  } catch (err) {
    throw new Error(unwrapError(err, '查询日程失败'));
  }
}

/**
 * 按日期区间查询日程。
 * @param from YYYY-MM-DD
 * @param to   YYYY-MM-DD
 */
export async function listByRange(from: string, to: string): Promise<Schedule[]> {
  try {
    const { data } = await client.get<{ items?: RawScheduleRow[] }>('/schedule', {
      params: { from, to },
    });
    return (data.items || []).map(mapRow);
  } catch (err) {
    throw new Error(unwrapError(err, '查询日程区间失败'));
  }
}

/**
 * 新建日程。
 */
export async function create(payload: ScheduleCreatePayload): Promise<Schedule> {
  try {
    const { data } = await client.post<{
      id?: number | string;
      item?: RawScheduleRow;
    }>('/schedule', payload);
    const row: RawScheduleRow = data.item
      ? { ...payload, ...data.item, id: data.item.id ?? data.id }
      : { ...payload, id: data.id };
    return mapRow(row);
  } catch (err) {
    throw new Error(unwrapError(err, '新建日程失败'));
  }
}

/**
 * 更新日程。
 */
export async function update(
  id: number | string,
  payload: ScheduleUpdatePayload,
): Promise<void> {
  try {
    await client.put(`/schedule/${id}`, { id: Number(id), ...payload });
  } catch (err) {
    throw new Error(unwrapError(err, '更新日程失败'));
  }
}

/**
 * 删除日程。
 */
export async function remove(id: number | string): Promise<void> {
  try {
    await client.delete(`/schedule/${id}`);
  } catch (err) {
    throw new Error(unwrapError(err, '删除日程失败'));
  }
}

/**
 * 协作日程确认 / 取消确认。
 * @param confirmed true=确认, false=取消确认(回到 pending)
 */
export async function confirmCollaboration(
  id: number | string,
  confirmed: boolean = true,
): Promise<ScheduleStatus> {
  try {
    const { data } = await client.post<{ status?: string }>(
      `/schedule/${id}/confirm`,
      null,
      { params: { confirmed } },
    );
    return normalizeStatus(data.status);
  } catch (err) {
    throw new Error(unwrapError(err, '协作确认失败'));
  }
}
