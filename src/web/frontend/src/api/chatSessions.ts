/**
 * Chat Sessions API 客户端 - v3.1.0
 * =================================
 *
 * 与后端 `src/web/backend/api/chat_sessions.py` 对齐:
 * - GET    /api/chat/sessions?user_id=&limit=&offset=
 * - POST   /api/chat/sessions                body: { user_id, title? }
 * - GET    /api/chat/sessions/{id}/messages?limit=
 * - PATCH  /api/chat/sessions/{id}           body: { title }
 * - DELETE /api/chat/sessions/{id}           -> 204
 *
 * 设计要点:
 * - 纯 fetch,无 axios 依赖,便于与 useChatStream 解耦
 * - base URL 优先用 import.meta.env.VITE_API_BASE,否则默认 '/api'
 * - 失败抛 Error, 由 UI 层决定是否弹 message.error
 */

export interface ChatSession {
  id: number;
  user_id: string;
  title: string;
  created_at: number;
  updated_at: number;
  message_count: number;
}

export interface ChatMessage {
  id: number;
  session_id: number;
  role: 'user' | 'assistant' | 'system';
  content: string;
  emotion_json: string | null;
  conn_id: string | null;
  created_at: number;
}

function getBaseUrl(): string {
  const env = (import.meta as any)?.env;
  const base = env?.VITE_API_BASE;
  if (typeof base === 'string' && base.trim()) {
    return base.replace(/\/+$/, '');
  }
  return '/api';
}

async function unwrapError(resp: Response, fallback: string): Promise<never> {
  let detail = fallback;
  try {
    const data = await resp.json();
    if (data && typeof data === 'object') {
      const d = (data as any).detail;
      if (typeof d === 'string' && d.trim()) {
        detail = d;
      }
    }
  } catch {
    /* ignore parse error */
  }
  throw new Error(detail);
}

/**
 * 列出用户会话（按 updated_at 倒序）。
 */
export async function listSessions(
  userId: string = 'default',
  limit: number = 50,
  offset: number = 0,
): Promise<{ items: ChatSession[]; total: number }> {
  const url = `${getBaseUrl()}/chat/sessions?user_id=${encodeURIComponent(userId)}&limit=${limit}&offset=${offset}`;
  const resp = await fetch(url, { method: 'GET' });
  if (!resp.ok) {
    return unwrapError(resp, `listSessions failed: ${resp.status}`);
  }
  const data = await resp.json();
  return {
    items: Array.isArray(data?.items) ? (data.items as ChatSession[]) : [],
    total: Number(data?.total ?? 0) || 0,
  };
}

/**
 * 创建新会话。
 */
export async function createSession(
  userId: string,
  title?: string,
): Promise<ChatSession> {
  const url = `${getBaseUrl()}/chat/sessions`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, title: title ?? '新会话' }),
  });
  if (!resp.ok) {
    return unwrapError(resp, `createSession failed: ${resp.status}`);
  }
  return (await resp.json()) as ChatSession;
}

/**
 * 删除会话（级联删 messages）。
 */
export async function deleteSession(sessionId: number): Promise<void> {
  const url = `${getBaseUrl()}/chat/sessions/${sessionId}`;
  const resp = await fetch(url, { method: 'DELETE' });
  if (!resp.ok && resp.status !== 204) {
    return unwrapError(resp, `deleteSession failed: ${resp.status}`);
  }
}

/**
 * 重命名会话。
 */
export async function renameSession(
  sessionId: number,
  title: string,
): Promise<ChatSession> {
  const url = `${getBaseUrl()}/chat/sessions/${sessionId}`;
  const resp = await fetch(url, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title }),
  });
  if (!resp.ok) {
    return unwrapError(resp, `renameSession failed: ${resp.status}`);
  }
  return (await resp.json()) as ChatSession;
}

/**
 * 拉取会话消息（按 id 升序）。
 */
export async function listMessages(
  sessionId: number,
  limit: number = 200,
): Promise<{ items: ChatMessage[]; total: number }> {
  const url = `${getBaseUrl()}/chat/sessions/${sessionId}/messages?limit=${limit}`;
  const resp = await fetch(url, { method: 'GET' });
  if (!resp.ok) {
    return unwrapError(resp, `listMessages failed: ${resp.status}`);
  }
  const data = await resp.json();
  return {
    items: Array.isArray(data?.items) ? (data.items as ChatMessage[]) : [],
    total: Number(data?.total ?? 0) || 0,
  };
}

export default {
  listSessions,
  createSession,
  deleteSession,
  renameSession,
  listMessages,
};
