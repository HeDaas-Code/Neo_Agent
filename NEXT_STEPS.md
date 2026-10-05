# Neo Agent 下一步开发计划

## 当前状态 ✓

### 已完成的重构
1. **服务-客户端分离** ✓
   - 守护进程服务正常运行
   - TUI 可独立连接/断开
   - Unix socket + JSON-RPC 2.0 通信

2. **琥珀色主题** ✓
   - 5 级深度表面颜色
   - 温暖专业的视觉体验
   - 所有组件样式统一

3. **导航系统** ✓
   - 键盘导航（回车键切换）
   - 鼠标点击支持
   - 所有 6 个视图可访问

4. **视图模块化** ✓
   - app.py 从 664 行减少到 336 行
   - views.py 独立管理所有视图
   - 代码组织清晰

5. **基础视图实现** ✓
   - ChatView：对话与消息发送
   - ItineraryView：今日行程展示
   - ScenePoolView：场景池管理
   - MemoryView：记忆搜索
   - RelationshipView：关系网络
   - AuditView：审计日志

## 立即任务（P0）

### 1. 完善服务端 RPC 方法
**目标**：让所有视图可以显示真实数据

**需要实现的 API**：
```python
# 会话管理
session.get_history(limit: int) -> List[dict]
session.send_message(text: str) -> {reply, emotion, scene}
session.get_context() -> {current_scene, emotion, relationship}

# 角色与状态
character.get_profile() -> {name, bio, traits, ...}

# 日程与场景
schedule.get_today_itinerary() -> List[dict]
schedule.generate_today_itinerary() -> {status, items}
scene.get_current() -> {location, area, objects, description}
scene.list_pool() -> List[dict]
scene.generate_new(activity, purpose) -> {location_id, ...}

# 知识与记忆
memory.search(query: str) -> List[dict]
knowledge.query(topic: str) -> List[dict]

# 关系与情绪
relationship.get_status(entity: str) -> {score, history}
relationship.list_all() -> List[dict]
emotion.get_current() -> {state, intensity, timestamp}

# 审计日志
audit.get_logs(risk_level: Optional[str], limit: int) -> List[dict]
```

**实施步骤**：
1. 在 `neo_agent/service/rpc_handlers.py` 中实现这些方法
2. 连接到现有的运行时服务（认知门控、场景管理、日程服务等）
3. 确保返回格式与视图期望的结构一致
4. 添加错误处理和日志记录

**验收标准**：
- 启动 TUI，对话视图显示真实历史消息
- 今日行程显示实际生成的计划
- 场景池显示已访问的场景
- 记忆搜索返回相关结果
- 关系网络显示当前关系状态
- 审计日志显示操作记录

### 2. 集成 WebSocket 实时推送
**目标**：TUI 自动响应服务端状态变化

**事件类型**：
```python
# 场景切换
{"type": "scene_changed", "scene": {...}}

# 情绪更新
{"type": "emotion_updated", "emotion": {...}}

# 新消息
{"type": "message_received", "message": {...}}

# 日程触发
{"type": "schedule_triggered", "schedule_item": {...}}

# 关系变化
{"type": "relationship_updated", "entity": "...", "score": ...}
```

**实施步骤**：
1. 在 `daemon.py` 中实现事件广播机制
2. 在 `app.py` 中添加 WebSocket 监听器
3. 更新顶栏显示（场景、情绪实时刷新）
4. 更新相应视图（新消息自动滚动、行程高亮等）

**验收标准**：
- 场景切换时顶栏立即更新
- 情绪变化时实时反映
- 新消息到达时聊天视图自动滚动
- 多个 TUI 实例同步状态

### 3. 实现命令模式
**目标**：提供高级配置和管理功能

**命令列表**：
```
:config          # 打开全局配置面板
:debug on|off    # 切换调试模式
:export <type>   # 导出数据（character, all）
:import <path>   # 导入角色数据
:help            # 显示帮助
:quit            # 退出 TUI
```

**实施步骤**：
1. 创建 `CommandPanel` 组件（模态面板）
2. 实现命令解析器和自动补全
3. 创建配置编辑界面（LLM 模型、PyVDisk 路径、时区等）
4. 实现导出/导入功能（连接到现有的导入导出服务）

**验收标准**：
- 按 `:` 唤起命令面板
- 输入命令有自动补全
- `:config` 可以编辑配置并保存
- `:debug on` 显示人工编辑入口
- `:export character` 导出成功

## 中期任务（P1）

### 4. 增强用户体验
- **快捷键系统**：
  - `h/j/k/l` Vim 风格导航
  - `?` 显示帮助面板
  - `Ctrl+R` 刷新当前视图
  - `Esc` 取消/返回上级

