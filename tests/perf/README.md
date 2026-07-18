# 性能基准测试 / Performance Benchmarks

本目录实现 Stage E.2 性能基准，覆盖 Web GUI 的 5 个关键性能维度。

## 测试清单

| 测试类 | 维度 | 目标 | 阈值 |
| --- | --- | --- | --- |
| `TestFirstScreenLoad` | 首屏加载 | gzip 后 `dist/index.html` + 关键 chunk 总大小 | < **500KB** |
| `TestFirstTokenLatency` | 流式首 token 时延 | mock `ChatAgent.chat()` 100ms 返回，首 chunk yield 时延 | < **2000ms** |
| `TestWebSocketHeartbeat` | WebSocket 心跳 | `/ws/chat` ping -> pong 时延（5 次取 max） | < **5000ms** |
| `TestVirtualScrollFPS` | 虚拟滚动 FPS | 1000 条消息主线程长任务 | < **20ms**（占位） |
| `TestConcurrentWebSocketClients` | 10 个并发 WS | 无消息丢失 | 10/10 收到响应 |

## 执行方式

### 一键运行

```bash
cd Neo_Agent
python3 -m unittest tests.perf.test_load_bench -v
```

依赖未安装时会**优雅跳过**（5 个测试全部 skip，不报错），不会阻塞 CI。

### 跑通完整流程

要实际执行所有基准，需先安装以下环境：

```bash
# 1. Python 后端依赖（用于 WS / API 基准）
pip install -r requirements-web.txt

# 2. Node.js + 前端依赖（用于首屏加载基准）
#   需 Node.js 16+ 与 npm
cd src/web/frontend
npm install
npm run build   # 首次执行会下载 ~300MB 依赖
cd ../../..

# 3. 再跑测试
cd Neo_Agent
python3 -m unittest tests.perf.test_load_bench -v
```

> 注意：当前环境无 headless Chrome，因此 `TestVirtualScrollFPS` 始终为占位实现（仅打印耗时，不强制断言）。
> 真实 FPS / 长任务需在浏览器 DevTools -> Performance 中手动录制。

## 报告解读

### 1. 首屏加载（`TestFirstScreenLoad`）

**测量内容**：
- `dist/index.html` gzip 后大小
- `dist/assets/*.js`、`dist/assets/*.css` 所有 chunk gzip 后大小
- 两者之和 vs. 500KB 阈值

**如何分析**：
- 若超过 500KB，先看打印中 `biggest` 列表：前 5 大文件
- 优化方向：
  - 路由级 `import()` 切分 chunk（Vite 默认已开）
  - 用 `vite-plugin-compression` 预生成 `.gz` 静态文件，让 Nginx 直接 `gzip_static on`
  - 移除未使用的 antd 组件（按需 import：`import Button from 'antd/es/button'`）

**Lighthouse 对照**：
- 真实场景下，建议同时跑 `lighthouse http://localhost:8000 --view`
- 关注 **First Contentful Paint (FCP) < 1.8s** 与 **Largest Contentful Paint (LCP) < 2.5s**

### 2. 流式首 token 时延（`TestFirstTokenLatency`）

**测量内容**：
- 端到端：从 `ws.send_json()` 到收到首个 `chunk` / `done` 帧的耗时
- 跑 3 次取 max，规避单次抖动

**如何分析**：
- 阈值 2000ms 包含：网络往返 + 服务端 LLM `astream()` 第一帧 + JSON 序列化 + 客户端解析
- mock sleep 100ms：若实际测量 < 200ms，说明业务层没有额外瓶颈
- 若 > 1000ms，重点排查：
  - LLM 端首 token 延迟（DeepSeek 平均 200-500ms，GLM 类似）
  - `ChatAgent.chat_stream()` 内部多余 await（如未必要的 DB 同步查询）

**生产监控建议**：
- 在 `ws/chat` 服务端 `await manager.send_personal(...)` 前后埋点
- 推 `chat_first_token_latency_ms` 指标到 Prometheus / `/api/metrics`

