# 项目架构图

## 整体系统架构

```mermaid
graph TB
    subgraph "用户界面层"
        UI[GameUI]
        CMD[命令处理器]
    end
    
    subgraph "游戏控制层"
        GAME[AVGGame]
        STATE[游戏状态管理]
    end
    
    subgraph "AI核心层"
        CORE[LLMCore]
        STAGE1[认知阶段]
        STAGE2[记忆阶段]
        STAGE3[理解阶段]
        STAGE4[决策阶段]
        STAGE5[执行阶段]
    end
    
    subgraph "数据层"
        MEM[记忆系统]
        SCRIPT[剧本框架]
        CONFIG[配置管理]
        SAVE[存档系统]
    end
    
    UI --> CMD
    CMD --> GAME
    GAME --> CORE
    GAME --> STATE
    
    CORE --> STAGE1
    STAGE1 --> STAGE2
    STAGE2 --> STAGE3
    STAGE3 --> STAGE4
    STAGE4 --> STAGE5
    
    STAGE2 --> MEM
    STAGE4 --> SCRIPT
    GAME --> CONFIG
    GAME --> SAVE
```

## 五阶段架构详细流程

```mermaid
flowchart TD
    INPUT[用户输入] --> COGNITION[认知阶段]
    
    subgraph "认知阶段处理"
        COGNITION --> PARSE[输入解析]
        PARSE --> INTENT[意图识别]
        INTENT --> CONFIDENCE[置信度评估]
    end
    
    CONFIDENCE --> MEMORY[记忆阶段]
    
    subgraph "记忆阶段处理"
        MEMORY --> RETRIEVE[检索相关记忆]
        RETRIEVE --> KNOWLEDGE[知识图谱查询]
        KNOWLEDGE --> CONTEXT[上下文构建]
    end
    
    CONTEXT --> UNDERSTANDING[理解阶段]
    
    subgraph "理解阶段处理"
        UNDERSTANDING --> ANALYZE[情境分析]
        ANALYZE --> EMOTION[情感理解]
        EMOTION --> GOAL[目标识别]
    end
    
    GOAL --> DECISION[决策阶段]
    
    subgraph "决策阶段处理"
        DECISION --> STRATEGY[策略选择]
        STRATEGY --> SCRIPT_CHECK[剧本约束检查]
        SCRIPT_CHECK --> ACTION[行动规划]
    end
    
    ACTION --> EXECUTION[执行阶段]
    
    subgraph "执行阶段处理"
        EXECUTION --> GENERATE[响应生成]
        GENERATE --> VALIDATE[响应验证]
        VALIDATE --> OUTPUT[最终输出]
    end
    
    OUTPUT --> STORE[存储交互记录]
    STORE --> UPDATE[更新游戏状态]
```

## 命令系统架构

```mermaid
graph LR
    subgraph "基本命令"
        HELP[help/h]
        STATUS[status/st]
        DETAIL[detail/dt]
        VERBOSE[verbose/v]
        QUIT[quit/exit/q]
    end
    
    subgraph "游戏命令"
        INV[inventory/inv]
        KNOW[knowledge/k]
        LOOK[look/l]
        SAVE[save]
        LOAD[load]
    end
    
    subgraph "剧情命令"
        STORY[story/s]
        BRANCH[branches/br]
        PROGRESS[progress/pr]
        SELECT[select]
    end
    
    subgraph "交互命令"
        TALK[talk]
        ASK[ask]
        TELL[tell]
        DIALOGUE[自然对话]
    end
    
    HELP --> UI_HELP[显示帮助]
    STATUS --> UI_STATUS[基本状态]
    DETAIL --> UI_DETAIL[详细状态]
    VERBOSE --> MODE_TOGGLE[切换详细模式]
    
    STORY --> STORY_STATUS[剧情状态]
    BRANCH --> STORY_BRANCHES[可用分支]
    PROGRESS --> STORY_PROGRESS[剧情进度]
    SELECT --> STORY_SELECT[选择分支]
    
    TALK --> AI_PROCESS[AI对话处理]
    ASK --> AI_PROCESS
    TELL --> AI_PROCESS
    DIALOGUE --> AI_PROCESS
```