- **错误处理**：
  - 网络断线友好提示
  - RPC 超时自动重试
  - 操作失败可恢复

- **性能优化**：
  - 长列表虚拟滚动
  - 历史消息懒加载
  - 场景池分页

### 5. 完善视图交互
- **对话视图**：
  - Markdown 渲染
  - 代码块语法高亮
  - 多行输入编辑器

- **行程视图**：
  - 手动创建/编辑行程（Debug 模式）
  - 冲突检测可视化
  - 日程绑定场景选择器

- **场景视图**：
  - 场景详情展开/收起
  - 区域层级树状展示
  - 物体状态编辑（Debug 模式）

- **记忆视图**：
  - 高级搜索过滤器
  - 记忆时间线
  - 相关性评分展示

- **关系视图**：
  - 关系图可视化
  - 历史变化曲线
  - 事件关联展示

- **审计视图**：
  - 详细日志展开
  - 风险级别过滤器
  - 导出审计报告

## 长期目标（P2）

### 6. 多客户端协同
- 多个 TUI 实例状态同步
- 用户在线/离线状态
- 并发操作冲突解决

### 7. 远程服务支持
- TCP socket 选项
- TLS 加密通信
- SSH 隧道指南
- 远程连接认证

### 8. Web 客户端
- 复用 JSON-RPC API
- React/Vue 前端
- 浏览器端实时推送
- 响应式设计

### 9. 插件系统扩展
- TUI 视图插件化
- 第三方视图注册
- 自定义命令扩展
- 主题系统

## 技术债务

### 需要清理的项目
- [ ] 删除测试脚本（`test_*.py`）
- [ ] 删除备份文件（`app_backup.py`）
- [ ] 删除临时脚本（`create_unified_views.py`）
- [ ] 更新 README.md
- [ ] 更新 TECHNICAL.md
- [ ] 添加 API 文档

### 需要改进的代码
- [ ] RPC 方法返回值标准化
- [ ] 错误码体系建立
- [ ] 日志级别规范化
- [ ] 类型注解完善
- [ ] 单元测试覆盖

## 测试计划

### 单元测试
- [ ] RPC 方法单元测试
- [ ] 视图组件测试
- [ ] 命令解析器测试
- [ ] WebSocket 事件处理测试

### 集成测试
- [ ] 端到端用户流程测试
- [ ] 多客户端并发测试
- [ ] 服务重启恢复测试
- [ ] 数据持久化测试

### 性能测试
- [ ] 大量历史消息加载测试
- [ ] 长时间运行稳定性测试
- [ ] 内存泄漏检测
- [ ] WebSocket 推送延迟测试

## 文档任务

### 用户文档
- [ ] 安装指南
- [ ] 快速开始教程
- [ ] 功能使用说明
- [ ] 快捷键参考
- [ ] 命令参考
- [ ] 常见问题

### 开发文档
- [ ] 架构设计文档
- [ ] API 参考
- [ ] 插件开发指南
- [ ] 主题定制指南
- [ ] 贡献指南

## 里程碑

### Milestone 1: 基础功能完善（1-2 周）
- 完成 P0 任务 1-3
- 所有视图显示真实数据
- 命令模式可用
- WebSocket 推送集成

### Milestone 2: 用户体验优化（2-3 周）
- 完成 P1 任务 4-5
- 快捷键系统
- 错误处理增强
- 视图交互完善

### Milestone 3: 高级功能（1 个月+）
- 完成 P2 任务 6-9
- 多客户端协同
- 远程服务支持
- Web 客户端
- 插件系统

## 团队协作

### 当前优先级
1. **后端开发者**：实现服务端 RPC 方法（P0.1）
2. **前端开发者**：完善视图交互（P1.5）
3. **DevOps**：WebSocket 推送集成（P0.2）
4. **文档团队**：用户文档编写

### 沟通渠道
- 每日站会：同步进度，解决阻塞
- 代码审查：PR 提交后 24 小时内审查
- 技术讨论：复杂问题提前讨论设计方案

### 分支策略
- `Dev`：开发分支（当前活跃）
- `feature/*`：功能分支
- `bugfix/*`：修复分支
- `main`：稳定版本（待合并）

## 总结

TUI 重构的基础工作已完成，架构清晰，导航流畅，主题统一。下一步的重点是**让 TUI 真正可用**：

1. **连接真实数据**（P0.1）
2. **实时状态推送**（P0.2）
3. **高级配置能力**（P0.3）

完成这三项后，Neo Agent 将具备完整的终端管理能力，可以进入用户测试阶段。
