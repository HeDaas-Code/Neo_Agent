# 环境域(Domain)功能文档

## 概述

环境域(Domain)是一个虚拟的环境集合概念，用于将多个相关的环境组织成一个整体。域提供了层级化的位置管理能力，允许智能体在不同精度级别上理解和描述其所在位置。

### 核心概念

- **域(Domain)**: 多个环境的集合，代表一个抽象的位置概念
  - 例如："小可家" = 小可的房间 + 小可的客厅 + 小可的厨房
  - 例如："学校" = 教室 + 操场 + 图书馆

- **默认环境**: 每个域可以设置一个默认环境，用于域间导航时的目标位置
  - 例如：从"小可家"到"学校"，智能体会到达"学校"的默认环境（如操场）

- **精度级别**:
  - **低精度（域级别）**: 用于简单的位置查询，返回域名称
    - 用户: "你在哪？"
    - 智能体: "我在小可家"
  - **高精度（环境级别）**: 用于详细的环境查询，返回具体环境描述
    - 用户: "周围有什么？"
    - 智能体: "我在小可的房间，房间里有书桌、书架、床..."

## 数据库架构

### 环境域表 (environment_domains)

存储域的基本信息。

| 字段 | 类型 | 说明 |
|------|------|------|
| uuid | TEXT | 域的唯一标识符 |
| name | TEXT | 域名称（如"小可家"） |
| description | TEXT | 域的描述信息 |
| default_environment_uuid | TEXT | 默认环境的UUID（用于域间导航） |
| created_at | TEXT | 创建时间 |
| updated_at | TEXT | 更新时间 |

### 域环境关联表 (domain_environments)

存储域和环境之间的多对多关系。

| 字段 | 类型 | 说明 |
|------|------|------|
| uuid | TEXT | 关联记录的唯一标识符 |
| domain_uuid | TEXT | 域UUID（外键） |
| environment_uuid | TEXT | 环境UUID（外键） |
| created_at | TEXT | 创建时间 |

## 核心API

### DatabaseManager 域相关方法

#### 创建域
```python
domain_uuid = db.create_domain(
    name="小可家",
    description="小可的温馨家庭，包括房间、客厅和厨房",
    default_environment_uuid=living_room_uuid
)
```

#### 查询域
```python
# 获取单个域
domain = db.get_domain(domain_uuid)

# 根据名称查询域
domain = db.get_domain_by_name("小可家")

# 获取所有域
all_domains = db.get_all_domains()
```

#### 更新域
```python
db.update_domain(
    domain_uuid,
    name="新名称",
    description="新描述",
    default_environment_uuid=new_default_uuid
)
```

#### 删除域
```python
db.delete_domain(domain_uuid)
```

#### 管理域和环境的关联
```python
# 添加环境到域
db.add_environment_to_domain(domain_uuid, environment_uuid)

# 从域中移除环境
db.remove_environment_from_domain(domain_uuid, environment_uuid)

# 获取域中的所有环境
environments = db.get_domain_environments(domain_uuid)

# 获取环境所属的所有域
domains = db.get_environment_domains(environment_uuid)

# 检查环境是否在域中
is_in = db.is_environment_in_domain(environment_uuid, domain_uuid)
```

### AgentVisionTool 域相关方法

#### 获取当前域
```python
current_domain = vision_tool.get_current_domain()
if current_domain:
    print(f"当前所在域: {current_domain['name']}")
```

#### 获取域描述
```python
# 获取域的概括描述
description = vision_tool.get_domain_description(domain_uuid)

# 获取域的详细描述（包含默认环境信息）
description = vision_tool.get_domain_description(
    domain_uuid, 
    use_default_env=True
)
```

#### 根据精度获取视觉上下文
```python
# 自动检测精度需求
high_precision = vision_tool.detect_precision_requirement(user_query)

# 根据精度获取上下文
vision_context = vision_tool.get_vision_context_with_precision(
    user_query,
    high_precision=high_precision
)

# 格式化为提示词
prompt = vision_tool.format_vision_prompt(vision_context)
```