## 系统整体架构

```mermaid
graph TB
    subgraph "LLM Core System"
        A[User Input] --> B[LLMCore.process_dialogue]
        B --> C[Five-Stage Pipeline]
        
        subgraph "Five-Stage Pipeline"
            C1[1. Cognition Stage]
            C2[2. Memory Stage]
            C3[3. Understanding Stage]
            C4[4. Decision Stage]
            C5[5. Execution Stage]
            
            C1 --> C2
            C2 --> C3
            C3 --> C4
            C4 --> C5
        end
        
        C5 --> D[Final Response]
    end
    
    subgraph "Supporting Systems"
        E[ModelManager]
        F[MemorySystem]
        G[CharacterController]
        H[ScriptFrameworkConstrainer]
        I[KnowledgeGraph]
        J[GameStateManager]
    end
    
    C1 -.-> G
    C1 -.-> H
    C1 -.-> J
    C2 -.-> F
    C2 -.-> I
    C3 -.-> E
    C4 -.-> G
    C4 -.-> H
    C5 -.-> E
    C5 -.-> F
    C5 -.-> J
```

## 五阶段详细流程

```mermaid
flowchart TD
    Start([User Input]) --> Stage1
    
    subgraph "Stage 1: Cognition"
        Stage1[Analyze Scene Status]
        Stage1 --> S1A[Integrate Character Profile]
        S1A --> S1B[Evaluate Interaction History]
        S1B --> S1C[CognitionResult]
    end
    
    S1C --> Stage2
    
    subgraph "Stage 2: Memory"
        Stage2[Retrieve Long-term Memory]
        Stage2 --> S2A[Update Dialogue Cache]
        S2A --> S2B[Associate Knowledge Nodes]
        S2B --> S2C[MemoryResult]
    end
    
    S2C --> Stage3
    
    subgraph "Stage 3: Understanding"
        Stage3[Parse Dialogue Intent]
        Stage3 --> S3A[Evaluate Suggestion Feedback]
        S3A --> S3B[Identify Sentiment Shift]
        S3B --> S3C[UnderstandingResult]
    end
    
    S3C --> Stage4
    
    subgraph "Stage 4: Decision"
        Stage4[Generate Response Options]
        Stage4 --> S4A[Calculate Utility Scores]
        S4A --> S4B[Select Dialogue Strategy]
        S4B --> S4C[DecisionResult]
    end
    
    S4C --> Stage5
    
    subgraph "Stage 5: Execution"
        Stage5[Output NLP Response]
        Stage5 --> S5A[Trigger Game Actions]
        S5A --> S5B[Update Character State]
        S5B --> S5C[ExecutionResult]
    end
    
    S5C --> End([Final Response])
```

## 数据流向图

```mermaid
graph LR
    subgraph "Input Data"
        I1[user_input]
        I2[character_state]
        I3[game_state]
        I4[previous_dialogue]
    end
    
    subgraph "Stage Results"
        R1[CognitionResult]
        R2[MemoryResult]
        R3[UnderstandingResult]
        R4[DecisionResult]
        R5[ExecutionResult]
    end
    
    subgraph "Output Data"
        O1[nlp_output]
        O2[game_action]
        O3[character_state_update]
    end
    
    I1 --> R1
    I2 --> R1
    I3 --> R1
    I4 --> R1
    
    R1 --> R2
    R2 --> R3
    R3 --> R4
    R4 --> R5
    
    R5 --> O1
    R5 --> O2
    R5 --> O3
```

## 模块依赖关系

