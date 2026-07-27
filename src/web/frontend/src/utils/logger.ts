/**
 * Frontend Logger SDK
 *
 * 统一收集前端日志并通过 WebSocket 实时推送到后端 UnifiedLogger。
 * 特性：
 *  - 拦截 console.log/warn/error/debug，保留原始控制台输出
 *  - 批量 + 节流发送，避免压垮后端
 *  - WebSocket 断线时暂存队列，重连后补发
 *  - 超过缓冲区上限时丢弃最旧日志
 *  - 提供显式 logger.debug/info/warn/error/fatal API
 */

export type LogLevel = 'DEBUG' | 'INFO' | 'WARN' | 'ERROR' | 'FATAL';

export interface FrontendLogEntry {
  timestamp: string;
  level: LogLevel;
  module: string;
  message: string;
  source: 'frontend';
  url?: string;
  userAgent?: string;
  sessionId?: string;
  extra?: Record<string, unknown>;
}

export interface FrontendLoggerOptions {
  /** WebSocket URL，默认根据当前环境自动推断 */
  wsUrl?: string;
  /** 批量发送间隔（毫秒），默认 200 */
  throttleMs?: number;
  /** 单批最大条数，默认 50 */
  maxBatch?: number;
  /** 内存缓冲区最大条数，默认 500 */
  bufferSize?: number;
  /** 单条消息最大字符数，默认 8192 */
  maxMessageLength?: number;
  /** 模块名前缀，默认 'frontend' */
  module?: string;
  /** 启动时是否自动拦截 console，默认 true */
  interceptConsole?: boolean;
}

type ConsoleMethod = (...args: unknown[]) => void;

interface LoggerInternalState {
  ws: WebSocket | null;
  status: 'closed' | 'connecting' | 'open';
  queue: FrontendLogEntry[];
  timer: ReturnType<typeof setInterval> | null;
  reconnectTimer: ReturnType<typeof setTimeout> | null;
  sessionId: string;
  originalConsole: Partial<Record<keyof typeof console, ConsoleMethod>>;
  isDestroyed: boolean;
}

const LEVEL_MAP: Record<string, LogLevel> = {
  log: 'INFO',
  info: 'INFO',
  warn: 'WARN',
  warning: 'WARN',
  error: 'ERROR',
  debug: 'DEBUG',
  trace: 'DEBUG',
};

function resolveDefaultWsUrl(): string {
  if (typeof window === 'undefined') {
    return 'ws://localhost:8000/ws/frontend-logs';
  }
  const isDev = import.meta.env?.DEV === true;
  if (isDev) {
    return 'ws://localhost:8000/ws/frontend-logs';
  }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.host}/ws/frontend-logs`;
}

function generateSessionId(): string {
  return `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}

function safeStringify(value: unknown): string {
  if (value === undefined) return 'undefined';
  if (value === null) return 'null';
  if (typeof value === 'string') return value;
  if (typeof value === 'number' || typeof value === 'boolean') return String(value);
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}

function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return `${str.slice(0, maxLength)}...[truncated]`;
}

class FrontendLogger {
  private opts: Required<FrontendLoggerOptions>;
  private state: LoggerInternalState;

  constructor(options: FrontendLoggerOptions = {}) {
    this.opts = {
      wsUrl: options.wsUrl || resolveDefaultWsUrl(),
      throttleMs: options.throttleMs ?? 200,
      maxBatch: options.maxBatch ?? 50,
      bufferSize: options.bufferSize ?? 500,
      maxMessageLength: options.maxMessageLength ?? 8192,
      module: options.module || 'frontend',
      interceptConsole: options.interceptConsole !== false,
    };

    this.state = {
      ws: null,
      status: 'closed',
      queue: [],
      timer: null,
      reconnectTimer: null,
      sessionId: generateSessionId(),
      originalConsole: {},
      isDestroyed: false,
    };

    if (this.opts.interceptConsole) {
      this.interceptConsole();
    }
    this.startFlushTimer();
    this.connect();
  }

  /** 初始化并返回 Logger 实例 */
  static init(options?: FrontendLoggerOptions): FrontendLogger {
    return new FrontendLogger(options);
  }

  /** 显式记录日志 */
  debug(module: string, message: string, extra?: Record<string, unknown>): void {
    this.enqueue('DEBUG', module, message, extra);
  }

  info(module: string, message: string, extra?: Record<string, unknown>): void {
    this.enqueue('INFO', module, message, extra);
  }

  warn(module: string, message: string, extra?: Record<string, unknown>): void {
    this.enqueue('WARN', module, message, extra);
  }

  error(module: string, message: string, extra?: Record<string, unknown>): void {
    this.enqueue('ERROR', module, message, extra);
  }

  fatal(module: string, message: string, extra?: Record<string, unknown>): void {
    this.enqueue('FATAL', module, message, extra);
  }

