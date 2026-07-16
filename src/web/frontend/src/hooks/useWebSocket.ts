/**
 * useWebSocket - generic React hook for managing a WebSocket connection.
 *
 * Features:
 *  - Automatic exponential backoff reconnection (1s -> 2s -> 4s -> ... capped at 30s)
 *  - JSON parsing with raw string fallback
 *  - Optional ping/pong heartbeat (opt-in via `heartbeatInterval`).
 *    When enabled, the hook sends {"type":"ping"} every N ms and records
 *    the timestamp of each "pong" response in `lastPongAt`.
 *  - Auto cleanup on component unmount
 *  - Returns connection status + a `send` helper + an accumulated `messages` array
 */

import { useCallback, useEffect, useRef, useState } from 'react';

export type WebSocketStatus = 'connecting' | 'open' | 'closed' | 'error';

export interface UseWebSocketOptions<T = any> {
  onMessage?: (data: T, raw: string) => onMessageResult | void;
  onOpen?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  onError?: (event: Event) => void;
  /** Initial reconnect interval in milliseconds. Default 1000. */
  reconnectInterval?: number;
  /** Max reconnect interval cap in milliseconds. Default 30000. */
  maxReconnectInterval?: number;
  /** Should the hook reconnect on close. Default true. */
  reconnect?: boolean;
  /**
   * Heartbeat interval in milliseconds. If > 0, the hook sends
   * {"type":"ping"} at this interval while the socket is open and records
   * the time of each "pong" response in `lastPongAt`. Default 0 (disabled).
   */
  heartbeatInterval?: number;
  /**
   * Payload used for the heartbeat. Defaults to {"type":"ping"}.
   * Must be JSON-serializable.
   */
  heartbeatPayload?: any;
}

export type onMessageResult =
  | { handled?: boolean; isPong?: boolean }
  | undefined
  | void;

export interface UseWebSocketResult<T = any> {
  status: WebSocketStatus;
  send: (data: any) => boolean;
  messages: T[];
  clearMessages: () => void;
  reconnectNow: () => void;
  /** Epoch ms of the most recent pong response, or null if none yet. */
  lastPongAt: number | null;
}

const DEFAULT_RECONNECT = 1000;
const DEFAULT_MAX_RECONNECT = 30000;
const DEFAULT_HEARTBEAT = 0;

