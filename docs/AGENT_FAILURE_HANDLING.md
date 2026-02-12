# 智能体失败处理修复文档

## 问题描述

### 症状
当多智能体任务中所有智能体都执行失败时（例如遇到API rate limiting错误429），系统仍然将任务标记为成功并更新事件状态为COMPLETED。

### 实际案例
```
任务：搜索关于明日方舟终末地的相关信息

执行过程：
1. 网络信息检索员 → 失败（Error 429: TPM limit reached）
2. 信息分析师 → 失败（Error 429: TPM limit reached）
3. 结果综合 → "成功"（主模型生成了承认失败的文本）
4. 任务状态 → success: true ❌
5. 事件状态 → COMPLETED ❌
```

## 根本原因

### 原有逻辑缺陷

在 `src/core/dynamic_multi_agent_graph.py` 的 `process_task_event` 方法中：

```python
# 旧代码（line 647-653）
if final_state.get('error'):
    return {'success': False, ...}

return {
    'success': True,  # ❌ 无条件返回成功
    'result': final_state.get('final_result', '任务完成'),
    ...
}
```

**问题**：
- 只检查 `final_state` 是否有 `error` 字段
- 即使所有智能体都失败，只要结果综合步骤完成，就返回成功
- 结果综合步骤总能"成功"（主模型会生成承认失败的文本）

### 为什么会这样？

1. **智能体失败不会导致 final_state 错误**
   - 智能体失败时，状态被标记为 `'status': 'failed'`
   - 但执行流程继续，进入结果综合节点
   - `final_state` 没有 `error` 字段

2. **结果综合总是"成功"**
   - 主模型被要求整合智能体结果
   - 即使所有智能体都失败，主模型仍能生成回复
   - 例如："由于rate limiting，无法获取信息..."
   - 这个回复生成"成功"，导致任务被标记为成功

## 解决方案

### 修复逻辑

新增智能体状态检查：

```python
# 新代码（line 647-690）
if final_state.get('error'):
    return {'success': False, ...}

# ✅ 检查智能体执行状态
orchestration_plan = final_state.get('orchestration_plan', {})
agents = orchestration_plan.get('agents', [])

if agents:
    # 统计成功和失败的智能体
    successful_agents = [a for a in agents if a.get('status') == 'completed']
    failed_agents = [a for a in agents if a.get('status') == 'failed']
    
    # 如果所有智能体都失败
    if failed_agents and not successful_agents:
        error_details = []
        for agent in failed_agents:
            error_msg = agent.get('error', '未知错误')
            error_details.append(f"[{agent.get('role')}]: {error_msg}")
        
        return {
            'success': False,  # ✅ 正确标记为失败
            'error': "所有智能体执行失败。详情：\n" + "\n".join(error_details),
            'result': final_state.get('final_result'),  # 保留综合说明
            ...
        }
    
    # 如果有部分失败
    if failed_agents:
        debug_logger.log_warning('DynamicMultiAgentGraph', 
            f'任务部分完成：{len(successful_agents)}/{len(agents)}个智能体成功')

return {'success': True, ...}  # 只有真正成功才返回True
```

## 修复效果

### 场景1：所有智能体失败

**修改前**：
```python
{
    'success': True,  ❌
    'result': '由于rate limiting，无法获取信息...'
}
→ 事件状态: COMPLETED ❌
```

**修改后**：
```python
{
    'success': False,  ✅
    'error': '所有智能体执行失败。详情：\n[网络信息检索员]: Error 429\n[信息分析师]: Error 429',
    'result': '由于rate limiting，无法获取信息...',  # 保留说明
    'failed_agents_count': 2,
    'successful_agents_count': 0
}
→ 事件状态: FAILED ✅
```

### 场景2：部分智能体失败

```python
{
    'success': True,  ✅ 部分成功
    'result': '整合后的结果（基于成功的智能体）',
    ...
}
→ 事件状态: COMPLETED
→ 警告日志: "任务部分完成：1/2个智能体成功"
```

### 场景3：所有智能体成功

```python
{
    'success': True,  ✅
    'result': '完整的任务结果',
    ...
}
→ 事件状态: COMPLETED
```

## 返回结果增强

失败时的返回现在包含更多有用信息：

