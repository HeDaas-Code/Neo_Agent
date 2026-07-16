# 回滚步骤（Web GUI → Tkinter GUI）

> **5 分钟内**将系统从 Web GUI 切回 Tkinter GUI 的标准操作流程。

---

## 适用场景

- Web 端出现严重 bug 且无法快速修复
- 后端依赖（FastAPI / Uvicorn / WebSockets）无法在当前环境安装
- 浏览器兼容性问题导致用户无法访问
- 端口 `8000` / `5173` 被其他服务占用且无法释放
- 临时降级以快速恢复线上可用性

---

## 5 分钟回滚步骤

### Step 1. 停止 Web 服务（如在运行）

```bash
# 方式 A：前台运行时在终端按 Ctrl+C
# 方式 B：后台运行时按 pid 终止
ps -ef | grep -E "uvicorn|run_web|main\.py|npm run dev" | grep -v grep
kill <pid>
# 如未退出，等待 5 秒后强杀
kill -9 <pid>
```

如有前端 dev server（`npm run dev`）也一并结束。`start.sh` 会在收到 SIGINT/SIGTERM 时自动级联关闭 Vite dev server。

### Step 2. 启动 Tkinter 模式

```bash
python main.py --tk
```

> 默认模式为 Web，`--tk` 显式切换到 Tkinter GUI。窗口出现后即可正常使用。

### Step 3. 验证 Tkinter 启动正常

肉眼检查以下清单：

- [ ] 主窗口正常打开（无 `ImportError` / `TclError`）
- [ ] 启动日志出现 `后台调度启动` 字样（如启用）
- [ ] Chat / Debug / Schedule / Knowledge 等 Tab 可点击切换
- [ ] 之前在 Web 端创建的对话、知识库条目、日程仍可见

### Step 4. 验证 `chat_agent.db` 数据完整

```bash
# 项目根目录下检查 SQLite 文件存在
ls -lh chat_agent.db

# 抽查关键表行数
sqlite3 chat_agent.db "SELECT 'chat_history', COUNT(*) FROM chat_history
                        UNION ALL SELECT 'knowledge_entries', COUNT(*) FROM knowledge_entries
                        UNION ALL SELECT 'schedule_items', COUNT(*) FROM schedule_items;"
```

预期：所有表的 `COUNT(*)` 与 Web 端最后一次使用时一致；如启用 WAL，目录里会同时存在 `chat_agent.db-wal` / `chat_agent.db-shm`。

---

## 数据零迁移

Web GUI 与 Tkinter GUI **共享同一份数据库**，**无任何数据迁移步骤**。

### 共享范围

- 数据库文件：`<project_root>/chat_agent.db`
- 模式：SQLite + **WAL 模式**（`src/core/database_manager.py:74-80` 启用 `PRAGMA journal_mode=WAL`）
- 访问入口：两端均通过 `DatabaseManager` 单例

### 切换时的行为

| 场景 | 行为 |
| --- | --- |
| Web → Tkinter | Web 关闭后连接释放；Tkinter 启动后立即看到全部数据 |
| Tkinter → Web | 同上 |
| 双端同时（不推荐） | WAL 模式允许并发读，单写者安全；写入交错由 SQLite 串行化 |

### 哪些表是共享的

所有由 `DatabaseManager` 管理的表（约 23 张），典型如：

- `chat_history` — 聊天历史
- `knowledge_entries` — 知识库条目
- `schedule_items` — 日程
- `events` / `proactive_messages` — 事件与主动消息
- `emotion_*` / `long_term_memory` — 情感与长期记忆
- `background_scheduler_status` — 调度器状态

业务层（`src/core/*`）未做任何 GUI 耦合修改，所以"回滚"在数据层完全等价于"换了个壳"。

---

## 故障排查 FAQ

### Q1. Tkinter 启动报 `ModuleNotFoundError: No module named 'tkinter'` / `TclError`

A: 系统未安装 Tk 库。Debian/Ubuntu 安装：

