# Neo Agent Web API 参考

> Stage E.3 - 简要 API 列表（REST + WebSocket）。**完整定义由 FastAPI 自动生成在 `/docs`（Swagger UI）与 `/redoc`。**

本文件用于**快速速查**，每个端点的 schema / 错误码 / 示例请以 FastAPI 生成的文档为准。

---

## 1. REST 端点

### 1.1 健康检查

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/health` | 服务存活检查；返回 `{status, version, timestamp}` |

**响应示例**：

```json
{
  "status": "ok",
  "version": "3.0.0",
  "timestamp": "2026-07-14T12:00:00.000000+00:00"
}
```

### 1.2 聊天（占位）

| Method | Path | 说明 |
| --- | --- | --- |
| GET | `/api/chat` | Stage A.3 占位端点；返回 `{message: "chat endpoint placeholder"}` |

> 未来将由 `POST /api/chat`（同步）与 `POST /api/chat/stream`（流式 SSE）替换。
> 当前聊天入口走 WebSocket `/ws/chat`。

### 1.3 业务域端点（占位 / Stage B-C 计划）

| 路径前缀 | 计划方法 | 用途 |
| --- | --- | --- |
| `/api/knowledge` | GET / POST / PUT / DELETE | 知识库 CRUD + `/search` |
| `/api/schedule` | GET / POST / PUT / DELETE | 日程管理 |
| `/api/events` | GET | 事件查询（运行时事件） |
| `/api/nps/status` | GET | NPS 工具状态 |
| `/api/database/tables` | GET | 数据库元信息（表 / schema 摘要） |
| `/api/creative/generate` | POST | 创意生成 |

> 这些端点在当前 Stage 尚未注册到 `src/web/backend/main.py`；实现按业务域分文件放到 `src/web/backend/api/`。

---

## 2. WebSocket 端点

所有 WS 端点位于 `/ws/*`；连接时由服务端先发送 `{"type": "ack" | "system", ...}`。

### 2.1 `/ws/chat` — 流式聊天

| 方向 | 帧 | 字段 |
| --- | --- | --- |
| 客户端 → 服务端 | `message` | `{type, content, context?}` |
| 客户端 → 服务端 | `ping` | `{type: "ping"}` |
| 服务端 → 客户端 | `system` | `{type, message}`（连接成功） |
| 服务端 → 客户端 | `chunk` | `{type, content}`（流式增量） |
| 服务端 → 客户端 | `done` | `{type}`（流式结束） |
| 服务端 → 客户端 | `pong` | `{type}`（心跳响应） |
| 服务端 → 客户端 | `error` | `{type, message}` |

**示例**：

```text
# 客户端
ws.send('{"type":"message","content":"你好"}')
# 服务端（按顺序）
<- {"type": "system", "message": "connected to /ws/chat"}
<- {"type": "chunk", "content": "你好"}
<- {"type": "chunk", "content": "，"}
<- {"type": "chunk", "content": "很高兴认识你"}
<- {"type": "done"}
```

### 2.2 `/ws/events` — 全局事件

| 方向 | 帧 | 字段 |
| --- | --- | --- |
| 客户端 → 服务端 | 任意 | `{type, ...}`（当前仅做 ack） |
| 服务端 → 客户端 | `ack` | `{type, conn_id, channel: "events"}` |
| 服务端 → 客户端 | 事件 payload | `{type: <event_type>, data: {...}}` |

事件类型（EventManager → EventService → broadcast）：

- `scheduler_tick` — 后台调度器心跳（每 60s）
- `proactive_message` — 主动消息（ProactiveEngine 触发）
- `chat_event` — 聊天事件（user_message / done）
- `message` — 通用消息总线
- 通配：`*` 订阅全部

### 2.3 `/ws/debug` — 调试日志

| 方向 | 帧 | 字段 |
| --- | --- | --- |
| 客户端 → 服务端 | 任意 | `{type, ...}`（仅 ack） |
| 服务端 → 客户端 | `ack` | `{type, conn_id, channel: "debug"}` |
| 服务端 → 客户端 | 日志帧 | `{type: "debug_log", level, module, message, timestamp}` |

> 接入 `src/tools/debug_logger.py`（`DebugLogger.subscribe`），
> `src/web/backend/ws/debug_broadcaster.py` 负责将日志广播到所有 `/ws/debug` 连接。

### 2.4 `/ws/proactive` — 主动消息

| 方向 | 帧 | 字段 |
| --- | --- | --- |
| 客户端 → 服务端 | 任意 | `{type, ...}`（仅 ack） |
| 服务端 → 客户端 | `ack` | `{type, conn_id, channel: "proactive"}` |
| 服务端 → 客户端 | 主动消息 | `{type: "proactive_message", title, body, ts}` |

> Stage A.2 骨架：连接后保持长连接，主动推送由 `manager.broadcast("proactive", msg)` 驱动。

### 2.5 `/ws/event`（已弃用，请用 `/ws/events`）

Stage A.2 早期版本。保留以做兼容，**新代码请使用 `/ws/events`**。

---

## 3. Pydantic Schema 速查

源文件位置：`src/web/backend/schemas/`

| Schema | 用途 |
| --- | --- |
| `ChatRequest` | `/api/chat` POST 请求体 |
| `ChatChunk` | 流式 chunk（`type=chunk` / `done` / `error`） |
| `ChatResponse` | 同步响应（`content` + `message_id` + `emotion?`） |
| `EventDTO` | 事件对象 |
| `EventListResponse` | 事件列表响应 |
| `KnowledgeEntity` / `KnowledgeDefinition` | 知识库实体 / 概念定义 |
| `KnowledgeSearchRequest` / `KnowledgeSearchResponse` | 知识库搜索 |
| `ScheduleDTO` / `ScheduleCreate` / `ScheduleUpdate` | 日程 CRUD |

> 未来扩展：`emotion.py` / `memory.py` / `creative.py` / `nps.py` / `debug.py`。

---

## 4. 错误与状态码

### 4.1 HTTP

- `200 OK` — 正常
- `400 Bad Request` — 请求参数不合法（Pydantic 校验失败）
- `404 Not Found` — 路由不存在
- `422 Unprocessable Entity` — FastAPI 校验失败（请求体 schema 不匹配）
- `500 Internal Server Error` — 服务端异常

### 4.2 WebSocket 错误帧

服务端通过 `{type: "error", message: "..."}` 推送错误，连接**不自动关闭**，由客户端决定是否重试。

| 场景 | message 示例 |
| --- | --- |
| 空输入 | `"empty input"` |
| ChatService 不可用 | `"ChatService unavailable"` |
| chat_stream 异常 | 异常 `str(e)` |

---

## 5. 自动化文档

| 工具 | URL |
| --- | --- |
| Swagger UI | `http://localhost:8000/docs` |
| ReDoc | `http://localhost:8000/redoc` |
| OpenAPI JSON | `http://localhost:8000/openapi.json` |

> WebSocket 端点**不会**自动出现在 `/docs` 中，请参考本文件 §2。

---

## 6. 相关文件

- `src/web/backend/main.py` — FastAPI 入口
- `src/web/backend/ws/*.py` — WebSocket 路由
- `src/web/backend/services/*.py` — Service 层
- `src/web/backend/schemas/*.py` — Pydantic v2 模型
- `architecture.md` — 整体架构
- `rollback-procedure.md` — 故障回滚