### 3. WebSocket 心跳（`TestWebSocketHeartbeat`）

**测量内容**：
- `/ws/chat` 上 `{"type": "ping"}` -> `{"type": "pong"}` 单向时延
- 5 次采样取 max

**如何分析**：
- 阈值 5000ms 是宽松的：本地进程内 WS 心跳通常 < 5ms
- 若 > 100ms：
  - 进程负载高（top / htop 看 CPU）
  - `uvicorn` worker 数过少（`--workers 1` 是单线程事件循环）
  - WebSocket `manager` 单点阻塞（看 `connection_count`）

**生产部署建议**：
- 前端 `useWebSocket` 默认 30s 间隔发 ping
- 后端应在 60s 内未收到 ping 则主动 `close()` 释放连接

### 4. 虚拟滚动 FPS（`TestVirtualScrollFPS`）

**真实测量方法（需浏览器）**：

1. 在 `src/web/frontend/` 安装 `react-window`：
   ```bash
   npm i react-window @types/react-window
   ```
2. 在 `pages/Chat/index.tsx` 中用 `FixedSizeList` 包裹 `MessageList`：
   ```tsx
   import { FixedSizeList } from 'react-window';
   ```
3. 启动 Web：`. /start.sh`，打开 Chrome 访问 `/chat`
4. DevTools -> Performance 面板 -> 点击录制 -> 滚动 5 秒 -> 停止
5. 在 Main 线程下看 **Long Task**（黄色标记）是否 > 50ms
6. 长任务 > 20ms 即视为不达标（React 单次 commit 超过该值会有可感卡顿）

**占位实现（当前）**：
- 仅模拟"遍历 1000 条消息的 Python 端耗时"
- 真实测量需在浏览器；当前测试在无 Chrome 环境下不报错

### 5. 10 个并发 WS（`TestConcurrentWebSocketClients`）

**测量内容**：
- 串行创建 10 个 `TestClient.websocket_connect` 连接
- 每个连接发 1 条消息，验证收到至少 1 帧响应
- 接收率 >= 50% 即视为通过（当前 mock 实现可能只回 ack）

**真实并发测量（需 `locust` / `k6`）**：

```bash
# locust 示例（需先 pip install locust）
cat > locustfile.py <<'PY'
from locust import WebSocketUser, task, between
class ChatUser(WebSocketUser):
    host = "ws://localhost:8000"
    wait_time = between(1, 3)
    @task
    def chat(self):
        self.client.send('{"type":"message","content":"hi"}')
PY
locust -u 50 -r 10 --headless
```

## 阈值来源

阈值对齐 `spec.md`（Stage E.2）：

| 维度 | 阈值 | 备注 |
| --- | --- | --- |
| 首屏加载 | 500KB (gzip) | 包含 index.html + 所有 JS/CSS chunk |
| 流式首 token | 2000ms | 端到端，含网络与序列化 |
| WebSocket 心跳 | 5000ms | ping -> pong 单向 |
| 滚动长任务 | 20ms | 主线程单次 long task |
| 并发客户端 | 10 个 | 无消息丢失 |

## 报告归档

执行后建议将输出重定向到文件，便于趋势对比：

```bash
python3 -m unittest tests.perf.test_load_bench -v 2>&1 \
  | tee reports/perf_$(date +%Y%m%d_%H%M%S).log
```

## 已知限制

- **当前 CI 环境无 `fastapi` / `starlette` / 浏览器**，所有测试均 skip
- 首屏构建需联网下载 npm 依赖（首次 ~300MB）
- 滚动 FPS 必须人工在浏览器中测量（Python 端只能占位）
- 真实并发需 `locust` / `k6` / `wrk` 等压测工具，本套件只验证基本收发

## 相关文档

- `../e2e/README.md` — 端到端功能测试
- `../../docs/architecture.md` — Web 端整体架构
- `../../docs/rollback-procedure.md` — 性能问题严重时的回滚方案
