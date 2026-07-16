/**
 * useProactiveStream - subscribe to /ws/proactive for server-pushed
 * "proactive" messages (no user input required).
 *
 * The backend ProactiveEngine publishes events through EventManager, which
 * the EventService forwards to the ``proactive`` WebSocket channel. The
 * payload looks like:
 *
 *   {
 *     "type": "proactive",         // or "proactive_message"
 *     "content": "…",
 *     "reason": "habit_care",      // impulse-pool tag
 *     "timestamp": "2026-07-14T…",
 *     "user": "default",
 *     "idea_id": "…",
 *     "priority": "normal",
 *     "source": "ProactiveEngine",
 *     // optional:
 *     "related_uuid": "…",
 *     // legacy / wrapper form supported too:
 *     "event_type": "proactive_message",
 *     "payload": { ...above... }
 *   }
 *
 * The hook normalises both raw and wrapped shapes, generates a stable uuid
 * for React keys, and exposes:
 *   - proactiveMessages: ProactiveMessage[]   (newest first)
 *   - status: WebSocketStatus
 *   - clearProactive(uuid): void
 *   - clearAll(): void
 *
 * On unmount the WebSocket is closed by the underlying useWebSocket hook.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useWebSocket, WebSocketStatus } from './useWebSocket';

export interface ProactiveMessage {
  /** Stable client-side id (React key + dismiss target). */
  uuid: string;
  content: string;
  reason: string;
  timestamp: string;
  priority: string;
  source: string;
  idea_id: string;
  user?: string;
  /** Optional: if present, the banner is clickable to navigate to context. */
  related_uuid?: string;
  /** Original raw payload, useful for debugging / advanced rendering. */
  raw: any;
}

export interface UseProactiveStreamOptions {
  /** Override the websocket URL. */
  url?: string;
  /**
   * Cap on the number of proactive messages kept in state. Oldest are
   * dropped first. Default 20.
   */
  maxMessages?: number;
  /**
   * Disable the WebSocket connection (e.g. user opted out). The hook will
   * report status='closed' and never push messages.
   */
  enabled?: boolean;
  /**
   * Optional callback fired for every accepted message *after* state is
   * updated. Useful for triggering a notification sound.
   */
  onProactive?: (msg: ProactiveMessage) => void;
}

export interface UseProactiveStreamResult {
  proactiveMessages: ProactiveMessage[];
  status: WebSocketStatus;
  /** Remove a single banner. */
  clearProactive: (uuid: string) => void;
  /** Remove every banner. */
  clearAll: () => void;
  /** Last raw error / status, if any. */
  lastError: string | null;
}

const DEFAULT_DEV_URL = 'ws://localhost:8000/ws/proactive';
const DEFAULT_MAX = 20;

function resolveUrl(override?: string): string {
  if (override) return override;
  const isDev = Boolean((import.meta as any)?.env?.DEV);
  if (isDev) {
    return DEFAULT_DEV_URL;
  }
  if (typeof window !== 'undefined') {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${proto}://${window.location.host}/ws/proactive`;
  }
  return DEFAULT_DEV_URL;
}

let _idCounter = 0;
function generateUuid(): string {
  _idCounter += 1;
  return `proactive-${Date.now().toString(36)}-${_idCounter.toString(36)}-${Math.random()
    .toString(36)
    .slice(2, 8)}`;
}

function isProactiveFrame(data: any): boolean {
  if (!data || typeof data !== 'object') return false;
  // Direct forms sent by EventService -> manager.broadcast('proactive', ...)
  const t = (data as any).type;
  if (t === 'proactive' || t === 'proactive_message') return true;
  // Wrapper form sent by /ws/events: { type: "event", event_type: "proactive_message", payload: {...} }
  if (t === 'event' && (data as any).event_type === 'proactive_message') return true;
  return false;
}

function extractPayload(data: any): any {
  if (!data || typeof data !== 'object') return null;
  // If payload is nested, use it; otherwise the frame is the payload.
  if ((data as any).payload && typeof (data as any).payload === 'object') {
    return (data as any).payload;
  }
  return data;
}

function normaliseProactive(raw: any): ProactiveMessage | null {
  const payload = extractPayload(raw);
  if (!payload || typeof payload !== 'object') return null;
  const content = (payload as any).content ?? (payload as any).message ?? '';
  if (typeof content !== 'string' || content.trim().length === 0) {
    return null;
  }
  return {
    uuid: generateUuid(),
    content,
    reason: (payload as any).reason ?? '',
    timestamp:
      (payload as any).timestamp ??
      (payload as any).ts ??
      new Date().toISOString(),
    priority: (payload as any).priority ?? 'normal',
    source: (payload as any).source ?? 'ProactiveEngine',
    idea_id: (payload as any).idea_id ?? '',
    user: (payload as any).user,
    related_uuid:
      (payload as any).related_uuid ??
      (payload as any).related_loop_uuid ??
      (payload as any).related_project_uuid,
    raw: payload,
  };
}

export function useProactiveStream(
  options: UseProactiveStreamOptions = {}
): UseProactiveStreamResult {
  const {
    url,
    maxMessages = DEFAULT_MAX,
    enabled = true,
    onProactive,
  } = options;

  const resolvedUrl = useMemo(() => (enabled ? resolveUrl(url) : ''), [
    url,
    enabled,
  ]);

  const [proactiveMessages, setProactiveMessages] = useState<ProactiveMessage[]>([]);
  const [lastError, setLastError] = useState<string | null>(null);

  // Keep latest onProactive callback in a ref so the message handler is stable.
  const onProactiveRef = useRef(onProactive);
  useEffect(() => {
    onProactiveRef.current = onProactive;
  }, [onProactive]);

  const handleMessage = useCallback((data: any) => {
    if (!isProactiveFrame(data)) return;
    const msg = normaliseProactive(data);
    if (!msg) return;
    setProactiveMessages((prev) => {
      // Newest first; cap length.
      const next = [msg, ...prev];
      if (next.length > maxMessages) {
        next.length = maxMessages;
      }
      return next;
    });
    try {
      onProactiveRef.current?.(msg);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[useProactiveStream] onProactive callback threw:', err);
    }
  }, [maxMessages]);

  const handleError = useCallback((event: Event) => {
    setLastError('proactive websocket error');
    // eslint-disable-next-line no-console
    console.warn('[useProactiveStream] websocket error:', event);
  }, []);

  const handleClose = useCallback(() => {
    // Close is informational; we keep lastError only on real errors.
  }, []);

  const ws = useWebSocket(resolvedUrl, {
    onMessage: handleMessage,
    onError: handleError,
    onClose: handleClose,
    // For proactive messages we still want reconnection (the spec notes the
    // push is best-effort) - default reconnection behaviour of useWebSocket
    // already covers this. We disable it only if the user turned the hook off.
    reconnect: enabled,
  });

  // Expose connection status to consumers (useWebSocket returns 'connecting'
  // for an empty url, which we surface as 'closed' when disabled).
  const status: WebSocketStatus = enabled ? ws.status : 'closed';

  const clearProactive = useCallback((uuid: string) => {
    setProactiveMessages((prev) => prev.filter((m) => m.uuid !== uuid));
  }, []);

  const clearAll = useCallback(() => {
    setProactiveMessages([]);
  }, []);

  return {
    proactiveMessages,
    status,
    clearProactive,
    clearAll,
    lastError,
  };
}

export default useProactiveStream;
