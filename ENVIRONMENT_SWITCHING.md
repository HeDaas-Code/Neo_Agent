# 环境切换功能文档

**中文** | [English](ENVIRONMENT_SWITCHING_EN.md)

## 概述

环境切换功能允许智能体在多个环境之间移动，并通过连接关系控制哪些环境之间可以切换。这个功能增强了智能体的空间感知能力，使对话更加真实和沉浸。

## 主要功能

### 1. 环境连接系统

环境之间可以建立连接关系，只有连通的环境才能相互切换。

#### 连接类型
- `normal` - 普通连接
- `door` - 门
- `portal` - 传送门
- `stairs` - 楼梯
- `corridor` - 走廊
- `window` - 窗户
- `other` - 其他

#### 连接方向
- `bidirectional` (双向) - 可以双向移动，如 A ⟷ B
- `one_way` (单向) - 只能单向移动，如 A → B

### 2. 智能切换检测

系统会自动检测用户的环境切换意图，关键词包括：
- 去、走、移动、前往、过去、进入
- 离开、出去、回到、返回
- 切换、换到、转移

例如：
- "我去客厅吧" - 会检测到切换到客厅的意图
- "我想回房间" - 会检测到切换到房间的意图

### 3. 权限验证

系统会自动验证切换权限：
- ✅ 只能切换到与当前环境连通的环境
- ❌ 不能切换到没有连接的孤立环境
- ✅ 尊重连接的方向性（单向/双向）

### 4. GUI管理界面

#### 环境管理面板
- 🔄 刷新 - 刷新环境列表
- ➕ 新建环境 - 创建新环境
- ➕ 添加物体 - 向环境添加物体
- 🏠 创建默认环境 - 快速创建示例环境

#### 环境切换和连接
- 🔀 切换环境 - 手动切换到其他环境
- 🔗 管理连接 - 管理环境连接关系
- 🗺️ 关系图 - 可视化查看环境关系
- 📋 使用记录 - 查看视觉工具使用记录

## 使用方法

### 创建环境

```python
from database_manager import DatabaseManager

db = DatabaseManager()

# 创建环境
room_uuid = db.create_environment(
    name="卧室",
    overall_description="温馨的卧室",
    atmosphere="安静舒适",
    lighting="柔和的灯光",
    sounds="轻柔的音乐",
    smells="淡淡的香气"
)
```

### 创建连接

```python
# 创建双向连接
conn_uuid = db.create_environment_connection(
    from_env_uuid=room_uuid,
    to_env_uuid=living_uuid,
    connection_type="door",
    direction="bidirectional",
    description="通过门可以进入客厅"
)
```

### 检查连通性

```python
# 检查是否可以从A移动到B
can_move = db.can_move_to_environment(room_uuid, living_uuid)
if can_move:
    print("可以移动！")
else:
    print("不能移动！")
```

### 切换环境

```python
from agent_vision import AgentVisionTool

vision = AgentVisionTool(db)

# 切换到指定环境
success = vision.switch_environment(living_uuid)
if success:
    print("切换成功！")
```

### 在聊天中使用

智能体会自动检测和响应环境切换建议：

```
用户: 我去客厅吧
系统: 🚪 [环境切换] 已从「卧室」移动到「客厅」
智能体: 好的，我们现在在客厅了...
```

## GUI操作指南

### 创建新环境

1. 打开 "👁️ 环境管理" 选项卡
2. 点击 "➕ 新建环境" 按钮
3. 填写环境信息：
   - 环境名称
   - 整体描述
   - 氛围、光照、声音、气味（可选）
4. 点击 "保存"

### 创建环境连接

1. 在环境管理面板点击 "🔗 管理连接"
2. 点击 "➕ 新建连接"
3. 选择起始环境和目标环境
4. 选择连接类型和方向
5. 添加连接描述（可选）
6. 点击 "保存"

### 切换当前环境

1. 点击 "🔀 切换环境" 按钮
2. 从列表中选择目标环境
3. 点击 "切换"
   - 如果环境连通，直接切换
   - 如果不连通，会警告但允许强制切换

### 查看环境关系图

1. 点击 "🗺️ 关系图" 按钮
2. 查看可视化的环境关系图
   - 🔴 红色节点 - 当前激活环境
   - 🟢 绿色节点 - 其他环境
   - → 单向箭头 - 单向连接
   - ⟷ 双向箭头 - 双向连接

