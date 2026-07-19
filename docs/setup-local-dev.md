# Neo Agent v4.1.0 — 本地开发环境配置

> 5 分钟跑起来 Web GUI。

## 一键配置（推荐）

```bash
cd Neo_Agent
chmod +x setup-dev.sh
./setup-dev.sh
```

脚本会自动：
1. 检查 Python ≥ 3.10 + Node.js ≥ 18
2. 从 `.env.example` 复制生成 `.env`
3. 创建 `.venv` 虚拟环境
4. 安装 `requirements.txt` + `requirements-web.txt`
5. `npm install` 前端依赖

完成后**只需填 API Key**：

```bash
vim .env
# 改这两行：
#   SILICONFLOW_API_KEY=sk-...
#   SERPAPI_API_KEY=...
```

## 启动方式（任选其一）

### 方式 1：一键启动脚本（推荐）

```bash
./start.sh
# 自动 activate venv + ENABLE_FRONTEND_DEV=1 + python run_web.py
```

打开浏览器 → http://localhost:8000

### 方式 2：手动启动 Web GUI

```bash
source .venv/bin/activate
ENABLE_FRONTEND_DEV=1 python main.py --web
```

### 方式 3：纯 API 模式（无 Vite 热重载）

```bash
source .venv/bin/activate
python main.py --web --no-dev
```

适合生产部署或无前端 dev server 场景。

## 启动参数速查

| 参数 | 默认 | 说明 |
|---|---|---|
| `--port` | 8000 | FastAPI 监听端口 |
| `--host` | 0.0.0.0 | FastAPI 监听地址 |
| `--no-dev` | | 跳过 Vite dev server |
| `--no-static` | | 不挂载前端构建产物（纯 API） |
| `--reload` | | uvicorn 代码热重载（仅开发态） |

## 环境变量速查（.env）

| 变量 | 必填 | 说明 |
|---|---|---|
| `SILICONFLOW_API_KEY` | ✅ | LLM API 密钥 |
| `SERPAPI_API_KEY` | ✅ | 网络搜索 API 密钥 |
| `MAIN_MODEL_NAME` | | 主模型（默认 `deepseek-ai/DeepSeek-V3.2`） |
| `TOOL_MODEL_NAME` | | 小模型（默认 `zai-org/GLM-4.6V`） |
| `VISION_MODEL_NAME` | | 多模态模型（默认 `Qwen/Qwen3-VL-32B-Instruct`） |
| `ENABLE_FRONTEND_DEV` | | Vite dev server 开关（0/1） |
| `WEB_HOST` | | FastAPI 监听地址 |
| `WEB_PORT` | | FastAPI 监听端口 |
| `CORS_ORIGINS` | | CORS 允许来源（逗号分隔） |
| `CHAT_AGENT_DB` | | SQLite 路径 |
| `LOG_LEVEL` | | Web 日志级别（DEBUG/INFO/WARNING/ERROR） |
| `ENABLE_LIFE_STATE` | | 生活状态开关 |
| `ENABLE_PROACTIVE_ENGINE` | | 主动消息开关 |
| `ENABLE_EMOTION_WHEEL` | | 情感雷达开关 |
| `ENABLE_CREATIVE_WRITER` | | 创意写作开关 |

## 端口规划

| 端口 | 用途 | 启动者 |
|---|---|---|
| 8000 | FastAPI 后端 | `python main.py --web` |
| 5173 | Vite dev server（HMR） | `ENABLE_FRONTEND_DEV=1` 时自动启动 |
| 前端 `/api/*` 代理 → 8000 | dev 模式反代 | vite.config.ts |
| 前端 `/ws/*` 代理 → 8000 | dev 模式反代 | vite.config.ts |

## 常见问题

### Q1: `pip install` 失败
- 检查网络/代理
- 升级 pip：`python -m pip install --upgrade pip`
- 改用国内源：
  ```bash
  python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt
  ```

### Q2: 前端 5173 端口被占用
```bash
lsof -i :5173
kill <PID>
# 或修改 vite.config.ts 的 server.port
```

### Q3: 8000 端口被占用
```bash
python main.py --web --port 8080
```

### Q4: WebSocket 连不上
- 检查防火墙是否放行 8000 / 5173
- 检查 `CORS_ORIGINS` 是否包含实际访问的 origin
- 浏览器 DevTools → Network → WS 帧查看是否握手成功

