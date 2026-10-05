# Neo Agent 快速启动指南

## 环境准备

### 1. 激活虚拟环境
```bash
cd /home/hedass/桌面/Lien_os
source venv/bin/activate
```

### 2. 验证依赖
```bash
python3 -c "import textual; print(f'Textual {textual.__version__}')"
```

## 启动方式

### 方式一：使用模拟数据（推荐测试）

#### 终端 1：启动模拟服务
```bash
python3 neo_agent/service/mock_daemon.py
```
**预期输出**: `✓ 模拟服务已启动: /home/hedass/.neo_agent/agent.sock`

#### 终端 2：启动 TUI
```bash
python3 -m neo_agent.ui.v2.app
```

### 方式二：使用真实服务（开发中）

#### 终端 1：启动真实服务
```bash
# TODO: 真实服务实现后
python3 neo_agent/service/daemon.py
```

#### 终端 2：启动 TUI
```bash
python3 -m neo_agent.ui.v2.app
```

## TUI 使用指南

### 快捷键
```
c - 对话视图
i - 今日行程
s - 场景池
m - 记忆与知识
r - 关系网络
a - 审计日志
: - 命令模式
? - 帮助
q - 退出
```

### 命令模式（按 : 唤起）
```
:config       - 打开配置面板
:debug on     - 开启 Debug 模式
:debug off    - 关闭 Debug 模式
:export       - 导出数据
:import       - 导入数据
:help         - 显示帮助
:quit         - 退出应用
```

### 视图操作

#### 对话视图 (c)
- 在输入框输入消息
- 按 Enter 或点击"发送"按钮
- 查看历史对话记录

#### 今日行程 (i)
- 查看当日时间表
- 点击"刷新"更新行程
- 点击"生成新计划"创建新行程
- 点击行查看详情（开发中）

#### 场景池 (s)
- 查看当前场景信息
- 浏览已访问场景列表
- 点击场景查看详情（开发中）

#### 记忆与知识 (m)
- 查看记忆统计
- 输入关键词搜索
- 按 Enter 或点击"搜索"按钮

#### 关系网络 (r)
- 查看关系总览
- 浏览关系列表和亲密度
- 点击关系查看详情（开发中）

#### 审计日志 (a)
- 选择过滤器（全部/高风险/操作/决策）
- 查看时间倒序的日志流
- 风险等级颜色标识

## 测试组件

### 测试导航修复
```bash
python3 test_nav_fix.py
```
**预期**: 看到三个可点击的导航按钮，点击后显示通知

### 测试 UI 组件
```bash
python3 test_ui_components.py
```

## 开发工作流

### 修改 TUI 界面
1. 编辑 `neo_agent/ui/v2/views.py`
2. 保存文件
3. 重启 TUI（Ctrl+C 然后重新运行）
4. 测试修改效果

### 修改服务逻辑
1. 编辑 `neo_agent/service/mock_daemon.py`
2. 保存文件
3. 重启服务
4. TUI 会自动重连

### 调试技巧

#### 查看 Textual 开发者工具
```bash
# 终端 1：启动开发控制台
textual console

# 终端 2：启动应用（带调试）
textual run --dev neo_agent/ui/v2/app.py
```

#### 查看服务日志
```bash
# 如果使用 nohup 启动
tail -f /tmp/neo_agent_service.log
```

## 故障排除

### TUI 无法连接服务
**症状**: 底栏显示"连接失败"
**解决**:
1. 检查服务是否运行：`ps aux | grep mock_daemon`
2. 检查 socket 文件：`ls -la ~/.neo_agent/agent.sock`
3. 重启服务

### 导航无法点击
**症状**: 点击侧边栏无反应
**解决**: 确保使用最新代码（commit b8f3c17 之后）

### 视图数据不显示
**症状**: 切换视图后显示空白
**解决**:
1. 检查 mock_daemon 是否正常返回数据
2. 查看 TUI 错误通知
3. 检查 `load_data` 方法是否抛出异常

### Git 推送超时
**症状**: `git push` 无响应或超时
**解决**:
1. Ctrl+C 取消
2. 检查网络连接
3. 重试：`git push origin Dev`
4. 或使用：`git push --timeout=30 origin Dev`

## 文件位置参考

```
核心文件：
- TUI 主应用: neo_agent/ui/v2/app.py
- 视图组件: neo_agent/ui/v2/views.py
- 模态框: neo_agent/ui/v2/modals.py
- RPC 客户端: neo_agent/ui/v2/client.py
- 主题配置: neo_agent/ui/v2/theme.py

服务文件：
- 模拟服务: neo_agent/service/mock_daemon.py
- 真实服务: neo_agent/service/daemon.py (开发中)
- RPC 处理: neo_agent/service/rpc_handlers.py (开发中)

文档：
- 功能说明: TUI_FEATURES.md
- 完成报告: TUI_V2_COMPLETE.md
- 开发摘要: DEV_SUMMARY.md
- 项目状态: DEVELOPMENT_STATUS.md
- 本指南: QUICK_START.md
```

## 下一步开发

### 立即可做
1. 修改 mock_daemon.py 添加更多测试数据
2. 完善视图的错误处理和空状态
3. 添加新的快捷键或命令

### 需要真实服务
1. 实现 `rpc_handlers.py`
2. 连接 LangChain Agent
3. 集成 PyVDisk 持久化
4. 实现 WebSocket 推送

### 需要更多设计
1. 详情模态框的数据展示
2. Debug 模式的编辑界面
3. 配置的持久化逻辑

## 联系和反馈

**项目仓库**: https://github.com/HeDaas-Code/Neo_Agent  
**当前分支**: Dev  
**最新提交**: b8f3c17

遇到问题或有建议？请在 GitHub 提 Issue 或直接修改代码后提交 PR。

---
**更新时间**: 2026-10-05  
**文档版本**: 1.0  
**适用版本**: Dev 分支 b8f3c17 及之后