export function useWebSocket<T = any>(
  url: string,
  options: UseWebSocketOptions<T> = {}
): UseWebSocketResult<T> {
  const {
    onMessage,
    onOpen,
    onClose,
    onError,
    reconnectInterval = DEFAULT_RECONNECT,
    maxReconnectInterval = DEFAULT_MAX_RECONNECT,
    reconnect = true,
    heartbeatInterval = DEFAULT_HEARTBEAT,
    heartbeatPayload,
  } = options;

  const [status, setStatus] = useState<WebSocketStatus>('connecting');
  const [messages, setMessages] = useState<T[]>([]);

  // Refs hold the latest callbacks so we don't restart the connection on every render.
  const onMessageRef = useRef(onMessage);
  const onOpenRef = useRef(onOpen);
  const onCloseRef = useRef(onClose);
  const onErrorRef = useRef(onError);

  // Refs for reconnect bookkeeping and current WebSocket instance.
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef<number>(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const shouldConnectRef = useRef<boolean>(true);
  const isUnmountedRef = useRef<boolean>(false);
  const heartbeatTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPongAtRef = useRef<number | null>(null);
  // Trigger re-render when lastPongAt changes (consumers may want a stale-state check).
  const [, setPongTick] = useState<number>(0);

  useEffect(() => {
    onMessageRef.current = onMessage;
    onOpenRef.current = onOpen;
    onCloseRef.current = onClose;
    onErrorRef.current = onError;
  }, [onMessage, onOpen, onClose, onError]);

  const computeBackoff = useCallback(
    (attempt: number): number => {
      const base = reconnectInterval * Math.pow(2, attempt);
      // cap at maxReconnectInterval
      return Math.min(base, maxReconnectInterval);
    },
    [reconnectInterval, maxReconnectInterval]
  );

  const clearReconnectTimer = useCallback(() => {
    if (reconnectTimerRef.current !== null) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
  }, []);

  const clearHeartbeat = useCallback(() => {
    if (heartbeatTimerRef.current !== null) {
      clearInterval(heartbeatTimerRef.current);
      heartbeatTimerRef.current = null;
    }
  }, []);

  const startHeartbeat = useCallback(() => {
    if (heartbeatInterval <= 0) return;
    clearHeartbeat();
    heartbeatTimerRef.current = setInterval(() => {
      const socket = wsRef.current;
      if (!socket || socket.readyState !== WebSocket.OPEN) return;
      const payload = heartbeatPayload ?? { type: 'ping' };
      try {
        socket.send(typeof payload === 'string' ? payload : JSON.stringify(payload));
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('[useWebSocket] heartbeat send failed:', err);
      }
    }, heartbeatInterval);
  }, [heartbeatInterval, heartbeatPayload, clearHeartbeat]);

  const connect = useCallback(() => {
    if (isUnmountedRef.current) return;
    if (!url) {
      setStatus('error');
      return;
    }

    clearReconnectTimer();
    clearHeartbeat();
    setStatus('connecting');

    let socket: WebSocket;
    try {
      socket = new WebSocket(url);
    } catch (err) {
      // Construction can throw if URL is malformed; treat as error and schedule retry.
      // eslint-disable-next-line no-console
      console.error('[useWebSocket] failed to construct WebSocket:', err);
      setStatus('error');
      scheduleReconnect();
      return;
    }

    wsRef.current = socket;

    socket.onopen = (event) => {
      if (isUnmountedRef.current) {
        socket.close();
        return;
      }
      // Reset backoff on successful open.
      reconnectAttemptRef.current = 0;
      setStatus('open');
      onOpenRef.current?.(event);
      startHeartbeat();
    };

    socket.onmessage = (event) => {
      if (isUnmountedRef.current) return;
      const raw: string = typeof event.data === 'string' ? event.data : String(event.data);
      let parsed: any = raw;
      if (typeof raw === 'string') {
        const trimmed = raw.trim();
        if (trimmed.length > 0 && (trimmed[0] === '{' || trimmed[0] === '[')) {
          try {
            parsed = JSON.parse(raw);
          } catch {
            // Keep the raw string if it's not valid JSON.
            parsed = raw;
          }
        }
      }

      // Detect pong responses at the transport layer so consumers can use
      // lastPongAt for health checks regardless of their message handler.
      let isPong = false;
      if (parsed && typeof parsed === 'object') {
        const t = (parsed as any).type;
        if (t === 'pong' || t === 'PONG') {
          isPong = true;
        }
      } else if (typeof raw === 'string' && raw.trim() === 'pong') {
        isPong = true;
      }
      if (isPong) {
        lastPongAtRef.current = Date.now();
        setPongTick((n) => n + 1);
      }

      setMessages((prev) => [...prev, parsed as T]);

      let result: onMessageResult;
      try {
        result = onMessageRef.current?.(parsed as T, raw) as onMessageResult;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.error('[useWebSocket] onMessage handler threw:', err);
        result = undefined;
      }
      // Allow the consumer to mark a message as a pong that doesn't match the
      // default detection (e.g. wrapped frame, custom type).
      if (result && (result as any).isPong) {
        lastPongAtRef.current = Date.now();
        setPongTick((n) => n + 1);
      }
    };

    socket.onerror = (event) => {
      if (isUnmountedRef.current) return;
      setStatus('error');
      onErrorRef.current?.(event);
    };

    socket.onclose = (event) => {
      if (isUnmountedRef.current) return;
      wsRef.current = null;
      clearHeartbeat();
      setStatus('closed');
      onCloseRef.current?.(event);
      if (shouldConnectRef.current && reconnect) {
        scheduleReconnect();
      }
    };
  }, [url, reconnect, clearReconnectTimer, clearHeartbeat, startHeartbeat]);

  const scheduleReconnect = useCallback(() => {
    if (!shouldConnectRef.current) return;
    const attempt = reconnectAttemptRef.current;
    const delay = computeBackoff(attempt);
    reconnectAttemptRef.current = attempt + 1;
    clearReconnectTimer();
    reconnectTimerRef.current = setTimeout(() => {
      reconnectTimerRef.current = null;
      connect();
    }, delay);
  }, [computeBackoff, connect, clearReconnectTimer]);

  // Effect: manage connection lifecycle based on URL.
  useEffect(() => {
    isUnmountedRef.current = false;
    shouldConnectRef.current = true;
    reconnectAttemptRef.current = 0;
    lastPongAtRef.current = null;
    connect();
    return () => {
      isUnmountedRef.current = true;
      shouldConnectRef.current = false;
      clearReconnectTimer();
      clearHeartbeat();
      if (wsRef.current) {
        try {
          wsRef.current.onopen = null;
          wsRef.current.onmessage = null;
          wsRef.current.onerror = null;
          wsRef.current.onclose = null;
          if (
            wsRef.current.readyState === WebSocket.OPEN ||
            wsRef.current.readyState === WebSocket.CONNECTING
          ) {
            wsRef.current.close();
          }
        } catch (err) {
          // eslint-disable-next-line no-console
          console.error('[useWebSocket] error while closing socket:', err);
        }
        wsRef.current = null;
      }
    };
  }, [url, connect, clearReconnectTimer, clearHeartbeat]);

  const send = useCallback((data: any): boolean => {
    const socket = wsRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      // eslint-disable-next-line no-console
      console.warn('[useWebSocket] send() called but socket is not open');
      return false;
    }
    const payload = typeof data === 'string' ? data : JSON.stringify(data);
    socket.send(payload);
    return true;
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  const reconnectNow = useCallback(() => {
    if (wsRef.current) {
      try {
        wsRef.current.onclose = null;
        wsRef.current.close();
      } catch {
        // ignore
      }
      wsRef.current = null;
    }
    clearHeartbeat();
    reconnectAttemptRef.current = 0;
    connect();
  }, [connect, clearHeartbeat]);

  return { status, send, messages, clearMessages, reconnectNow, lastPongAt: lastPongAtRef.current };
}

export default useWebSocket;