```python
{
    'success': False,
    'error': '所有智能体执行失败。详情：\n[agent1]: error1\n[agent2]: error2',
    'result': '主模型的综合说明',  # 用户仍能看到系统的解释
    'orchestration_plan': {...},  # 完整的编排计划
    'agent_results': {...},  # 每个智能体的执行结果（包括失败信息）
    'collaboration_logs': [...],  # 完整的执行日志
    'failed_agents_count': 2,
    'successful_agents_count': 0
}
```

## 用户体验改进

### GUI显示

**修改前**：
- 任务显示为"已完成" ✅（绿色）
- 用户以为任务成功了
- 点开才发现实际上失败了

**修改后**：
- 任务显示为"失败" ❌（红色）
- 错误信息清晰列出每个失败的智能体
- 用户立即知道出了问题
- 仍可查看详细的执行日志和说明

### 日志输出

**修改前**：
```
[INFO] EventManager | 事件状态更新
  数据: {"event_id": "xxx", "new_status": "completed"}  ❌
[INFO] ChatAgent | 任务型事件处理完成
  数据: {"event_id": "xxx", "success": true}  ❌
```

**修改后**：
```
[WARNING] DynamicMultiAgentGraph | 所有智能体执行失败
  数据: {"failed_count": 2, "successful_count": 0}
[INFO] EventManager | 事件状态更新
  数据: {"event_id": "xxx", "new_status": "failed"}  ✅
[INFO] ChatAgent | 任务型事件处理完成
  数据: {"event_id": "xxx", "success": false}  ✅
```

## 测试场景

### 1. 所有智能体失败（rate limiting）

```python
# 两个智能体都遇到429错误
agents = [
    {'agent_id': 'agent1', 'status': 'failed', 'error': 'Error 429'},
    {'agent_id': 'agent2', 'status': 'failed', 'error': 'Error 429'}
]

result = process_task_event(...)
assert result['success'] == False  ✅
assert 'Error 429' in result['error']  ✅
assert result['failed_agents_count'] == 2  ✅
```

### 2. 部分智能体失败

```python
agents = [
    {'agent_id': 'agent1', 'status': 'completed'},
    {'agent_id': 'agent2', 'status': 'failed', 'error': 'Error 429'}
]

result = process_task_event(...)
assert result['success'] == True  ✅ 部分成功
# 警告日志会记录失败情况
```

### 3. 所有智能体成功

```python
agents = [
    {'agent_id': 'agent1', 'status': 'completed'},
    {'agent_id': 'agent2', 'status': 'completed'}
]

result = process_task_event(...)
assert result['success'] == True  ✅
```

### 4. Simple策略（无智能体）

```python
# simple策略直接返回结果，不创建智能体
agents = []

result = process_task_event(...)
assert result['success'] == True  ✅ 保持原逻辑
```

## 边界情况处理

### 1. 智能体列表为空
- Simple策略不创建智能体
- 跳过状态检查，直接返回成功
- 保持原有行为

### 2. 智能体状态为pending
- 理论上不应该发生（执行流程应该更新所有状态）
- 如果发生，pending不计入成功或失败
- 只要有successful_agents，任务可以成功

### 3. 没有orchestration_plan
- 某些异常情况可能导致plan丢失
- 跳过状态检查，使用原有逻辑
- 依赖final_state.error判断

## 配置选项

无需额外配置，自动生效。

## 向后兼容性

✅ **完全兼容**：
- 不影响成功场景的行为
- 只修正了错误场景的判断逻辑
- 返回结构保持一致（只是success值更准确）
- 所有现有代码无需修改

## 相关修复

本修复与以下修复协同工作：

1. **800a69f** - 事件状态修复
   - 在`chat_agent.py`中检查`result['success']`
   - 本修复确保`result['success']`的值正确

2. **61a81d7** - UI显示修复
   - 确保失败时仍保留orchestration_plan等数据
   - 本修复确保失败判断准确

## 文件变更

- `src/core/dynamic_multi_agent_graph.py` (line 638-690)
  - 新增智能体状态检查逻辑
  - 新增失败详情收集
  - 新增警告日志

## 提交信息

- Commit: 8e08228
- 标题: Fix: mark task as failed when all agents fail during execution
- 文件: src/core/dynamic_multi_agent_graph.py

## 总结

这个修复确保了任务执行状态的准确性：
- ✅ 所有智能体失败 → 任务失败
- ✅ 部分智能体失败 → 任务成功（带警告）
- ✅ 所有智能体成功 → 任务成功
- ✅ 详细的失败信息
- ✅ 完整的执行数据
- ✅ 准确的事件状态

现在用户可以准确了解任务的真实执行情况！