```mermaid
graph TB
    subgraph "Core Module"
        LLMCore[LLMCore]
    end
    
    subgraph "Stage Processors"
        CP[CognitionProcessor]
        MP[MemoryProcessor]
        UP[UnderstandingProcessor]
        DP[DecisionProcessor]
        EP[ExecutionProcessor]
    end
    
    subgraph "Data Classes"
        CR[CognitionResult]
        MR[MemoryResult]
        UR[UnderstandingResult]
        DR[DecisionResult]
        ER[ExecutionResult]
    end
    
    subgraph "External Systems"
        MM[ModelManager]
        MS[MemorySystem]
        CC[CharacterController]
        SFC[ScriptFrameworkConstrainer]
        KG[KnowledgeGraph]
        GSM[GameStateManager]
    end
    
    LLMCore --> CP
    LLMCore --> MP
    LLMCore --> UP
    LLMCore --> DP
    LLMCore --> EP
    
    CP --> CR
    MP --> MR
    UP --> UR
    DP --> DR
    EP --> ER
    
    CP -.-> CC
    CP -.-> SFC
    CP -.-> GSM
    
    MP -.-> MS
    MP -.-> KG
    
    UP -.-> MM
    
    DP -.-> CC
    DP -.-> SFC
    
    EP -.-> MM
    EP -.-> MS
    EP -.-> GSM
```

## 错误处理流程

```mermaid
flowchart TD
    Start([Stage Execution]) --> Try{Try Execute}
    Try -->|Success| Next[Next Stage]
    Try -->|Error| Catch[Catch Exception]
    
    Catch --> Log[Log Error]
    Log --> Fallback{Fallback Available?}
    
    Fallback -->|Yes| FB[Execute Fallback]
    Fallback -->|No| Fail[Stage Failure]
    
    FB --> Validate{Validate Result}
    Validate -->|Valid| Next
    Validate -->|Invalid| Fail
    
    Fail --> ErrorResponse[Generate Error Response]
    ErrorResponse --> End([Return Error])
    
    Next --> End2([Continue Pipeline])
```

## 性能监控点

```mermaid
graph LR
    subgraph "Performance Metrics"
        M1[Stage Execution Time]
        M2[Memory Usage]
        M3[API Call Count]
        M4[Cache Hit Rate]
        M5[Error Rate]
    end
    
    subgraph "Monitoring Points"
        P1[Stage Entry]
        P2[Stage Exit]
        P3[API Calls]
        P4[Memory Operations]
        P5[Error Handlers]
    end
    
    P1 --> M1
    P2 --> M1
    P2 --> M2
    P3 --> M3
    P4 --> M4
    P5 --> M5
```

## 配置管理

```mermaid
graph TB
    subgraph "Configuration Files"
        C1[config/model.json]
        C2[config/character.json]
        C3[config/memory.json]
        C4[config/script.json]
        C5[config/game.json]
    end
    
    subgraph "Stage Configuration"
        SC1[Cognition Config]
        SC2[Memory Config]
        SC3[Understanding Config]
        SC4[Decision Config]
        SC5[Execution Config]
    end
    
    C1 --> SC3
    C1 --> SC5
    C2 --> SC1
    C2 --> SC4
    C3 --> SC2
    C4 --> SC1
    C4 --> SC4
    C5 --> SC1
    C5 --> SC5
```

---

**架构设计说明:**

1. **模块化设计**: 每个阶段都是独立的处理单元，便于维护和测试
2. **数据驱动**: 明确的数据结构定义，确保阶段间数据传递的一致性
3. **错误隔离**: 每个阶段都有独立的错误处理机制
4. **性能监控**: 关键节点都有性能监控，便于优化
5. **配置化**: 支持通过配置文件调整各阶段的行为
6. **可扩展性**: 新功能可以作为新阶段插入，或在现有阶段中扩展

**版本**: v1.0  
**创建时间**: 2025-09-10  
**更新时间**: 2025-09-10
