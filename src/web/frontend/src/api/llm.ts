/**
 * LLM 配置 API 客户端 - v3.1.0
 * =============================
 *
 * 与后端 `src/web/backend/api/llm.py` 对齐:
 * - GET  /api/llm/config   -> LLMConfig
 * - POST /api/llm/test     body: { prompt: "ping" } -> {ok, latency_ms, sample_response, error}
 */

export interface LLMConfig {
  provider: string;
  base_url: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  timeout: number;
  valid: boolean;
  api_key_set?: boolean;
}

export interface LLMTestResult {
  ok: boolean;
  latency_ms?: number;
  sample_response?: string;
  error?: string;
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
    /* ignore */
  }
  throw new Error(detail);
}

/**
 * 读取当前生效 LLM 配置（provider / base_url / model / 温度 / tokens / timeout / 有效性）。
 */
export async function getConfig(): Promise<LLMConfig> {
  const url = `${getBaseUrl()}/llm/config`;
  const resp = await fetch(url, { method: 'GET' });
  if (!resp.ok) {
    return unwrapError(resp, `getConfig failed: ${resp.status}`);
  }
  return (await resp.json()) as LLMConfig;
}

/**
 * 调一次 ping 验证 LLM 连通性。
 */
export async function testConnection(prompt: string = 'ping'): Promise<LLMTestResult> {
  const url = `${getBaseUrl()}/llm/test`;
  const resp = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt }),
  });
  if (!resp.ok) {
    return unwrapError(resp, `testConnection failed: ${resp.status}`);
  }
  return (await resp.json()) as LLMTestResult;
}

export default {
  getConfig,
  testConnection,
};