```bash
sudo apt-get update && sudo apt-get install -y python3-tk
```

macOS（Homebrew Python）：`brew install python-tk`。Windows：重新安装 Python 时勾选 "tcl/tk and IDLE"。

### Q2. Web 关闭后端口 `8000` 仍被占用

A: 残留进程没退干净。查找并强杀：

```bash
# 查找占用 8000 端口的进程
lsof -i :8000
# 或
fuser 8000/tcp
# 杀掉它
kill -9 <pid>
```

如启动 `start.sh` 时遇到同样问题，先 `pkill -f run_web.py` 再重试。

### Q3. Tkinter 模式下"之前的对话不见了" / 数据像是被清空

A: 大概率是打开的项目目录不对，或误用了 `chat_agent.db` 的另一份副本。检查：

```bash
# 当前工作目录下是否真的有 db 文件
ls -lh chat_agent.db
# 它的修改时间是否就是上次 Web 关闭的时间
stat chat_agent.db
```

如确有第二份 db，统一到同一目录即可（两端共享 `chat_agent.db` 的相对路径）。

### Q4. 回滚后 `ENABLE_BACKGROUND_SCHEDULER=true` 不再生效

A: 调度器依赖 LLM 凭据，Web 模式下能跑通不代表 Tkinter 也行。检查：

- `.env` 中 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY` 等关键变量存在
- 控制台日志中是否出现 `后台调度启动失败（不影响 GUI 启动）` 的警告
- 调度器只是辅助功能，关闭它仍可使用 Tkinter：在 `.env` 中设置 `ENABLE_BACKGROUND_SCHEDULER=false`

### Q5. 切回 Web 模式后，前端页面 404 / API 报 500

A: 通常是前端 dev server 缓存或后端 CORS 问题。逐项排查：

1. **404** — 前端构建产物未生成：
   ```bash
   cd src/web/frontend && npm run build
   ```
   或开发态用 `./start.sh`（自动启动 Vite dev server at :5173）。
2. **CORS 500** — 浏览器访问的不是 `http://localhost:8000` 而是其他 host/port。FastAPI 的 CORS 白名单仅包含 `localhost` / `127.0.0.1` 下的 `5173` 与 `8000`。
3. **API 500** — 看终端 `uvicorn` 输出的 traceback，对照 [`docs/architecture.md`](architecture.md) 定位是 `Service` 层还是 `core` 层异常。
4. **WebSocket 反复断开** — 浏览器 F12 → Network → WS 检查 `close code`：1006 通常是反向代理超时，配置 Nginx 加上 `proxy_read_timeout 3600s;`。

---

## 回滚验证清单

完成上述 4 步后请确认：

- [ ] 原 Tkinter 窗口正常打开（无 `ImportError` / `TclError`）
- [ ] 之前的对话记录可查看（`chat_history` 表）
- [ ] 知识库条目可查询（`knowledge_entries` 表）
- [ ] 日程条目可编辑（`schedule_items` 表）
- [ ] 事件 / 主动消息功能仍能触发（如有定时器）
- [ ] 后台调度器正常启动（启动日志出现 `后台调度启动` 字样）

---

## 切回 Web 模式

排查完 Web 端问题后，恢复 Web 启动：

```bash
# 1. 关闭 Tkinter（Ctrl+C）

# 2. 重启 Web
./start.sh
# 或
python run_web.py
# 或显式
python main.py --web
```

---

## 联系 / 升级路径

- 详细 Web 架构：[`architecture.md`](architecture.md)
- Web 端依赖：`requirements-web.txt`
- 启动脚本：`start.sh` / `run_web.py` / `main.py --web`

如频繁触发回滚，请收集以下信息以改进 Web 端：

1. 失败时浏览器控制台报错（F12 → Console）
2. 后端 `uvicorn` 输出最后 50 行
3. `chat_agent.db` 文件大小与 `git log -p` 最近 5 次提交
4. `.env` 中 `ENABLE_*` 系列开关的实际值