#### 域级别导航
```python
# 切换到指定域（会自动切换到默认环境）
success = vision_tool.switch_to_domain(domain_uuid)

# 检测域切换意图
switch_intent = vision_tool.detect_domain_switch_intent("去学校")
if switch_intent:
    target_domain = switch_intent['to_domain']
    vision_tool.switch_to_domain(target_domain['uuid'])
```

## 使用场景

### 场景1: 简单位置查询

**用户**: "你在哪？"

**处理流程**:
1. 检测到位置查询（should_use_vision返回True）
2. 判断精度需求为低（detect_precision_requirement返回False）
3. 获取域级别的上下文（get_vision_context_with_precision）
4. 返回域名称

**智能体回答**: "我在小可家"

### 场景2: 详细环境查询

**用户**: "周围有什么？"

**处理流程**:
1. 检测到环境查询（should_use_vision返回True）
2. 判断精度需求为高（detect_precision_requirement返回True）
3. 获取环境级别的详细上下文（get_vision_context）
4. 返回详细的环境描述和物体列表

**智能体回答**: "我在小可的房间。房间里有书桌、书架、床、台灯..."

### 场景3: 域间导航

**用户**: "去学校"

**处理流程**:
1. 检测域切换意图（detect_domain_switch_intent）
2. 找到目标域"学校"
3. 切换到学校域的默认环境（如操场）
4. 更新当前激活环境

**智能体回答**: "好的，我现在到学校的操场了"

## 设计考虑

### 为什么需要域？

1. **自然的交互体验**: 在日常对话中，人们通常使用抽象的位置概念
   - "我在家" 而不是 "我在卧室"
   - "我在学校" 而不是 "我在教室"

2. **灵活的精度控制**: 根据查询的具体性提供合适详细程度的回答
   - 简单查询 → 域级别回答
   - 详细查询 → 环境级别回答

3. **便捷的导航**: 域间切换自动导航到默认位置
   - 用户说"去学校"，智能体自动到达学校的默认位置（如操场）
   - 无需用户指定具体环境

### 精度检测原理

系统通过关键词匹配来判断用户查询的精度需求：

**高精度关键词**:
- 具体、详细、什么东西、有什么、有哪些
- 看到、周围、附近、房间、屋子
- 物体、物品

**低精度查询**:
- 不包含高精度关键词的位置查询
- 例如："你在哪？"、"在什么地方？"

## 最佳实践

### 1. 合理组织域

将语义相关的环境组织到同一个域中：
```python
# 家庭域
home_domain = db.create_domain("小可家", "...")
db.add_environment_to_domain(home_domain, room_uuid)
db.add_environment_to_domain(home_domain, living_room_uuid)
db.add_environment_to_domain(home_domain, kitchen_uuid)

# 学校域
school_domain = db.create_domain("学校", "...")
db.add_environment_to_domain(school_domain, classroom_uuid)
db.add_environment_to_domain(school_domain, playground_uuid)
```

### 2. 设置合适的默认环境

选择域中最具代表性或最常访问的环境作为默认环境：
```python
# 家的默认环境设为客厅（家人最常聚集的地方）
db.update_domain(home_domain, default_environment_uuid=living_room_uuid)

# 学校的默认环境设为操场（到校后的第一个地方）
db.update_domain(school_domain, default_environment_uuid=playground_uuid)
```

### 3. 建立域间连接

在域的出入口环境之间建立连接：
```python
# 从家的客厅可以去学校的操场
db.create_environment_connection(
    from_env_uuid=living_room_uuid,
    to_env_uuid=playground_uuid,
    direction='bidirectional',
    description='从家出发去学校'
)
```

## 示例代码

完整的使用示例请参见：
- `test_domain_feature.py` - 功能测试脚本
- `demo_domain_feature.py` - 演示脚本

## 扩展建议

### 未来可能的增强

1. **域的层级结构**: 支持域嵌套（如"中国" -> "北京" -> "朝阳区"）
2. **动态精度调整**: 根据对话历史自动调整精度级别
3. **域的属性继承**: 子环境继承域的某些属性
4. **路径规划**: 在多个域之间规划最优路径

## 注意事项

1. 一个环境可以属于多个域
2. 域的默认环境必须是该域包含的环境之一
3. 删除域不会删除其包含的环境，只删除关联关系
4. 精度检测基于关键词匹配，可能不够精确，未来可考虑使用LLM判断
