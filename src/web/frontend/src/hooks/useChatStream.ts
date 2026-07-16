/**
 * useChatStream - stateful chat session backed by a WebSocket. (v3.1.0)
 * ====================================================================
 *
 * Stage 3.1 / 3.3:
 *  - 增加 sessionId 状态,所有 WebSocket 帧 (含 ack) 都带 session_id
 *  - 新增 switchSession() / loadHistory() 异步方法
 *  - sessionStorage 兜底:断网时缓存最近 20 条 user/assistant (key: chat_draft_<sessionId>)
 *  - localStorage 持久化 current_session_id 用于刷新恢复
 *  - WebSocket URL 加 ?session_id=xxx query,useWebSocket 会因 url 变更自动重连
 *
 * Connects to /ws/chat and exchanges JSON frames:
 *
 *  Outbound (client -> server):
 *    { "type": "message", "content": "<text>" }   (optional "conn_id": "<id>")
 *    { "type": "ping" }                            (heartbeat, auto-sent every 30s)
 *
 *  Inbound (server -> client):
 *    { "type": "system",  "message": "..."     }   -> server greeting, ignored
 *    { "type": "ack",     "conn_id": "...", "session_id": "..." } -> store conn_id
 *                                                              + set sessionId
 *    { "type": "chunk",   "content": "..."     }   -> append to current assistant bubble
 *    { "type": "done"                          }   -> mark isStreaming=false, finalise
 *    { "type": "emotion",  ...                 }   -> attach to most recent assistant msg
 *    { "type": "emotion_update", ...           }   -> Stage B.3: cache to window.__lastEmotion
 *    { "type": "error",   "message": "..."     }   -> set error state, clear streaming
 *    { "type": "pong"                          }   -> heartbeat response
 *
 * The hook keeps an exponential-backoff reconnection (1s -> 2s -> 4s -> 8s -> 16s
 * -> 30s cap) via `useWebSocket`, and exposes a `lastPongAt` timestamp + a
 * `sendMessage` helper that returns false when the socket is not open.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useWebSocket, WebSocketStatus } from './useWebSocket';
import { listMessages } from '../api/chatSessions';

export type ChatRole = 'user' | 'assistant' | 'system';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string;
  emotion?: any;
  done?: boolean;
  connId?: string;
}

export interface UseChatStreamOptions {
  /** Override the websocket URL. If omitted, computed from import.meta.env.DEV */
  url?: string;
  /** Optional system message shown when messages is empty */
  welcomeMessage?: string;
  /** Heartbeat ping interval in ms. Default 30000. */
  heartbeatInterval?: number;
  /** Active session id; if null/undefined the WS will auto-create a new session. */
  sessionId?: number | null;
  /** Default user_id used for listMessages fallback (unused for now; reserved). */
  userId?: string;
}

export interface UseChatStreamResult {
  messages: ChatMessage[];
  status: WebSocketStatus;
  connId: string | null;
  sessionId: number | null;
  sendMessage: (text: string) => boolean;
  retryLast: () => boolean;
  clearMessages: () => void;
  clearError: () => void;
  isStreaming: boolean;
  error: string | null;
  lastPongAt: number | null;
  switchSession: (newId: number | null) => Promise<void>;
  loadHistory: (id: number) => Promise<void>;
}

const DEFAULT_DEV_URL = 'ws://localhost:8000/ws/chat';
const DEFAULT_HEARTBEAT = 30000;
const SESSION_STORAGE_KEY_PREFIX = 'chat_draft_';
const LOCAL_STORAGE_KEY = 'current_session_id';
const HISTORY_FETCH_LIMIT = 200;
const DRAFT_KEEP = 20;
const DRAFT_FLUSH_INTERVAL = 5000;

function resolveChatUrl(override?: string, sessionId?: number | null): string {
  let baseUrl: string;
  if (override) {
    baseUrl = override;
  } else {
    const isDev = Boolean((import.meta as any)?.env?.DEV);
    if (isDev) {
      baseUrl = DEFAULT_DEV_URL;
    } else if (typeof window !== 'undefined') {
      const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
      baseUrl = `${proto}://${window.location.host}/ws/chat`;
    } else {
      baseUrl = DEFAULT_DEV_URL;
    }
  }
  if (sessionId && Number.isFinite(sessionId) && sessionId > 0) {
    const sep = baseUrl.includes('?') ? '&' : '?';
    return `${baseUrl}${sep}session_id=${sessionId}`;
  }
  return baseUrl;
}