  /** 拦截原生 console */
  interceptConsole(): void {
    if (typeof window === 'undefined') return;

    const levels: Array<keyof typeof console> = ['debug', 'log', 'info', 'warn', 'error'];
    this.state.originalConsole = {};

    levels.forEach((level) => {
      const original = console[level] as (...args: unknown[]) => void;
      this.state.originalConsole[level] = original;

      console[level] = (...args: unknown[]) => {
        // 仍打印到浏览器控制台
        original.apply(console, args);

        const logLevel = LEVEL_MAP[level] || 'INFO';
        const message = args.map(safeStringify).join(' ');
        this.enqueue(logLevel, this.opts.module, message, { rawLevel: level });
      };
    });
  }

  /** 恢复原生 console */
  restoreConsole(): void {
    if (typeof window === 'undefined') return;
    (Object.keys(this.state.originalConsole) as Array<keyof typeof console>).forEach(
      (level) => {
        const original = this.state.originalConsole[level];
        if (original) {
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          (console as any)[level] = original;
        }
      },
    );
    this.state.originalConsole = {};
  }

  private enqueue(
    level: LogLevel,
    module: string,
    message: string,
    extra?: Record<string, unknown>,
  ): void {
    if (this.state.isDestroyed) return;

    const entry: FrontendLogEntry = {
      timestamp: new Date().toISOString(),
      level,
      module,
      message: truncate(message, this.opts.maxMessageLength),
      source: 'frontend',
      url: typeof window !== 'undefined' ? window.location.href : undefined,
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : undefined,
      sessionId: this.state.sessionId,
      extra,
    };

    this.state.queue.push(entry);
    if (this.state.queue.length > this.opts.bufferSize) {
      this.state.queue.splice(0, this.state.queue.length - this.opts.bufferSize);
    }
  }

  private startFlushTimer(): void {
    if (this.state.timer) return;
    this.state.timer = setInterval(() => {
      this.flush();
    }, this.opts.throttleMs);
  }

  private stopFlushTimer(): void {
    if (this.state.timer) {
      clearInterval(this.state.timer);
      this.state.timer = null;
    }
  }

  private connect(): void {
    if (this.state.isDestroyed) return;
    if (this.state.status === 'connecting' || this.state.status === 'open') return;

    try {
      this.state.status = 'connecting';
      const ws = new WebSocket(this.opts.wsUrl);
      this.state.ws = ws;

      ws.onopen = () => {
        this.state.status = 'open';
        this.flush();
      };

      ws.onclose = () => {
        this.state.status = 'closed';
        this.state.ws = null;
        this.scheduleReconnect();
      };

      ws.onerror = () => {
        this.state.status = 'closed';
        this.state.ws = null;
      };
    } catch (err) {
      this.state.status = 'closed';
      this.state.ws = null;
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect(): void {
    if (this.state.isDestroyed) return;
    if (this.state.reconnectTimer) return;

    this.state.reconnectTimer = setTimeout(() => {
      this.state.reconnectTimer = null;
      this.connect();
    }, 1000);
  }

  /** 立即发送队列中的日志 */
  flush(): void {
    if (this.state.queue.length === 0) return;
    if (this.state.status !== 'open' || !this.state.ws) return;

    const batch = this.state.queue.splice(0, this.opts.maxBatch);
    try {
      this.state.ws.send(JSON.stringify({ type: 'logs', entries: batch }));
    } catch (err) {
      // 发送失败：重新放回队列（保持顺序）
      this.state.queue.unshift(...batch);
    }
  }

  /** 销毁 Logger，恢复 console，关闭连接 */
  destroy(): void {
    this.state.isDestroyed = true;
    this.stopFlushTimer();
    this.restoreConsole();
    this.flush();

    if (this.state.reconnectTimer) {
      clearTimeout(this.state.reconnectTimer);
      this.state.reconnectTimer = null;
    }

    if (this.state.ws) {
      try {
        this.state.ws.close();
      } catch {
        // ignore
      }
      this.state.ws = null;
    }
  }
}

let globalLogger: FrontendLogger | null = null;

/** 初始化全局前端日志采集器 */
export function initFrontendLogger(options?: FrontendLoggerOptions): FrontendLogger {
  if (globalLogger) {
    globalLogger.destroy();
  }
  globalLogger = FrontendLogger.init(options);
  return globalLogger;
}

/** 获取当前全局 Logger 实例（如未初始化则自动初始化） */
export function getFrontendLogger(): FrontendLogger {
  if (!globalLogger) {
    globalLogger = FrontendLogger.init();
  }
  return globalLogger;
}

/** 销毁全局 Logger */
export function destroyFrontendLogger(): void {
  if (globalLogger) {
    globalLogger.destroy();
    globalLogger = null;
  }
}