## 数据库结构

### environment_connections 表

| 字段 | 类型 | 说明 |
|------|------|------|
| uuid | TEXT | 连接唯一标识 |
| from_environment_uuid | TEXT | 起始环境UUID |
| to_environment_uuid | TEXT | 目标环境UUID |
| connection_type | TEXT | 连接类型 |
| direction | TEXT | 连接方向 |
| description | TEXT | 连接描述 |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

## API参考

### DatabaseManager

#### create_environment_connection()
创建环境连接

```python
conn_uuid = db.create_environment_connection(
    from_env_uuid: str,
    to_env_uuid: str,
    connection_type: str = "normal",
    direction: str = "bidirectional",
    description: str = ""
) -> str
```

#### can_move_to_environment()
检查是否可以移动到目标环境

```python
can_move = db.can_move_to_environment(
    from_env_uuid: str,
    to_env_uuid: str
) -> bool
```

#### get_connected_environments()
获取与指定环境连通的所有环境

```python
connected_envs = db.get_connected_environments(
    env_uuid: str
) -> List[Dict[str, Any]]
```

#### get_environment_connections()
获取环境的所有连接

```python
connections = db.get_environment_connections(
    env_uuid: str,
    direction: str = "both"  # "from", "to", "both"
) -> List[Dict[str, Any]]
```

### AgentVisionTool

#### detect_environment_switch_intent()
检测用户是否有切换环境的意图

```python
intent = vision.detect_environment_switch_intent(
    user_query: str
) -> Optional[Dict[str, Any]]
```

返回格式：
```python
{
    'intent': 'switch_environment',
    'from_env': {...},  # 当前环境信息
    'to_env': {...},    # 目标环境信息
    'can_switch': True  # 是否可以切换
}
```

#### switch_environment()
切换到指定环境

```python
success = vision.switch_environment(
    to_env_uuid: str
) -> bool
```

#### get_available_environments_for_switch()
获取可以切换到的环境列表

```python
available_envs = vision.get_available_environments_for_switch()
-> List[Dict[str, Any]]
```

## 测试

运行测试脚本：

```bash
python test_environment_switching.py
```

测试涵盖：
- ✅ 环境创建
- ✅ 连接创建
- ✅ 连通性检查
- ✅ 环境切换
- ✅ 权限验证
- ✅ 意图检测

## 最佳实践

### 1. 环境规划

在创建环境连接之前，先规划好环境布局：
- 画出环境关系图
- 确定哪些环境应该连通
- 决定连接类型和方向

### 2. 连接管理

- 使用有意义的连接类型（door, stairs等）
- 添加描述信息说明连接的特点
- 避免创建循环过多的复杂连接

### 3. 用户体验

- 保持环境数量合理（建议10个以内）
- 环境名称简短明确
- 连接关系符合直觉

### 4. 调试

启用DEBUG模式查看详细的切换过程：

```python
# 在.env中设置
DEBUG_MODE=True
```

## 故障排查

### 问题1：切换不起作用

**可能原因：**
- 环境没有建立连接
- 连接方向不对（单向连接）
- 目标环境名称不在查询中

**解决方法：**
1. 检查环境连接：点击 "🔗 管理连接"
2. 查看关系图：点击 "🗺️ 关系图"
3. 确保查询中包含目标环境名称

### 问题2：无法创建连接

**可能原因：**
- 连接已存在
- 环境UUID无效

**解决方法：**
1. 检查是否已有相同的连接
2. 验证环境UUID是否正确

### 问题3：环境显示不完整

**可能原因：**
- 数据库同步问题

**解决方法：**
1. 点击 "🔄 刷新" 按钮
2. 重新加载代理

## 未来增强

计划中的功能：
- [ ] 环境切换动画
- [ ] 路径规划（自动寻找最短路径）
- [ ] 环境访问历史记录
- [ ] 条件性连接（如需要钥匙）
- [ ] 时间限制的连接（特定时间开放）
- [ ] 环境状态系统（锁定/解锁）

## 版本历史

### v1.0 (2025-01-18)
- ✅ 初始实现环境连接系统
- ✅ 实现智能切换检测
- ✅ 添加权限验证
- ✅ 创建GUI管理界面
- ✅ 添加环境关系可视化
- ✅ 完整的测试套件

## 许可证

MIT License - 与项目主许可证相同

## 支持

如有问题或建议，请在项目GitHub仓库提交Issue。