let _idCounter = 0;
function generateId(): string {
  _idCounter += 1;
  return `${Date.now().toString(36)}-${_idCounter.toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

function safeParse(json: string | null | undefined): any {
  if (!json) return undefined;
  try {
    return JSON.parse(json);
  } catch {
    return undefined;
  }
}

function buildWelcomeMessage(welcomeMessage?: string): ChatMessage[] {
  if (!welcomeMessage) return [];
  return [
    {
      id: generateId(),
      role: 'system',
      content: welcomeMessage,
      timestamp: new Date().toISOString(),
      done: true,
    },
  ];
}

function mapHistoryItem(it: any): ChatMessage {
  const role = (it?.role === 'user' || it?.role === 'assistant' || it?.role === 'system')
    ? (it.role as ChatRole)
    : 'assistant';
  return {
    id: `srv-${it?.id ?? generateId()}`,
    role,
    content: String(it?.content ?? ''),
    timestamp: new Date(Number(it?.created_at ?? Date.now() / 1000) * 1000).toISOString(),
    done: true,
    connId: it?.conn_id ?? undefined,
    emotion: safeParse(it?.emotion_json),
  };
}

export function useChatStream(options: UseChatStreamOptions = {}): UseChatStreamResult {
  const { url, welcomeMessage, heartbeatInterval = DEFAULT_HEARTBEAT, sessionId: externalSessionId } =
    options;

  // Internal session state - takes initial value from external prop if provided.
  const [sessionId, setSessionId] = useState<number | null>(
    externalSessionId !== undefined && externalSessionId !== null && Number.isFinite(externalSessionId)
      ? Number(externalSessionId)
      : null
  );

  // Sync external prop changes into internal state (preserves the imperative switchSession path).
  useEffect(() => {
    if (
      externalSessionId !== undefined &&
      externalSessionId !== null &&
      Number.isFinite(externalSessionId) &&
      Number(externalSessionId) !== sessionId
    ) {
      setSessionId(Number(externalSessionId));
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [externalSessionId]);

  const resolvedUrl = useMemo(
    () => resolveChatUrl(url, sessionId),
    [url, sessionId]
  );

  const [messages, setMessages] = useState<ChatMessage[]>(() => buildWelcomeMessage(welcomeMessage));
  const [connId, setConnId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Track the id of the assistant message currently being streamed.
  const currentAssistantIdRef = useRef<string | null>(null);
  // Track the most recent user text so retryLast can resend it.
  const lastUserInputRef = useRef<string | null>(null);
  // Track the last-rendered sessionId so we can detect changes inside effects.
  const lastSessionIdRef = useRef<number | null>(sessionId);

  // ---- sessionStorage draft helpers ----
  const draftKey = (id: number | null) =>
    id === null ? null : `${SESSION_STORAGE_KEY_PREFIX}${id}`;

  const writeDraft = useCallback((id: number | null, msgs: ChatMessage[]) => {
    const key = draftKey(id);
    if (!key || typeof window === 'undefined') return;
    try {
      const draft = msgs
        .filter((m) => m.role === 'user' || m.role === 'assistant')
        .slice(-DRAFT_KEEP);
      window.sessionStorage.setItem(key, JSON.stringify(draft));
    } catch {
      /* quota / private mode: ignore */
    }
  }, []);

  const readDraft = useCallback((id: number): ChatMessage[] | null => {
    const key = draftKey(id);
    if (!key || typeof window === 'undefined') return null;
    try {
      const raw = window.sessionStorage.getItem(key);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed)) return parsed as ChatMessage[];
      return null;
    } catch {
      return null;
    }
  }, []);

  const handleMessage = useCallback((data: any) => {
    if (!data || typeof data !== 'object') return;
    const type = (data as any).type;

    switch (type) {
      case 'ack': {
        const cid = (data as any).conn_id ?? (data as any).connId;
        if (typeof cid === 'string') {
          setConnId(cid);
        }
        // v3.1.0: server tells us the authoritative session_id (auto-created when missing)
        const sid = (data as any).session_id ?? (data as any).sessionId;
        if (sid !== undefined && sid !== null && sid !== '') {
          const id = Number(sid);
          if (Number.isFinite(id) && id > 0) {
            setSessionId(id);
            if (typeof window !== 'undefined') {
              try {
                window.localStorage.setItem(LOCAL_STORAGE_KEY, String(id));
              } catch {
                /* ignore */
              }
            }
          }
        }
        return;
      }
      case 'chunk': {
        // Backend sends { "type": "chunk", "content": "<delta>" }.
        // Tolerate legacy frames that used the `chunk` field name.
        const chunk: string =
          (data as any).content ?? (data as any).chunk ?? '';
        setError(null);
        setMessages((prev) => {
          // If there's no current assistant message, create one.
          if (!currentAssistantIdRef.current) {
            const id = generateId();
            currentAssistantIdRef.current = id;
            setIsStreaming(true);
            return [
              ...prev,
              {
                id,
                role: 'assistant',
                content: chunk,
                timestamp: new Date().toISOString(),
                done: false,
              },
            ];
          }
          return prev.map((m) =>
            m.id === currentAssistantIdRef.current
              ? { ...m, content: m.content + chunk }
              : m
          );
        });
        return;
      }
      case 'done': {
        setMessages((prev) => {
          return prev.map((m) =>
            m.id === currentAssistantIdRef.current ? { ...m, done: true } : m
          );
        });
        currentAssistantIdRef.current = null;
        setIsStreaming(false);
        return;
      }
      case 'emotion': {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === currentAssistantIdRef.current
              ? { ...m, emotion: (data as any).emotion ?? data }
              : m
          )
        );
        return;
      }
      case 'emotion_update': {
        // Stage B.3: 缓存到 window.__lastEmotion，供 EmotionPanel/Chat 页面读取
        try {
          if (typeof window !== 'undefined') {
            (window as any).__lastEmotion = {
              type: 'emotion_update',
              data: (data as any).data ?? null,
              cumulative: (data as any).cumulative ?? null,
              historical_max: (data as any).historical_max ?? null,
              last_message: (data as any).last_message ?? '',
              timestamp: (data as any).timestamp ?? '',
              user_id: (data as any).user_id ?? 'default',
              received_at: new Date().toISOString(),
            };
          }
        } catch (err) {
          // eslint-disable-next-line no-console
          console.debug('[useChatStream] window.__lastEmotion cache failed', err);
        }
        return;
      }
      case 'error': {
        const messageText =
          (data as any).message ?? (data as any).error ?? 'Server error';
        setError(messageText);
        // Finalise any in-flight assistant bubble so the UI shows it as
        // complete (with whatever content it had) rather than stuck streaming.
        if (currentAssistantIdRef.current !== null) {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === currentAssistantIdRef.current ? { ...m, done: true } : m
            )
          );
        }
        currentAssistantIdRef.current = null;
        setIsStreaming(false);
        return;
      }
      case 'system': {
        const sysMsg: string = (data as any).message ?? '';
        if (sysMsg) {
          // eslint-disable-next-line no-console
          console.debug('[useChatStream] system:', sysMsg);
        }
        return;
      }
      case 'pong': {
        return;
      }
      case 'message': {
        const text: string = (data as any).content ?? (data as any).message ?? '';
        currentAssistantIdRef.current = null;
        setIsStreaming(false);
        setMessages((prev) => [
          ...prev,
          {
            id: generateId(),
            role: 'assistant',
            content: text,
            timestamp: new Date().toISOString(),
            done: true,
          },
        ]);
        return;
      }
      default:
        return;
    }
  }, []);

  const ws = useWebSocket(resolvedUrl, {
    onMessage: handleMessage,
    heartbeatInterval,
  });

  // React to transport-level status changes:
  //   - on open (reconnect), clear any lingering error
  //   - on closed/error mid-stream, finalize the in-flight assistant message
  //     and surface a transient error.
  useEffect(() => {
    if (ws.status === 'open') {
      setError(null);
      return;
    }
    if (ws.status === 'closed' || ws.status === 'error') {
      if (currentAssistantIdRef.current !== null) {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === currentAssistantIdRef.current && !m.done
              ? { ...m, done: true }
              : m
          )
        );
        currentAssistantIdRef.current = null;
        setIsStreaming(false);
      }
      // Don't override an existing explicit error from a server frame.
      setError((prev) => prev ?? '连接已断开');
    }
  }, [ws.status]);

  // ---- sessionStorage draft flush ----
  // Persist the last 20 user/assistant messages every 5s for offline fallback.
  useEffect(() => {
    if (sessionId === null) return;
    const id = sessionId;
    // initial flush
    writeDraft(id, messages);
    const timer = window.setInterval(() => {
      // We deliberately read the latest messages from the closure captured at
      // effect time, but since messages is part of the dep list the effect
      // re-runs on change and the new closure is re-installed.
      writeDraft(id, messages);
    }, DRAFT_FLUSH_INTERVAL);
    return () => window.clearInterval(timer);
  }, [sessionId, messages, writeDraft]);

  // ---- sessionId change side effects ----
  // When sessionId changes, clear messages (keeping welcome) and let
  // useWebSocket reconnect to /ws/chat?session_id=... (URL change is the
  // trigger). History loading is performed imperatively by switchSession()
  // / loadHistory() to keep the effect side-effect free of network I/O.
  useEffect(() => {
    if (lastSessionIdRef.current === sessionId) return;
    lastSessionIdRef.current = sessionId;
    currentAssistantIdRef.current = null;
    setIsStreaming(false);
    setMessages(buildWelcomeMessage(welcomeMessage));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  // ---- Public action: loadHistory(id) ----
  const loadHistory = useCallback(
    async (id: number): Promise<void> => {
      if (!Number.isFinite(id) || id <= 0) return;
      try {
        const { items } = await listMessages(id, HISTORY_FETCH_LIMIT);
        const mapped: ChatMessage[] = (items || []).map(mapHistoryItem);
        setMessages(() => [...buildWelcomeMessage(welcomeMessage), ...mapped]);
      } catch (err) {
        // Fallback to sessionStorage draft
        const draft = readDraft(id);
        if (draft && draft.length > 0) {
          setMessages(() => [...buildWelcomeMessage(welcomeMessage), ...draft]);
        }
        // eslint-disable-next-line no-console
        console.warn('[useChatStream] loadHistory failed, draft fallback used', err);
      }
    },
    [welcomeMessage, readDraft]
  );

  // ---- Public action: switchSession(newId) ----
  const switchSession = useCallback(
    async (newId: number | null): Promise<void> => {
      // Persist to localStorage so refresh restores the same session.
      if (typeof window !== 'undefined') {
        try {
          if (newId === null) {
            window.localStorage.removeItem(LOCAL_STORAGE_KEY);
          } else {
            window.localStorage.setItem(LOCAL_STORAGE_KEY, String(newId));
          }
        } catch {
          /* ignore */
        }
      }
      // setSessionId will trigger URL change -> useWebSocket reconnects.
      // The sessionId-change effect will clear messages (keeping welcome).
      setSessionId(newId);
      // Fetch history (if applicable).
      if (newId !== null) {
        await loadHistory(newId);
      }
    },
    [loadHistory]
  );

  const sendMessage = useCallback(
    (text: string): boolean => {
      const trimmed = text.trim();
      if (!trimmed) return false;
      const socketOpen = ws.status === 'open';
      const userMsg: ChatMessage = {
        id: generateId(),
        role: 'user',
        content: trimmed,
        timestamp: new Date().toISOString(),
        done: true,
      };
      setMessages((prev) => [...prev, userMsg]);
      // Start a new assistant stream slot.
      const assistantId = generateId();
      currentAssistantIdRef.current = assistantId;
      setIsStreaming(true);
      setMessages((prev) => [
        ...prev,
        {
          id: assistantId,
          role: 'assistant',
          content: '',
          timestamp: new Date().toISOString(),
          done: false,
        },
      ]);
      lastUserInputRef.current = trimmed;
      setError(null);
      if (!socketOpen) {
        return false;
      }
      return ws.send({ type: 'message', content: trimmed, conn_id: connId });
    },
    [ws, connId]
  );

  const retryLast = useCallback((): boolean => {
    const last = lastUserInputRef.current;
    if (!last) return false;
    return sendMessage(last);
  }, [sendMessage]);

  const clearError = useCallback(() => setError(null), []);

  const clearMessages = useCallback(() => {
    currentAssistantIdRef.current = null;
    lastUserInputRef.current = null;
    setConnId(null);
    setIsStreaming(false);
    setError(null);
    setMessages(buildWelcomeMessage(welcomeMessage));
  }, [welcomeMessage]);

  return {
    messages,
    status: ws.status,
    connId,
    sessionId,
    sendMessage,
    retryLast,
    clearMessages,
    clearError,
    isStreaming,
    error,
    lastPongAt: ws.lastPongAt,
    switchSession,
    loadHistory,
  };
}

export default useChatStream;