## 目录结构（关键文件）

```
Neo_Agent/
├── .env                          # 本地敏感配置（gitignored）
├── .env.example                  # 配置模板（已提交）
├── main.py                       # 启动入口（Web / API）
├── run_web.py                    # Web 启动脚本
├── start.sh                      # 一键启动
├── setup-dev.sh                  # 一键配置（新增）
├── requirements.txt              # Python 核心依赖
├── requirements-web.txt          # Python Web 依赖
├── src/
│   ├── core/                     # 业务核心（只读，不要改）
│   └── web/
│       ├── backend/              # FastAPI 后端
│       └── frontend/             # React + Vite 前端
│           ├── package.json
│           └── vite.config.ts
└── docs/
    └── setup-local-dev.md        # 本文件
```

## 验证启动

启动后访问：

| URL | 说明 |
|---|---|
| http://localhost:8000/ | Web GUI 主页 |
| http://localhost:8000/docs | FastAPI Swagger |
| http://localhost:8000/api/health | 健康检查 |
| http://localhost:5173/ | Vite dev server（开发态） |

健康检查应返回：
```json
{"status":"ok","version":"4.1.0","timestamp":"2026-07-14T..."}
```

## 常见工作流

### 第一次跑通
```bash
./setup-dev.sh
vim .env       # 填 API Key
./start.sh
# 浏览器开 http://localhost:8000
```

### 改后端代码 → 自动热重载
```bash
python main.py --web --reload
```

### 改前端代码 → 自动 HMR
Vite dev server 已自动启动，改完即热重载。

### 跑测试
```bash
source .venv/bin/activate
python -m unittest discover tests -v
```

## 下一步

- 阅读 [CHANGELOG.md](../CHANGELOG.md) 了解 v3.0.0 变更
- 阅读 [docs/architecture.md](architecture.md) 了解 Web 端架构
- 阅读 [docs/api.md](api.md) 了解 REST/WS 端点

---

## LLM 供应商配置（v3.1.0+）

v3.1.0 新增**供应商无关的 LLM 通用配置**。通过 `LLM_PROVIDER` 预设即可一键切换 OpenAI / DeepSeek / SiliconFlow / Moonshot / Zhipu / 自建网关，不再需要为每个供应商写不同变量名。

### 通用配置（推荐）

```env
# 供应商预设：openai / deepseek / siliconflow / moonshot / zhipu / custom
LLM_PROVIDER=siliconflow
# API Key
LLM_API_KEY=sk-...
# 可选：自定义 base_url（custom 模式必填；preset 模式省略时使用厂商默认）
# LLM_BASE_URL=https://api.openai.com/v1
# 可选：自定义模型名
# LLM_MODEL_NAME=gpt-4o-mini
# 全局超时/温度/最大 tokens
LLM_TIMEOUT=60
LLM_TEMPERATURE=0.7
LLM_MAX_TOKENS=2000
```

### 6 个 preset 的最小配置示例

| 供应商 | `LLM_PROVIDER` | 必填 | 默认 base_url | 默认 model | 申请地址 |
|---|---|---|---|---|---|
| OpenAI | `openai` | `LLM_API_KEY` | `https://api.openai.com/v1` | `gpt-4o-mini` | https://platform.openai.com/api-keys |
| DeepSeek | `deepseek` | `LLM_API_KEY` | `https://api.deepseek.com/v1` | `deepseek-chat` | https://platform.deepseek.com/api_keys |
| SiliconFlow | `siliconflow` | `LLM_API_KEY` | `https://api.siliconflow.cn/v1` | `deepseek-ai/DeepSeek-V3.2` | https://cloud.siliconflow.cn/account/ak |
| Moonshot | `moonshot` | `LLM_API_KEY` | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | https://platform.moonshot.cn/console/api-keys |
| 智谱 Zhipu | `zhipu` | `LLM_API_KEY` | `https://open.bigmodel.cn/api/paas/v4` | `glm-4-flash` | https://open.bigmodel.cn/usercenter/apikeys |
| Custom | `custom` | `LLM_API_KEY` + `LLM_BASE_URL` + `LLM_MODEL_NAME` | (用户必填) | (用户必填) | - |

