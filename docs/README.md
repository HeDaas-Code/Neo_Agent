# Neo Agent 提示词系统

本目录包含Neo Agent的所有提示词模板，采用模块化设计，支持灵活配置和扩展。

## 目录结构

```
prompts/
├── README.md                    # 提示词系统说明
├── character/                   # 角色设定模板
│   ├── default_character.md    # 默认角色模板
│   ├── character_template.md   # 角色模板示例
│   └── [自定义角色].md         # 自定义角色文件
├── system/                      # 系统提示词模板
│   ├── chat_system.md          # 聊天系统提示词
│   ├── emotion_analysis.md     # 情感分析提示词
│   ├── knowledge_extraction.md # 知识提取提示词
│   └── task_coordination.md    # 任务协调提示词
├── task/                        # 任务相关提示词
│   ├── sub_agent_task.md       # 子智能体任务模板
│   └── schedule_intent.md      # 日程意图识别模板
└── worldview/                   # 世界观设定
    ├── default_world.md        # 默认世界观
    └── [自定义世界观].md       # 自定义世界观文件
```

## 使用说明

### 1. 角色设定 (Character)

角色设定文件定义AI的人格、背景和行为方式。每个角色文件包含：

- **基本信息**：姓名、年龄、性别、身份等
- **性格特征**：性格描述、说话风格等
- **背景故事**：角色的背景和经历
- **兴趣爱好**：角色的爱好和专长
- **行为准则**：角色的行为规范和限制

### 2. 系统提示词 (System)

系统提示词定义不同功能模块的行为和输出格式：

- `chat_system.md`：主要对话系统的行为准则
- `emotion_analysis.md`：情感分析的评估标准和输出格式
- `knowledge_extraction.md`：知识提取的规则和结构
- `task_coordination.md`：多智能体协作的协调规则

### 3. 任务提示词 (Task)

任务提示词定义特定任务的执行方式：

- `sub_agent_task.md`：子智能体执行任务的标准模板
- `schedule_intent.md`：日程意图识别的分析规则

### 4. 世界观设定 (Worldview)

世界观文件定义AI所处的虚拟世界背景：

- 世界的基本规则和设定
- 环境描述和氛围
- 角色之间的关系网络
- 可能的事件和情境

## 模板变量

提示词模板支持以下变量替换：

- `{character_name}` - 角色名称
- `{character_gender}` - 角色性别
- `{character_age}` - 角色年龄
- `{character_role}` - 角色身份
- `{character_personality}` - 性格特征
- `{character_background}` - 背景故事
- `{character_hobby}` - 兴趣爱好
- `{world_name}` - 世界名称
- `{world_setting}` - 世界设定
- `{context}` - 上下文信息
- `{task_description}` - 任务描述

## 自定义提示词

### 创建自定义角色

1. 复制 `character/character_template.md` 
2. 修改角色信息
3. 保存为新文件名（如 `my_character.md`）
4. 在 `.env` 文件中设置 `CHARACTER_PROMPT_FILE=my_character`

### 创建自定义世界观

1. 复制 `worldview/default_world.md`
2. 修改世界设定
3. 保存为新文件名（如 `my_world.md`）
4. 在 `.env` 文件中设置 `WORLDVIEW_FILE=my_world`

## 提示词设计原则

1. **清晰性**：使用简洁明确的语言，避免歧义
2. **结构化**：使用标题、列表等结构化格式组织内容
3. **示例驱动**：提供具体示例说明期望的行为
4. **灵活性**：使用变量支持不同配置
5. **模块化**：将不同功能的提示词分离，便于维护

## 提示词优化建议

- 根据实际使用效果迭代优化提示词
- 使用A/B测试比较不同版本的效果
- 记录用户反馈，持续改进
- 参考成功案例（如SillyTavern）的提示词工程经验

## 参考资源

- [SillyTavern](https://github.com/SillyTavern/SillyTavern) - 优秀的角色扮演AI项目
- [LangChain提示词工程](https://python.langchain.com/docs/modules/model_io/prompts/)
- [提示词工程指南](https://www.promptingguide.ai/)
