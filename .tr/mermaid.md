# LLM驱动AVG游戏 - 系统架构图

## 整体系统架构

```mermaid
graph TB
    subgraph "用户交互层"
        UI[游戏界面]
        Input[用户输入]
    end
    
    subgraph "LLM驱动核心 (llm_core.py)"
        Core[LLMCore主控制器]
        
        subgraph "模型管理"
            MM[ModelManager]
            DeepSeek[DeepSeek API]
            BGE[BGE嵌入模型]
        end
        
        subgraph "记忆系统"
            MS[MemorySystem]
            Chroma[ChromaDB向量库]
        end
        
        subgraph "角色控制"
            CC[CharacterController]
            Prompts[多层级提示词]
        end
        
        subgraph "知识管理"
            KG[KnowledgeGraph]
            Info[信息边界控制]
        end
        
        subgraph "游戏状态"
            GS[GameState]
            Perms[权限等级]
            Frags[数据碎片]
            Crew[船员状态]
        end
    end
    
    subgraph "游戏系统层"
        NS[叙事对话系统]
        PS[权限层级系统]
        DM[数据碎片管理]
        LM[生命指标监测]
        ED[事件驱动系统]
    end
    
    %% 数据流向
    UI --> Input
    Input --> Core
    Core --> MM
    Core --> MS
    Core --> CC
    Core --> KG
    Core --> GS
    
    MM --> DeepSeek
    MM --> BGE
    MS --> Chroma
    CC --> Prompts
    KG --> Info
    GS --> Perms
    GS --> Frags
    GS --> Crew
    
    Core --> NS
    Core --> PS
    Core --> DM
    Core --> LM
    Core --> ED
    
    NS --> UI
```

## 核心类关系图

```mermaid
classDiagram
    class LLMCore {
        +ModelManager model_manager
        +MemorySystem memory_system
        +CharacterController character_controller
        +KnowledgeGraph knowledge_graph
        +GameState game_state
        +process_input(text) str
        +update_game_state()
        +get_character_response(input, context)
    }
    
    class ModelManager {
        +str deepseek_api_key
        +str bge_model_path
        +call_deepseek_api(prompt) str
        +get_embeddings(text) list
        +handle_api_error(error)
    }
    
    class MemorySystem {
        +ChromaDB client
        +str collection_name
        +store_memory(text, metadata)
        +retrieve_memories(query, limit) list
        +update_memory(id, content)
        +delete_memory(id)
    }
    
    class CharacterController {
        +dict character_config
        +dict prompt_templates
        +build_system_prompt() str
        +apply_character_constraints(response) str
        +update_character_state(emotion, health)
    }
    
    class KnowledgeGraph {
        +dict known_information
        +dict access_permissions
        +check_information_access(info_id) bool
        +unlock_information(info_id)
        +get_available_knowledge() list
    }
    
    class GameState {
        +int permission_level
        +list data_fragments
        +dict crew_status
        +dict current_location
        +update_permission(level)
        +add_fragment(fragment)
        +update_crew_status(status)
        +trigger_events() list
    }
    
    LLMCore --> ModelManager
    LLMCore --> MemorySystem
    LLMCore --> CharacterController
    LLMCore --> KnowledgeGraph
    LLMCore --> GameState
    
    ModelManager --> "DeepSeek API"
    ModelManager --> "BGE Model"
    MemorySystem --> "ChromaDB"
```

## 数据流程图

```mermaid
sequenceDiagram
    participant User as 用户
    participant Core as LLMCore
    participant Memory as MemorySystem
    participant Character as CharacterController
    participant Knowledge as KnowledgeGraph
    participant Model as ModelManager
    participant State as GameState
    
    User->>Core: 输入对话文本
    Core->>Memory: 检索相关记忆
    Memory-->>Core: 返回上下文记忆
    
    Core->>Knowledge: 检查信息访问权限
    Knowledge-->>Core: 返回可用知识
    
    Core->>State: 获取当前游戏状态
    State-->>Core: 返回权限、碎片、船员状态
    
    Core->>Character: 构建角色提示词
    Character-->>Core: 返回系统提示词
    
    Core->>Model: 调用LLM生成响应
    Model->>Model: 调用DeepSeek API
    Model-->>Core: 返回生成的响应
    
    Core->>Character: 应用角色约束过滤
    Character-->>Core: 返回过滤后响应
    
    Core->>Memory: 存储对话记忆
    Core->>State: 更新游戏状态
    
    Core-->>User: 返回最终响应
```

## 模块依赖关系

```mermaid
graph LR
    subgraph "外部依赖"
        Requests[requests库]
        ChromaDB[chromadb库]
        JSON[json库]
        Asyncio[asyncio库]
        Logging[logging库]
    end
    
    subgraph "核心模块"
        LLMCore[LLMCore]
        ModelManager[ModelManager]
        MemorySystem[MemorySystem]
        CharacterController[CharacterController]
        KnowledgeGraph[KnowledgeGraph]
        GameState[GameState]
    end
    
    subgraph "外部服务"
        DeepSeekAPI[硅基流动API]
        BGEModel[BGE嵌入模型]
    end
    
    ModelManager --> Requests
    ModelManager --> DeepSeekAPI
    ModelManager --> BGEModel
    
    MemorySystem --> ChromaDB
    
    LLMCore --> JSON
    LLMCore --> Asyncio
    LLMCore --> Logging
    
    LLMCore --> ModelManager
    LLMCore --> MemorySystem
    LLMCore --> CharacterController
    LLMCore --> KnowledgeGraph
    LLMCore --> GameState
```

## 配置文件结构

```mermaid
graph TB
    subgraph "配置文件"
        Config[config.json]
        
        subgraph "角色配置"
            CharConfig[character_config]
            Personality[人格设定]
            Emotions[情绪状态]
            Knowledge[初始知识]
        end
        
        subgraph "API配置"
            APIConfig[api_config]
            DeepSeekKey[DeepSeek API Key]
            BGEPath[BGE模型路径]
            Endpoints[API端点]
        end
        
        subgraph "游戏配置"
            GameConfig[game_config]
            Permissions[权限等级定义]
            Fragments[数据碎片配置]
            Events[事件触发条件]
        end
    end
    
    Config --> CharConfig
    Config --> APIConfig
    Config --> GameConfig
    
    CharConfig --> Personality
    CharConfig --> Emotions
    CharConfig --> Knowledge
    
    APIConfig --> DeepSeekKey
    APIConfig --> BGEPath
    APIConfig --> Endpoints
    
    GameConfig --> Permissions
    GameConfig --> Fragments
    GameConfig --> Events
```