#### OpenAI

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-...
# 可选覆盖：
# LLM_MODEL_NAME=gpt-4o
```

#### DeepSeek

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-...
# 可选覆盖：
# LLM_MODEL_NAME=deepseek-reasoner
```

#### SiliconFlow

```env
LLM_PROVIDER=siliconflow
LLM_API_KEY=sk-...
# 可选覆盖：
# LLM_MODEL_NAME=Qwen/Qwen3-VL-32B-Instruct
```

#### Moonshot

```env
LLM_PROVIDER=moonshot
LLM_API_KEY=sk-...
# 可选覆盖：
# LLM_MODEL_NAME=moonshot-v1-128k
```

#### Zhipu

```env
LLM_PROVIDER=zhipu
LLM_API_KEY=...
# 可选覆盖：
# LLM_MODEL_NAME=glm-4-plus
```

#### Custom（自建网关/代理）

```env
LLM_PROVIDER=custom
LLM_API_KEY=...
LLM_BASE_URL=https://my-proxy.example.com/v1
LLM_MODEL_NAME=my-model-name
```

### 向后兼容

旧变量（v3.0.x）**仍可使用**，系统会自动 fallback：

```env
# 仍可工作（fallback 到 LLM_API_KEY）
SILICONFLOW_API_KEY=sk-...
# 仍可工作（fallback 到 LLM_BASE_URL）
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions
# 仍可工作（fallback 到 LLM_MODEL_NAME）
MODEL_NAME=deepseek-ai/DeepSeek-V3
```

推荐迁移到新的 `LLM_*` 变量。`/api/llm/config` 与 `/api/llm/test` 不依赖具体供应商，可在前端 `/settings` 页面查看当前生效配置与一键测试连接。

### 三层模型独立配置

仍可通过 `MAIN_MODEL_NAME` / `TOOL_MODEL_NAME` / `VISION_MODEL_NAME` 为三层分别指定模型名（fallback 到 `LLM_MODEL_NAME`）。视觉/工具层可独立设置 `LLM_BASE_URL`（多供应商混合：主模型 OpenAI，视觉用 SiliconFlow Qwen-VL）。

---

## 会话管理（v3.1.0+）

v3.1.0 新增**会话持久化**：

- 所有聊天会话与消息存储到 `chat_sessions` / `chat_messages` 数据库表
- 支持多会话切换、刷新页面自动恢复、删除级联

### Web 端使用

1. 打开 http://localhost:8000/chat
2. 顶部 toolbar 左侧点击「**会话**」按钮（📂 图标）→ 弹出左侧 SessionSidebar
3. SessionSidebar 操作：
   - **+ 新建会话**：创建新空会话并切换
   - 点击列表项：切换到该会话，自动从后端拉取历史消息填充
   - hover 列表项右侧删除按钮：弹确认框 → 调 `DELETE /api/chat/sessions/{id}`，DB 级联删 messages
   - 当前会话用蓝色背景 + 「当前」Tag 高亮
4. 刷新页面：前端从 `localStorage.current_session_id` 读 ID 自动恢复

### REST API 速查

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/chat/sessions?user_id=default&limit=50` | 列出用户会话 |
| POST | `/api/chat/sessions` body `{user_id, title?}` | 创建新会话 |
| GET | `/api/chat/sessions/{id}/messages?limit=200` | 拉取会话消息（按 id 升序） |
| PATCH | `/api/chat/sessions/{id}` body `{title}` | 重命名 |
| DELETE | `/api/chat/sessions/{id}` | 级联删 messages（外键 ON DELETE CASCADE） |
| GET | `/api/chat/sessions/current?user_id=default` | 取用户最近一个活跃 session |

### WebSocket 绑定

`/ws/chat?session_id=xxx` 接收后消息关联到该 session；未带 `session_id` 时后端自动创建并通过 `ack` 帧回传：

```json
{ "type": "ack", "conn_id": "abc", "session_id": "42" }
```

前端收到 `ack.session_id` 后会自动写入 `localStorage.current_session_id` 持久化。

### 离线兜底

断网时前端会把最近 20 条 user/assistant 消息写入 `sessionStorage`（key: `chat_draft_<sessionId>`）。重连成功后从后端拉历史覆盖本地草稿；DB 拉取失败时回退用 draft 填充。
