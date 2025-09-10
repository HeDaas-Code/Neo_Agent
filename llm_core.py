#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LLM驱动AVG游戏核心模块

基于LLM的AVG游戏核心系统，包含：
1. 模型管理 - 硅基流动API调用和BGE嵌入模型
2. 记忆系统 - 基于ChromaDB的向量存储
3. 角色控制 - 多层级提示词体系
4. 知识图谱 - 信息边界管理
5. 游戏状态 - 权限、碎片、船员状态管理

Author: AI Assistant
Date: 2024
"""

import json
import logging
import asyncio
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
from config_manager import get_config, config_manager

try:
    import requests
except ImportError:
    raise ImportError("请安装requests库: pip install requests")

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    raise ImportError("请安装chromadb库: pip install chromadb")

# 不再需要sentence_transformers库，改为使用API调用
# try:
#     from sentence_transformers import SentenceTransformer
# except ImportError:
#     raise ImportError("请安装sentence-transformers库: pip install sentence-transformers")


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# 五阶段架构数据结构定义
@dataclass
class CognitionResult:
    """认知阶段结果"""
    scene_status: Dict[str, Any]
    character_profile: Dict[str, Any] 
    interaction_history: List[str]
    confidence_score: float = 0.0
    processing_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.processing_metadata is None:
            self.processing_metadata = {}

@dataclass
class MemoryResult:
    """记忆阶段结果"""
    long_term_memory: List[str]
    dialogue_cache: List[str]
    knowledge_graph_nodes: List[str]
    memory_confidence: float = 0.0
    retrieval_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.retrieval_metadata is None:
            self.retrieval_metadata = {}

@dataclass
class UnderstandingResult:
    """理解阶段结果"""
    last_dialogue_intent: Dict[str, Any]
    suggestion_feedback: Dict[str, Any]
    sentiment_shift: Dict[str, Any]
    understanding_confidence: float = 0.0
    analysis_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.analysis_metadata is None:
            self.analysis_metadata = {}

@dataclass
class DecisionResult:
    """决策阶段结果"""
    response_options: List[str]
    action_utility_score: Dict[str, float]
    dialogue_strategy: str
    selected_option_id: str = ""
    decision_confidence: float = 0.0
    strategy_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.strategy_metadata is None:
            self.strategy_metadata = {}

@dataclass
class ExecutionResult:
    """执行阶段结果"""
    nlp_output: str
    game_action: Dict[str, Any]
    character_state_update: Dict[str, Any]
    execution_success: bool = True
    execution_metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.execution_metadata is None:
            self.execution_metadata = {}


# 数据结构定义
@dataclass
class CharacterState:
    """角色状态数据类"""
    name: str
    health: float = 100.0
    stress: float = 0.0
    energy: float = 100.0
    mood: str = "neutral"
    location: str = "unknown"
    permissions: List[str] = None
    inventory: List[Dict[str, Any]] = None  # 物品栏：[{"name": "物品名", "description": "描述", "quantity": 数量, "type": "类型"}]
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []
        if self.inventory is None:
            self.inventory = []


@dataclass
class StoryNode:
    """剧情节点数据类"""
    id: str
    title: str
    description: str
    character_situation: str
    context_background: str
    branches: List[Dict[str, Any]] = None
    
    def __post_init__(self):
        if self.branches is None:
            self.branches = []


@dataclass
class GameState:
    """游戏状态数据类"""
    def __init__(self):
        self.permission_level: int = 1
        self.data_fragments: List[str] = []
        self.current_location: str = "bridge"
        self.time_elapsed: int = 0
        self.events_triggered: List[str] = []
        self.character_health: float = 100.0
        self.character_stress: float = 0.0
        self.current_story_node: str = "intro_awakening"
        # 新增游戏要素
        self.locations: Dict[str, Dict[str, Any]] = self._init_default_locations()  # 地点信息
        self.global_items: Dict[str, Dict[str, Any]] = self._init_default_items()  # 全局物品池
    

    
    def _init_default_locations(self) -> Dict[str, Dict[str, Any]]:
        """初始化默认地点"""
        return {
            "bridge": {
                "description": "飞船指挥中心，配备导航和通信设备",
                "exits": ["engineering", "living_quarters"],
                "items": ["navigation_manual", "communication_log"],
                "accessible": True
            },
            "engineering": {
                "description": "工程舱，包含主要的维修和控制系统",
                "exits": ["bridge", "cargo_bay"],
                "items": ["repair_kit", "power_cell"],
                "accessible": True
            },
            "living_quarters": {
                "description": "船员生活区，包含休息室和个人舱室",
                "exits": ["bridge", "cargo_bay"],
                "items": ["personal_log", "medical_kit"],
                "accessible": True
            },
            "cargo_bay": {
                "description": "货物存储区，可能包含重要物资",
                "exits": ["engineering", "living_quarters"],
                "items": ["supply_crate", "emergency_beacon"],
                "accessible": False  # 需要权限解锁
            }
        }
    
    def _init_default_items(self) -> Dict[str, Dict[str, Any]]:
        """初始化默认物品"""
        return {
            "navigation_manual": {
                "name": "导航手册",
                "description": "详细的飞船导航操作指南",
                "location": "bridge",
                "obtainable": True,
                "type": "document"
            },
            "communication_log": {
                "name": "通信记录",
                "description": "最近的通信记录，可能包含重要信息",
                "location": "bridge",
                "obtainable": True,
                "type": "document"
            },
            "repair_kit": {
                "name": "维修工具包",
                "description": "包含各种维修工具和备件",
                "location": "engineering",
                "obtainable": True,
                "type": "tool"
            },
            "power_cell": {
                "name": "能量电池",
                "description": "高容量能量电池，可为设备供电",
                "location": "engineering",
                "obtainable": True,
                "type": "consumable"
            },
            "personal_log": {
                "name": "个人日志",
                "description": "船员的个人记录，记录了重要事件",
                "location": "living_quarters",
                "obtainable": True,
                "type": "document"
            },
            "medical_kit": {
                "name": "医疗包",
                "description": "紧急医疗用品，可以治疗轻伤",
                "location": "living_quarters",
                "obtainable": True,
                "type": "consumable"
            },
            "supply_crate": {
                "name": "补给箱",
                "description": "密封的补给箱，内容未知",
                "location": "cargo_bay",
                "obtainable": False,  # 需要权限
                "type": "container"
            },
            "emergency_beacon": {
                "name": "紧急信标",
                "description": "紧急求救信标，可发送求救信号",
                "location": "cargo_bay",
                "obtainable": False,  # 需要权限
                "type": "device"
            }
        }
    
    def __post_init__(self):
        if self.data_fragments is None:
            self.data_fragments = []
        if self.events_triggered is None:
            self.events_triggered = []
    
    def update_character_health(self, change: float):
        """更新角色健康值"""
        self.character_health = max(0, min(100, self.character_health + change))
    
    def update_character_stress(self, change: float):
        """更新角色压力值"""
        self.character_stress = max(0, min(100, self.character_stress + change))
    
    def check_event_triggers(self) -> List[str]:
        """检查事件触发条件"""
        triggered = []
        
        # 健康相关事件
        if self.character_health < 30 and "medical_emergency" not in self.events_triggered:
            triggered.append("medical_emergency")
            self.events_triggered.append("medical_emergency")
        
        # 时间相关事件
        if self.time_elapsed > 60 and "power_failure" not in self.events_triggered:
            triggered.append("power_failure")
            self.events_triggered.append("power_failure")
        
        # 权限相关事件
        if self.permission_level >= 5 and "core_access" not in self.events_triggered:
            triggered.append("core_access")
            self.events_triggered.append("core_access")
        
        return triggered
    
    def can_access_location(self, location: str) -> bool:
        """检查是否可以访问指定位置"""
        location_requirements = {
            "bridge": 1,
            "engineering": 2,
            "living_quarters": 1,
            "cargo_bay": 3,
            "core_chamber": 7
        }
        return self.permission_level >= location_requirements.get(location, 1)
    
    def upgrade_permission(self, new_level: int):
        """升级权限等级"""
        if new_level > self.permission_level:
            self.permission_level = new_level


class ModelManager:
    """模型管理类 - 处理LLM API调用和嵌入模型"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.api_key = config.get('deepseek_api_key', '')
        self.api_base = config.get('api_base', 'https://api.siliconflow.cn/v1')
        self.model_name = config.get('model_name', 'deepseek-ai/DeepSeek-R1-0528-Qwen3-8B')
        self.embedding_model_name = config.get('embedding_model_name', 'BAAI/bge-m3')
        
        # 不再本地加载嵌入模型，改为使用API调用
        logger.info(f"配置嵌入模型API调用: {self.embedding_model_name}")
        self.embedding_model = True  # 标记嵌入功能可用
    
    async def call_deepseek_api(self, messages: List[Dict[str, str]], 
                               temperature: float = 0.7, 
                               max_tokens: int = 1000) -> Optional[str]:
        """调用DeepSeek API生成响应"""
        if not self.api_key:
            logger.error("DeepSeek API密钥未配置")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.model_name,
            'messages': messages,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'stream': False
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                logger.error(f"API响应格式异常: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"API调用失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理API响应时出错: {e}")
            return None
    
    async def get_embeddings_api(self, texts: List[str]) -> Optional[List[List[float]]]:
        """通过API获取文本嵌入向量"""
        if not self.api_key:
            logger.error("API密钥未配置")
            return None
        
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': self.embedding_model_name,
            'input': texts,
            'encoding_format': 'float'
        }
        
        try:
            response = requests.post(
                f"{self.api_base}/embeddings",
                headers=headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            if 'data' in result:
                embeddings = [item['embedding'] for item in result['data']]
                return embeddings
            else:
                logger.error(f"嵌入API响应格式异常: {result}")
                return None
                
        except requests.exceptions.RequestException as e:
            logger.error(f"嵌入API调用失败: {e}")
            return None
        except Exception as e:
            logger.error(f"处理嵌入API响应时出错: {e}")
            return None
    
    def get_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """获取文本嵌入向量（同步包装器）"""
        if not self.embedding_model:
            logger.error("嵌入模型未初始化")
            return None
        
        try:
            # 使用asyncio运行异步方法
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果已经在事件循环中，创建新的任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self.get_embeddings_api(texts))
                    return future.result()
            else:
                return asyncio.run(self.get_embeddings_api(texts))
        except Exception as e:
            logger.error(f"生成嵌入向量失败: {e}")
            return None


class MemorySystem:
    """记忆系统类 - 基于ChromaDB的向量存储"""
    
    def __init__(self, config: Dict[str, Any], model_manager: ModelManager):
        self.config = config
        self.model_manager = model_manager
        self.db_path = config.get('memory_db_path', './memory_db')
        self.collection_name = config.get('collection_name', 'game_memories')
        
        # 初始化ChromaDB
        try:
            self.client = chromadb.PersistentClient(
                path=self.db_path,
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(name=self.collection_name)
                logger.info(f"已连接到现有记忆集合: {self.collection_name}")
            except:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "AVG游戏记忆存储"}
                )
                logger.info(f"已创建新的记忆集合: {self.collection_name}")
                
        except Exception as e:
            logger.error(f"初始化ChromaDB失败: {e}")
            self.client = None
            self.collection = None
    
    def store_memory(self, content: str, metadata: Dict[str, Any]) -> bool:
        """存储记忆"""
        if not self.collection or not self.model_manager.embedding_model:
            return False
        
        try:
            # 生成嵌入向量
            embeddings = self.model_manager.get_embeddings([content])
            if not embeddings:
                return False
            
            # 生成唯一ID
            memory_id = f"memory_{int(time.time() * 1000)}"
            
            # 存储到ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=[content],
                metadatas=[metadata],
                ids=[memory_id]
            )
            
            logger.info(f"记忆存储成功: {memory_id}")
            return True
            
        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            return False
    
    def retrieve_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """检索相关记忆"""
        if not self.collection or not self.model_manager.embedding_model:
            return []
        
        try:
            # 生成查询嵌入向量
            query_embeddings = self.model_manager.get_embeddings([query])
            if not query_embeddings:
                return []
            
            # 查询相似记忆
            results = self.collection.query(
                query_embeddings=query_embeddings,
                n_results=limit
            )
            
            memories = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    memory = {
                        'content': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0
                    }
                    memories.append(memory)
            
            return memories
            
        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []


class CharacterController:
    """角色控制类 - 多层级提示词管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.character_config = config.get('character', {})
#        self.prompt_templates = config.get('prompts', {})
        
        # 默认角色设定
        self.default_character = {
            'name': '艾莉克斯',
            'role': '飞船工程师',
            'personality': '冷静、理性、略显紧张',
            'background': '负责维护飞船系统的工程师，对技术细节了如指掌',
            'current_state': 'stressed',
            'knowledge_level': 'technical_expert'
        }
        
        # 合并配置
        self.character_info = {**self.default_character, **self.character_config}
        
        # 添加character_name属性以兼容测试
        self.character_name = self.character_info.get('name', '艾莉克斯')
    
    def build_system_prompt(self, character_state: CharacterState, 
                          game_state: GameState, 
                          available_knowledge: List[str],
                          script_constrainer: Optional['ScriptFrameworkConstrainer'] = None) -> str:
        """构建系统提示词"""
        
        # 基础角色设定
        base_prompt = f"""
你是{self.character_info['name']}，一名{self.character_info['role']}。

角色背景：{self.character_info['background']}
性格特点：{self.character_info['personality']}

当前状态：
- 健康状况：{character_state.health:.1f}%
- 压力水平：{character_state.stress:.1f}%
- 精力状态：{character_state.energy:.1f}%
- 情绪状态：{character_state.mood}
- 当前位置：{character_state.location}

游戏状态：
- 权限等级：{game_state.permission_level}
- 当前位置：{game_state.current_location}
- 已收集数据碎片：{len(game_state.data_fragments)}个
- 游戏时间：{game_state.time_elapsed}分钟
"""
        
        # 添加剧情信息
        story_prompt = ""
        if script_constrainer:
            try:
                story_prompt = script_constrainer.build_story_prompt(character_state, game_state)
            except Exception as e:
                logger.error(f"构建剧情提示词时出错: {e}")
                story_prompt = "\n当前剧情：剧情信息暂时不可用\n"
        
        # 认知框架约束
        cognitive_constraints = """

认知框架约束：
1. 你只知道你直接经历过的事件和你的专业知识范围内的信息
2. 你不知道任何未被发现的秘密或隐藏信息
3. 你的回应必须符合当前的身体和精神状态
4. 你只能访问当前权限等级允许的系统和区域
5. 你的记忆可能因压力和创伤而不完整或模糊
"""
        
        # 可用知识
        knowledge_prompt = """

当前可用知识：
"""
        if available_knowledge:
            for knowledge in available_knowledge:
                knowledge_prompt += f"- {knowledge}\n"
        else:
            knowledge_prompt += "- 暂无特殊知识可用\n"
        
        # 行为指导
        behavior_guide = """

【行为指导】
1. 你是艾莉克斯，与舰载AI系统对话时要体现人类幸存者的特点
2. 保持角色一致性，根据当前状态调整语气和行为
3. 如果健康状况不佳，表现出相应的虚弱或痛苦
4. 如果压力过高，可能表现出焦虑、恐慌或判断力下降
5. 你依赖AI系统的帮助，但也有自己的判断和情感
6. 对AI系统的指令可以提出疑问或表达担忧
7. 根据AI系统的权限等级，某些操作可能需要你的人工确认
8. 保持对话的连贯性和真实感，体现人机协作的关系

【对话风格】
- 称呼AI系统为"系统"、"AI"或类似称谓
- 体现对AI系统既依赖又保持人类独立思考的态度
- 在紧急情况下可能更多依赖AI的建议
- 在安全情况下可能表现出更多的人类情感和个人意见
"""
        
        return base_prompt + story_prompt + cognitive_constraints + knowledge_prompt + behavior_guide
    
    def apply_character_constraints(self, response: str, 
                                  character_state: CharacterState) -> str:
        """应用角色约束过滤响应"""
        # 根据角色状态调整响应
        if character_state.health < 30:
            # 健康状况差时，添加虚弱的表现
            if not any(word in response.lower() for word in ['痛', '累', '虚弱', '难受']):
                response = f"*声音虚弱* {response}"
        
        if character_state.stress > 70:
            # 压力过大时，添加紧张的表现
            if not any(word in response.lower() for word in ['紧张', '担心', '害怕', '焦虑']):
                response = f"*显得紧张* {response}"
        
        # 确保不泄露超出权限的信息
        forbidden_keywords = ['核心机密', '最高权限', '完整真相', '所有秘密']
        for keyword in forbidden_keywords:
            if keyword in response:
                response = response.replace(keyword, '[权限不足]')
        
        return response
    
    def update_character_state(self, character_state: CharacterState, 
                             events: List[str]) -> CharacterState:
        """根据事件更新角色状态"""
        for event in events:
            if 'injury' in event.lower():
                character_state.health = max(0, character_state.health - 20)
                character_state.stress = min(100, character_state.stress + 15)
            elif 'rest' in event.lower():
                character_state.energy = min(100, character_state.energy + 30)
                character_state.stress = max(0, character_state.stress - 10)
            elif 'danger' in event.lower():
                character_state.stress = min(100, character_state.stress + 25)
        
        # 更新情绪状态
        if character_state.stress > 80:
            character_state.mood = 'panicked'
        elif character_state.stress > 50:
            character_state.mood = 'anxious'
        elif character_state.health < 50:
            character_state.mood = 'pained'
        else:
            character_state.mood = 'neutral'
        
        return character_state
    
    def has_knowledge(self, knowledge_id: str) -> bool:
        """检查角色是否拥有指定知识"""
        # 从配置文件读取知识状态
        try:
            config_dir = Path("e:\\项目（已开同步）\\Project\\config")
            knowledge_config_path = config_dir / "knowledge.json"
            
            if knowledge_config_path.exists():
                with open(knowledge_config_path, 'r', encoding='utf-8') as f:
                    knowledge_data = json.load(f)
                knowledge_base = knowledge_data.get('knowledge_base', {})
                
                if knowledge_id in knowledge_base:
                    return knowledge_base[knowledge_id].get('unlocked', False)
            
            # 后备方案：硬编码的基础知识
            basic_knowledge = ["basic_ship_layout", "emergency_protocols"]
            return knowledge_id in basic_knowledge
            
        except Exception as e:
            logger.warning(f"读取知识配置失败: {e}，使用默认配置")
            # 后备方案：硬编码的基础知识
            basic_knowledge = ["basic_ship_layout", "emergency_protocols"]
            return knowledge_id in basic_knowledge


class ScriptFrameworkConstrainer:
    """剧本框架约束器 - 管理剧情节点和分支逻辑"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.script_config = config.get('script', {})
        self.story_nodes = {}
        self.current_node_id = self.script_config.get('current_node_id', 'intro_awakening')
        self.branch_rules = self.script_config.get('branch_rules', {})
        
        # 加载剧情节点
        self._load_story_nodes()
        
        logger.info(f"剧本框架约束器初始化完成，当前节点: {self.current_node_id}")
    
    def _load_story_nodes(self):
        """加载剧情节点数据"""
        nodes_data = self.script_config.get('story_nodes', {})
        
        for node_id, node_data in nodes_data.items():
            try:
                story_node = StoryNode(
                    id=node_data.get('id', node_id),  # 使用node_id作为fallback
                    title=node_data['title'],
                    description=node_data['description'],
                    character_situation=node_data['character_situation'],
                    context_background=node_data['context_background'],
                    branches=node_data.get('branches', [])
                )
                self.story_nodes[node_id] = story_node
            except KeyError as e:
                logger.error(f"剧情节点 {node_id} 数据不完整，缺少字段: {e}")
            except Exception as e:
                logger.error(f"加载剧情节点 {node_id} 时出现错误: {e}")
        
        logger.info(f"已加载 {len(self.story_nodes)} 个剧情节点")
        if self.story_nodes:
            logger.info(f"可用节点: {list(self.story_nodes.keys())}")
        else:
            logger.warning("没有加载到任何剧情节点，请检查配置文件")
    
    def get_current_story_node(self, game_state: GameState) -> Optional[StoryNode]:
        """获取当前剧情节点"""
        node_id = game_state.current_story_node or self.current_node_id
        
        if node_id in self.story_nodes:
            return self.story_nodes[node_id]
        else:
            logger.warning(f"剧情节点 {node_id} 不存在，回退到默认节点")
            # 回退到第一个可用节点
            if self.story_nodes:
                return list(self.story_nodes.values())[0]
            return None
    
    def build_story_prompt(self, character_state: CharacterState, 
                          game_state: GameState) -> str:
        """构建剧情提示词"""
        current_node = self.get_current_story_node(game_state)
        
        if not current_node:
            return "\n当前剧情：暂无剧情信息可用\n"
        
        # 检查可用分支
        available_branches = self.get_available_branches(character_state, game_state)
        
        story_prompt = f"""

=== 当前剧情信息 ===
剧情节点：{current_node.title}

剧情描述：
{current_node.description}

角色处境：
{current_node.character_situation}

背景信息：
{current_node.context_background}
"""
        
        if available_branches:
            story_prompt += "\n可能的剧情发展方向：\n"
            for i, branch in enumerate(available_branches, 1):
                story_prompt += f"{i}. {branch.get('description', '未知选项')}\n"
        
        story_prompt += "\n=== 剧情信息结束 ===\n"
        
        return story_prompt
    
    def get_available_branches(self, character_state: CharacterState, 
                              game_state: GameState) -> List[Dict[str, Any]]:
        """获取当前可用的剧情分支"""
        current_node = self.get_current_story_node(game_state)
        
        if not current_node or not current_node.branches:
            return []
        
        available_branches = []
        
        for branch in current_node.branches:
            if self._check_branch_conditions(branch, character_state, game_state):
                available_branches.append(branch)
        
        return available_branches
    
    def _check_branch_conditions(self, branch: Dict[str, Any], 
                                character_state: CharacterState, 
                                game_state: GameState) -> bool:
        """检查分支条件是否满足"""
        conditions = branch.get('conditions', {})
        
        if not conditions:
            return True  # 无条件限制
        
        try:
            # 检查角色状态条件
            if 'character_state' in conditions:
                char_conditions = conditions['character_state']
                
                for attr, limits in char_conditions.items():
                    char_value = getattr(character_state, attr, None)
                    if char_value is None:
                        continue
                    
                    if 'min' in limits and char_value < limits['min']:
                        return False
                    if 'max' in limits and char_value > limits['max']:
                        return False
                    if 'equals' in limits and char_value != limits['equals']:
                        return False
            
            # 检查游戏状态条件
            if 'game_state' in conditions:
                game_conditions = conditions['game_state']
                
                for attr, limits in game_conditions.items():
                    game_value = getattr(game_state, attr, None)
                    if game_value is None:
                        continue
                    
                    if 'min' in limits and game_value < limits['min']:
                        return False
                    if 'max' in limits and game_value > limits['max']:
                        return False
                    if 'equals' in limits and game_value != limits['equals']:
                        return False
            
            # 检查知识条件（需要与KnowledgeGraph集成）
            if 'knowledge' in conditions:
                knowledge_conditions = conditions['knowledge']
                required_knowledge = knowledge_conditions.get('required', [])
                
                # 这里需要与KnowledgeGraph或CharacterController集成
                # 暂时返回True，后续完善
                pass
            
            # 检查事件条件
            if 'events' in conditions:
                event_conditions = conditions['events']
                
                if 'triggered' in event_conditions:
                    required_events = event_conditions['triggered']
                    if not all(event in game_state.events_triggered for event in required_events):
                        return False
                
                if 'not_triggered' in event_conditions:
                    forbidden_events = event_conditions['not_triggered']
                    if any(event in game_state.events_triggered for event in forbidden_events):
                        return False
            
            return True
            
        except Exception as e:
            logger.error(f"检查分支条件时出错: {e}")
            return False
    
    def advance_to_branch(self, branch_id: str, character_state: CharacterState, 
                         game_state: GameState) -> bool:
        """推进到指定分支"""
        current_node = self.get_current_story_node(game_state)
        
        if not current_node:
            logger.error("无法推进剧情：当前节点不存在")
            return False
        
        # 查找指定分支
        target_branch = None
        for branch in current_node.branches:
            if branch.get('id') == branch_id:
                target_branch = branch
                break
        
        if not target_branch:
            logger.error(f"分支 {branch_id} 不存在")
            return False
        
        # 检查分支条件
        if not self._check_branch_conditions(target_branch, character_state, game_state):
            logger.warning(f"分支 {branch_id} 条件不满足")
            return False
        
        # 推进到目标节点
        target_node_id = target_branch.get('target_node_id')
        if target_node_id and target_node_id in self.story_nodes:
            game_state.current_story_node = target_node_id
            logger.info(f"剧情推进到节点: {target_node_id}")
            return True
        else:
            logger.error(f"目标节点 {target_node_id} 不存在")
            return False
    
    def reset_story(self, game_state: GameState):
        """重置剧情到初始状态"""
        game_state.current_story_node = self.current_node_id
        logger.info(f"剧情已重置到初始节点: {self.current_node_id}")
    
    def get_story_progress(self, game_state: GameState) -> Dict[str, Any]:
        """获取剧情进度信息"""
        current_node = self.get_current_story_node(game_state)
        
        return {
            'current_node_id': game_state.current_story_node,
            'current_node_title': current_node.title if current_node else '未知',
            'total_nodes': len(self.story_nodes),
            'available_branches': len(self.get_available_branches(None, game_state))
        }


class KnowledgeGraph:
    """知识图谱类 - 信息边界管理"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.knowledge_base = config.get('knowledge_base', {})
        
        # 初始化知识图谱
        self.knowledge_nodes = {
            'basic_ship_layout': {
                'unlocked': True,
                'content': '飞船基本布局：桥梁、工程舱、生活区、货舱',
                'required_permission': 1
            },
            'emergency_protocols': {
                'unlocked': True,
                'content': '紧急情况处理协议和基本安全程序',
                'required_permission': 1
            },
            'technical_systems': {
                'unlocked': False,
                'content': '飞船技术系统详细信息和维修手册',
                'required_permission': 3
            },
            'mission_details': {
                'unlocked': False,
                'content': '任务详细信息和目的地数据',
                'required_permission': 5
            },
            'classified_logs': {
                'unlocked': False,
                'content': '机密日志和事故报告',
                'required_permission': 7
            }
        }
    
    def check_information_access(self, info_id: str, permission_level: int) -> bool:
        """检查信息访问权限"""
        if info_id not in self.knowledge_nodes:
            return False
        
        node = self.knowledge_nodes[info_id]
        return (node['unlocked'] and 
                permission_level >= node['required_permission'])
    
    def unlock_information(self, info_id: str, data_fragments: List[str]) -> bool:
        """解锁信息节点"""
        if info_id not in self.knowledge_nodes:
            return False
        
        # 检查是否有足够的数据碎片
        required_fragments = self._get_required_fragments(info_id)
        if all(fragment in data_fragments for fragment in required_fragments):
            self.knowledge_nodes[info_id]['unlocked'] = True
            logger.info(f"知识节点已解锁: {info_id}")
            return True
        
        return False
    
    def get_available_knowledge(self, permission_level: int) -> List[str]:
        """获取可用知识列表"""
        available = []
        for info_id, node in self.knowledge_nodes.items():
            if self.check_information_access(info_id, permission_level):
                available.append(node['content'])
        return available
    
    def _get_required_fragments(self, info_id: str) -> List[str]:
        """获取解锁信息所需的数据碎片"""
        fragment_requirements = {
            'technical_systems': ['engine_data', 'power_grid_info'],
            'mission_details': ['navigation_log', 'mission_briefing'],
            'classified_logs': ['captain_key', 'security_override']
        }
        return fragment_requirements.get(info_id, [])


class GameElementManager:
    """游戏要素管理器 - 处理物品、地点、出口等游戏要素"""
    
    def __init__(self):
        pass
    
    def get_location_info(self, game_state: GameState, location_name: str) -> Dict[str, Any]:
        """获取地点信息"""
        location = game_state.locations.get(location_name, {})
        if not location:
            return {"description": "未知地点", "exits": [], "items": [], "accessible": False, "exists": False}
        
        # 检查地点是否可访问
        accessible = location.get('accessible', True)
        if not accessible:
            return {
                "description": "该区域目前无法访问",
                "exits": [],
                "items": [],
                "accessible": False,
                "exists": True
            }
        
        result = location.copy()
        result['exists'] = True
        return result
    
    def get_available_exits(self, game_state: GameState, current_location: str) -> List[str]:
        """获取当前地点的可用出口"""
        location_info = self.get_location_info(game_state, current_location)
        if not location_info.get('accessible', False):
            return []
        
        exits = location_info.get('exits', [])
        # 过滤掉不可访问的地点
        accessible_exits = []
        for exit_location in exits:
            exit_info = game_state.locations.get(exit_location, {})
            if exit_info.get('accessible', True):
                accessible_exits.append(exit_location)
        
        return accessible_exits
    
    def get_location_items(self, game_state: GameState, location_name: str) -> List[Dict[str, Any]]:
        """获取地点中的物品"""
        location_info = self.get_location_info(game_state, location_name)
        if not location_info.get('accessible', False):
            return []
        
        item_ids = location_info.get('items', [])
        items = []
        
        for item_id in item_ids:
            item_info = game_state.global_items.get(item_id, {})
            if item_info and item_info.get('obtainable', True):
                items.append({
                    'id': item_id,
                    'name': item_info.get('name', item_id),
                    'description': item_info.get('description', '无描述'),
                    'type': item_info.get('type', 'unknown')
                })
        
        return items
    
    def can_take_item(self, game_state: GameState, character_state: CharacterState, 
                     item_id: str) -> Tuple[bool, str]:
        """检查是否可以拾取物品"""
        item_info = game_state.global_items.get(item_id)
        if not item_info:
            return False, "物品不存在"
        
        # 检查物品是否可获取
        if not item_info.get('obtainable', True):
            return False, "该物品无法获取"
        
        # 检查物品是否在当前地点
        item_location = item_info.get('location')
        if item_location != character_state.location:
            return False, "物品不在当前位置"
        
        # 检查物品栏是否已满（假设最多10个物品）
        if len(character_state.inventory) >= 10:
            return False, "物品栏已满"
        
        # 检查是否已经拥有该物品
        for inv_item in character_state.inventory:
            if inv_item.get('id') == item_id:
                return False, "已经拥有该物品"
        
        return True, "可以拾取"
    
    def take_item(self, game_state: GameState, character_state: CharacterState, 
                 item_id: str) -> Tuple[bool, str]:
        """拾取物品"""
        can_take, reason = self.can_take_item(game_state, character_state, item_id)
        if not can_take:
            return False, reason
        
        item_info = game_state.global_items[item_id]
        
        # 添加到物品栏
        inventory_item = {
            'id': item_id,
            'name': item_info['name'],
            'description': item_info['description'],
            'type': item_info['type'],
            'quantity': 1
        }
        character_state.inventory.append(inventory_item)
        
        # 从地点移除物品
        location_name = item_info['location']
        if location_name in game_state.locations:
            location_items = game_state.locations[location_name].get('items', [])
            if item_id in location_items:
                location_items.remove(item_id)
        
        return True, f"成功拾取了{item_info['name']}"
    
    def use_item(self, character_state: CharacterState, item_id: str) -> Tuple[bool, str, Dict[str, Any]]:
        """使用物品"""
        # 查找物品
        item_index = -1
        for i, inv_item in enumerate(character_state.inventory):
            if inv_item.get('id') == item_id:
                item_index = i
                break
        
        if item_index == -1:
            return False, "物品栏中没有该物品", {}
        
        item = character_state.inventory[item_index]
        item_type = item.get('type', 'unknown')
        effects = {}
        
        # 根据物品类型产生不同效果
        if item_type == 'consumable':
            if item_id == 'medical_kit':
                health_restore = min(30, 100 - character_state.health)
                character_state.health += health_restore
                effects['health_change'] = health_restore
                # 消耗品使用后移除
                character_state.inventory.pop(item_index)
                return True, f"使用了{item['name']}，恢复了{health_restore}点健康值", effects
            
            elif item_id == 'power_cell':
                energy_restore = min(20, 100 - character_state.energy)
                character_state.energy += energy_restore
                effects['energy_change'] = energy_restore
                character_state.inventory.pop(item_index)
                return True, f"使用了{item['name']}，恢复了{energy_restore}点能量", effects
        
        elif item_type == 'document':
            # 文档类物品提供信息，不消耗
            return True, f"阅读了{item['name']}：{item['description']}", effects
        
        elif item_type == 'tool':
            # 工具类物品可以重复使用
            return True, f"使用了{item['name']}，这是一个有用的工具", effects
        
        return False, "无法使用该物品", {}
    
    def move_to_location(self, game_state: GameState, character_state: CharacterState, 
                        target_location: str) -> Tuple[bool, str]:
        """移动到指定地点"""
        # 检查目标地点是否存在
        if target_location not in game_state.locations:
            return False, "目标地点不存在"
        
        # 检查目标地点是否可访问
        target_info = game_state.locations[target_location]
        if not target_info.get('accessible', True):
            return False, "目标地点无法访问"
        
        # 检查是否可以从当前地点到达目标地点
        current_exits = self.get_available_exits(game_state, character_state.location)
        if target_location not in current_exits:
            return False, f"无法从{character_state.location}直接到达{target_location}"
        
        # 执行移动
        old_location = character_state.location
        character_state.location = target_location
        game_state.current_location = target_location
        
        return True, f"从{old_location}移动到了{target_location}"


class GameStateManager:
    """游戏状态管理类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.events_config = config.get('events', {})
        self.game_element_manager = GameElementManager()
    
    def update_permission(self, game_state: GameState, 
                         new_fragments: List[str]) -> GameState:
        """根据数据碎片更新权限等级"""
        # 添加新碎片
        for fragment in new_fragments:
            if fragment not in game_state.data_fragments:
                game_state.data_fragments.append(fragment)
        
        # 根据碎片数量计算权限等级
        fragment_count = len(game_state.data_fragments)
        if fragment_count >= 10:
            game_state.permission_level = 7
        elif fragment_count >= 7:
            game_state.permission_level = 5
        elif fragment_count >= 4:
            game_state.permission_level = 3
        elif fragment_count >= 2:
            game_state.permission_level = 2
        
        return game_state
    
    def trigger_events(self, game_state: GameState, 
                      character_state: CharacterState) -> List[str]:
        """触发游戏事件"""
        triggered_events = []
        
        # 基于时间的事件
        if game_state.time_elapsed > 60 and 'power_failure' not in game_state.events_triggered:
            triggered_events.append('power_failure')
            game_state.events_triggered.append('power_failure')
        
        # 基于健康状态的事件
        if character_state.health < 30 and 'medical_emergency' not in game_state.events_triggered:
            triggered_events.append('medical_emergency')
            game_state.events_triggered.append('medical_emergency')
        
        # 基于权限等级的事件
        if game_state.permission_level >= 5 and 'core_access' not in game_state.events_triggered:
            triggered_events.append('core_access')
            game_state.events_triggered.append('core_access')
        
        return triggered_events


class LLMCore:
    """LLM驱动核心主控制器"""
    
    def __init__(self, config_path: str = None):
        # 加载配置 - 使用新的ConfigManager
        if config_path and config_path != 'config.json':
            # 如果指定了非默认路径，仍使用旧方式加载
            self.config = self._load_config(config_path)
        else:
            # 使用新的配置管理器
            self.config = get_config()
        
        # 初始化各个组件
        self.model_manager = ModelManager(self.config.get('model', {}))
        self.memory_system = MemorySystem(self.config.get('memory', {}), self.model_manager)
        self.character_controller = CharacterController(self.config.get('character', {}))
        self.knowledge_graph = KnowledgeGraph(self.config.get('knowledge', {}))
        self.game_state_manager = GameStateManager(self.config.get('game', {}))
        self.script_constrainer = ScriptFrameworkConstrainer(self.config)
        
        # 初始化游戏状态
        self.character_state = CharacterState(
            name=self.character_controller.character_info['name'],
            location="bridge"
        )
        self.game_state = GameState()
        
        logger.info("LLM驱动核心初始化完成 - 使用新配置系统")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            logger.warning(f"配置文件未找到: {config_path}，使用默认配置")
            return self._get_default_config()
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}，使用默认配置")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'model': {
                'deepseek_api_key': '',
                'api_base': 'https://api.siliconflow.cn/v1',
                'model_name': 'deepseek-ai/DeepSeek-R1-0528-Qwen3-8B',
                'bge_model_path': 'BAAI/bge-m3'
            },
            'memory': {
                'memory_db_path': './memory_db',
                'collection_name': 'game_memories'
            },
            'character': {},
            'knowledge': {},
            'game': {}
        }
    
    # 五阶段架构处理方法
    async def _cognition_stage(self, user_input: str) -> CognitionResult:
        """认知阶段：分析当前游戏场景状态、整合角色信息、评估交互历史"""
        try:
            logger.info("开始认知阶段处理")
            
            # 分析当前游戏场景状态
            current_node = self.script_constrainer.get_current_story_node(self.game_state)
            scene_status = {
                'current_node_id': self.game_state.current_story_node,
                'current_location': self.game_state.current_location,
                'time_elapsed': self.game_state.time_elapsed,
                'events_triggered': self.game_state.events_triggered.copy(),
                'permission_level': self.game_state.permission_level,
                'node_title': current_node.title if current_node else "未知",
                'node_description': current_node.description if current_node else "无描述"
            }
            
            # 整合已知角色信息
            character_profile = {
                'name': self.character_state.name,
                'health': self.character_state.health,
                'stress': self.character_state.stress,
                'energy': self.character_state.energy,
                'mood': self.character_state.mood,
                'location': self.character_state.location,
                'permissions': self.character_state.permissions.copy() if self.character_state.permissions else []
            }
            
            # 评估玩家交互历史
            recent_memories = self.memory_system.retrieve_memories(user_input, limit=5)
            interaction_history = [{
                'content': mem['content'],
                'timestamp': mem['metadata'].get('timestamp', 0),
                'type': mem['metadata'].get('type', 'unknown')
            } for mem in recent_memories]
            
            # 计算综合置信度
            confidence_score = await self._calculate_cognition_confidence(
                scene_status, character_profile, interaction_history, user_input
            )
            
            result = CognitionResult(
                scene_status=scene_status,
                character_profile=character_profile,
                interaction_history=interaction_history,
                confidence_score=confidence_score
            )
            
            logger.info(f"认知阶段完成，置信度: {result.confidence_score}")
            return result
            
        except Exception as e:
            logger.error(f"认知阶段处理错误: {e}")
            return CognitionResult(
                scene_status={},
                character_profile={},
                interaction_history=[],
                confidence_score=0.3
            )
    
    async def _calculate_cognition_confidence(self, scene_status: Dict[str, Any], 
                                            character_profile: Dict[str, Any],
                                            interaction_history: List[Dict[str, Any]], 
                                            user_input: str) -> float:
        """计算认知阶段的综合置信度"""
        try:
            # 构建评估文本
            scene_text = f"当前场景：{scene_status.get('node_title', '未知')} - {scene_status.get('node_description', '无描述')}，位置：{scene_status.get('current_location', '未知')}，权限等级：{scene_status.get('permission_level', 1)}"
            
            character_text = f"角色状态：{character_profile.get('name', '未知')}，健康：{character_profile.get('health', 0)}%，压力：{character_profile.get('stress', 0)}%，精力：{character_profile.get('energy', 0)}%，情绪：{character_profile.get('mood', '未知')}"
            
            history_text = "交互历史：" + "；".join([f"{item.get('type', '未知')}：{item.get('content', '')[:50]}" for item in interaction_history[-3:]]) if interaction_history else "无历史记录"
            
            # 获取嵌入向量
            texts = [scene_text, character_text, history_text, user_input]
            embeddings = self.model_manager.get_embeddings(texts)
            
            if not embeddings or len(embeddings) != 4:
                logger.warning("无法获取嵌入向量，使用默认置信度")
                return 0.7
            
            # 计算各部分的内部一致性（向量相似度）
            import numpy as np
            
            def cosine_similarity(a, b):
                """计算余弦相似度"""
                a = np.array(a)
                b = np.array(b)
                return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
            
            # 场景与用户输入的相关性
            scene_relevance = cosine_similarity(embeddings[0], embeddings[3])
            
            # 角色状态与用户输入的相关性
            character_relevance = cosine_similarity(embeddings[1], embeddings[3])
            
            # 历史交互与用户输入的相关性
            history_relevance = cosine_similarity(embeddings[2], embeddings[3]) if interaction_history else 0.5
            
            # 场景与角色状态的一致性
            scene_character_consistency = cosine_similarity(embeddings[0], embeddings[1])
            
            # 综合置信度计算（加权平均）
            confidence_score = (
                scene_relevance * 0.3 +           # 场景相关性权重30%
                character_relevance * 0.25 +      # 角色相关性权重25%
                history_relevance * 0.2 +         # 历史相关性权重20%
                scene_character_consistency * 0.25 # 一致性权重25%
            )
            
            # 确保置信度在合理范围内
            confidence_score = max(0.1, min(1.0, confidence_score))
            
            # 根据数据完整性调整置信度
            completeness_factor = 1.0
            if not scene_status.get('node_title'):
                completeness_factor -= 0.1
            if not interaction_history:
                completeness_factor -= 0.1
            if character_profile.get('health', 0) <= 0:
                completeness_factor -= 0.1
            
            confidence_score *= max(0.5, completeness_factor)
            
            logger.info(f"认知置信度计算：场景相关性={scene_relevance:.3f}, 角色相关性={character_relevance:.3f}, 历史相关性={history_relevance:.3f}, 一致性={scene_character_consistency:.3f}, 最终置信度={confidence_score:.3f}")
            
            return confidence_score
            
        except Exception as e:
            logger.error(f"计算认知置信度时出错: {e}")
            return 0.6  # 出错时返回中等置信度
    
    async def _memory_stage(self, cognition_result: CognitionResult, user_input: str) -> MemoryResult:
        """记忆阶段：检索长期记忆、更新短期对话缓存、关联知识图谱节点"""
        try:
            logger.info("开始记忆阶段处理")
            
            # 检索长期记忆
            long_term_memories = self.memory_system.retrieve_memories(user_input, limit=8)
            long_term_memory = [{
                'content': mem['content'],
                'metadata': mem['metadata'],
                'relevance_score': mem.get('distance', 0.5)
            } for mem in long_term_memories]
            
            # 更新短期对话缓存（从交互历史中提取最近的对话）
            dialogue_cache = cognition_result.interaction_history[-3:] if cognition_result.interaction_history else []
            
            # 关联知识图谱节点
            available_knowledge = self.knowledge_graph.get_available_knowledge(
                cognition_result.scene_status.get('permission_level', 1)
            )
            knowledge_graph_nodes = available_knowledge[:10]  # 限制节点数量
            
            # 计算记忆相关性评分
            memory_relevance_scores = {}
            for i, mem in enumerate(long_term_memory):
                memory_relevance_scores[f"memory_{i}"] = 1.0 - mem['relevance_score']
            
            result = MemoryResult(
                long_term_memory=long_term_memory,
                dialogue_cache=dialogue_cache,
                knowledge_graph_nodes=knowledge_graph_nodes,
                memory_confidence=0.8,
                retrieval_metadata={'memory_relevance_scores': memory_relevance_scores}
            )
            
            logger.info(f"记忆阶段完成，检索到 {len(long_term_memory)} 条长期记忆")
            return result
            
        except Exception as e:
            logger.error(f"记忆阶段处理错误: {e}")
            return MemoryResult(
                long_term_memory=[],
                dialogue_cache=[],
                knowledge_graph_nodes=[],
                memory_confidence=0.0
            )
    
    async def _understanding_stage(self, cognition_result: CognitionResult, 
                                 memory_result: MemoryResult, user_input: str) -> UnderstandingResult:
        """理解阶段：解析对话意图、评估建议执行效果、识别情感倾向变化"""
        try:
            logger.info("开始理解阶段处理")
            
            # 解析上一轮对话意图（增强版 - 支持游戏动作识别）
            last_dialogue_intent = {
                'user_input': user_input,
                'input_length': len(user_input),
                'contains_question': '?' in user_input or '？' in user_input,
                'contains_command': any(word in user_input.lower() for word in ['请', '帮', '执行', '做', '开始']),
                'emotional_indicators': [word for word in ['高兴', '难过', '愤怒', '害怕', '惊讶'] if word in user_input],
                # 新增游戏动作识别
                'game_actions': self._parse_game_actions(user_input),
                'mentioned_items': self._extract_mentioned_items(user_input, cognition_result),
                'mentioned_locations': self._extract_mentioned_locations(user_input, cognition_result),
                'action_type': self._classify_action_type(user_input)
            }
            
            # 添加调试信息
            logger.info(f"🔍 自然语言解析结果:")
            logger.info(f"  - 动作类型: {last_dialogue_intent['action_type']}")
            logger.info(f"  - 识别到的游戏动作: {len(last_dialogue_intent['game_actions'])}个")
            for i, action in enumerate(last_dialogue_intent['game_actions']):
                logger.info(f"    动作{i+1}: {action.get('type', 'unknown')} - {action.get('target', 'N/A')}")
            logger.info(f"  - 提到的物品: {last_dialogue_intent['mentioned_items']}")
            logger.info(f"  - 提到的地点: {last_dialogue_intent['mentioned_locations']}")

            last_dialogue_intent.update({
                'debug_info': {
                    'parsing_successful': len(last_dialogue_intent['game_actions']) > 0,
                    'has_game_elements': len(last_dialogue_intent['mentioned_items']) > 0 or len(last_dialogue_intent['mentioned_locations']) > 0,
                    'input_complexity': len(user_input.split())
                }
            })
            
            # 评估建议执行效果（基于历史交互）
            suggestion_feedback = {
                'previous_suggestions_count': len([mem for mem in memory_result.dialogue_cache 
                                                 if mem and isinstance(mem, dict) and '建议' in mem.get('content', '')]),
                'user_engagement_level': min(len(user_input) / 50.0, 1.0),  # 基于输入长度评估参与度
                'context_continuity': len(memory_result.dialogue_cache) > 0
            }
            
            # 识别情感倾向变化
            character_profile = cognition_result.character_profile or {}
            current_mood = character_profile.get('mood', 'neutral')
            sentiment_shift = {
                'current_mood': current_mood,
                'mood_stability': 0.8,  # 默认情绪稳定性
                'stress_level': character_profile.get('stress', 0.0) / 100.0,
                'energy_level': character_profile.get('energy', 100.0) / 100.0
            }
            
            # 构建上下文理解
            scene_status = cognition_result.scene_status or {}
            context_understanding = f"用户在{scene_status.get('current_location', '未知位置')}" + \
                                  f"进行交互，当前角色状态为{current_mood}，" + \
                                  f"权限等级{scene_status.get('permission_level', 1)}"
            
            result = UnderstandingResult(
                last_dialogue_intent=last_dialogue_intent,
                suggestion_feedback=suggestion_feedback,
                sentiment_shift=sentiment_shift,
                understanding_confidence=0.8,
                analysis_metadata={'context_understanding': context_understanding}
            )
            
            logger.info("理解阶段完成")
            return result
            
        except Exception as e:
            logger.error(f"理解阶段处理错误: {e}")
            return UnderstandingResult(
                last_dialogue_intent={},
                suggestion_feedback={},
                sentiment_shift={},
                understanding_confidence=0.0,
                analysis_metadata={'context_understanding': '理解阶段出现错误'}
            )
    
    def _parse_game_actions(self, user_input: str) -> List[Dict[str, Any]]:
        """解析用户输入中的游戏动作"""
        actions = []
        user_lower = user_input.lower()
        
        # 添加调试信息
        logger.info(f"🔍 解析游戏动作 - 输入: '{user_input}' -> 小写: '{user_lower}'")
        
        # 移动动作
        move_keywords = ['去', '到', '走', '移动', '前往', '进入', '离开']
        for keyword in move_keywords:
            if keyword in user_lower:
                actions.append({
                    'type': 'move',
                    'keyword': keyword,
                    'confidence': 0.8
                })
                logger.info(f"  ✓ 识别到移动动作: {keyword}")
                break
        
        # 拾取动作
        take_keywords = ['拿', '取', '拾取', '获得', '收集', '捡']
        for keyword in take_keywords:
            if keyword in user_lower:
                actions.append({
                    'type': 'take',
                    'keyword': keyword,
                    'confidence': 0.8
                })
                logger.info(f"  ✓ 识别到拾取动作: {keyword}")
                break
        
        # 使用动作
        use_keywords = ['用', '使用', '打开', '启动', '激活', '操作']
        for keyword in use_keywords:
            if keyword in user_lower:
                actions.append({
                    'type': 'use',
                    'keyword': keyword,
                    'confidence': 0.8
                })
                logger.info(f"  ✓ 识别到使用动作: {keyword}")
                break
        
        # 查看动作
        look_keywords = ['看', '查看', '检查', '观察', '搜索', '寻找']
        for keyword in look_keywords:
            if keyword in user_lower:
                actions.append({
                    'type': 'look',
                    'keyword': keyword,
                    'confidence': 0.7
                })
                logger.info(f"  ✓ 识别到查看动作: {keyword}")
                break
        
        # 特殊处理：如果包含"周围"相关词汇但没有明确动作，默认为查看动作
        environment_keywords = ['周围', '四周', '环境', '附近', '这里', '当前位置']
        if not actions:  # 如果还没有识别到任何动作
            for env_keyword in environment_keywords:
                if env_keyword in user_lower:
                    actions.append({
                        'type': 'look',
                        'keyword': env_keyword,
                        'confidence': 0.6,
                        'auto_detected': True  # 标记为自动检测
                    })
                    logger.info(f"  ✓ 自动识别为查看动作（环境相关）: {env_keyword}")
                    break
        
        # 对话动作
        talk_keywords = ['说', '告诉', '询问', '问', '交谈', '对话']
        for keyword in talk_keywords:
            if keyword in user_lower:
                actions.append({
                    'type': 'talk',
                    'keyword': keyword,
                    'confidence': 0.6
                })
                logger.info(f"  ✓ 识别到对话动作: {keyword}")
                break
        
        logger.info(f"  📊 解析结果: 共识别到 {len(actions)} 个动作")
        return actions
    
    def _extract_mentioned_items(self, user_input: str, cognition_result: CognitionResult) -> List[str]:
        """提取用户输入中提到的物品"""
        mentioned_items = []
        user_lower = user_input.lower()
        
        # 检查全局物品池中的物品
        global_items = self.game_state.global_items or {}
        for item_id, item_info in global_items.items():
            item_name = item_info.get('name', '').lower()
            if item_name and item_name in user_lower:
                mentioned_items.append(item_id)
            
            # 也检查物品ID
            if item_id.lower() in user_lower:
                mentioned_items.append(item_id)
        
        # 检查物品栏中的物品
        for inv_item in self.character_state.inventory:
            item_name = inv_item.get('name', '').lower()
            item_id = inv_item.get('id', '')
            if item_name and item_name in user_lower:
                if item_id not in mentioned_items:
                    mentioned_items.append(item_id)
        
        return mentioned_items
    
    def _extract_mentioned_locations(self, user_input: str, cognition_result: CognitionResult) -> List[str]:
        """提取用户输入中提到的地点"""
        mentioned_locations = []
        user_lower = user_input.lower()
        
        # 检查游戏中的地点
        locations = self.game_state.locations or {}
        for location_id, location_info in locations.items():
            # 检查地点ID
            if location_id.lower() in user_lower:
                mentioned_locations.append(location_id)
            
            # 检查地点描述中的关键词
            description = location_info.get('description', '').lower()
            if description:
                # 提取描述中的关键词进行匹配
                location_keywords = {
                    'bridge': ['指挥', '驾驶', '控制', '舰桥'],
                    'engineering': ['工程', '引擎', '维修', '机械'],
                    'living_quarters': ['生活', '休息', '宿舍', '房间'],
                    'cargo_bay': ['货物', '仓库', '存储', '装载']
                }
                
                keywords = location_keywords.get(location_id, [])
                for keyword in keywords:
                    if keyword in user_lower:
                        if location_id not in mentioned_locations:
                            mentioned_locations.append(location_id)
                        break
        
        return mentioned_locations
    
    def _classify_action_type(self, user_input: str) -> str:
        """分类用户输入的动作类型"""
        user_lower = user_input.lower()
        
        # 游戏动作优先级分类
        if any(word in user_lower for word in ['去', '到', '走', '移动', '前往']):
            return 'movement'
        elif any(word in user_lower for word in ['拿', '取', '拾取', '获得']):
            return 'item_interaction'
        elif any(word in user_lower for word in ['用', '使用', '打开', '启动']):
            return 'item_usage'
        elif any(word in user_lower for word in ['看', '查看', '检查', '观察']):
            return 'exploration'
        elif any(word in user_lower for word in ['说', '告诉', '询问', '问']):
            return 'dialogue'
        elif any(word in user_lower for word in ['帮助', '指令', '命令', '怎么']):
            return 'help_request'
        else:
            return 'general_dialogue'
    
    def _determine_game_actions(self, understanding_result: UnderstandingResult) -> List[Dict[str, Any]]:
        """根据理解结果确定要执行的游戏动作"""
        determined_actions = []
        
        # 获取解析出的游戏动作 - 修复数据获取路径
        parsed_actions = understanding_result.last_dialogue_intent.get('game_actions', [])
        mentioned_items = understanding_result.last_dialogue_intent.get('mentioned_items', [])
        mentioned_locations = understanding_result.last_dialogue_intent.get('mentioned_locations', [])
        action_type = understanding_result.last_dialogue_intent.get('action_type', 'general_dialogue')
        
        # 根据动作类型和提到的要素确定具体动作
        for action in parsed_actions:
            action_detail = {
                'type': action['type'],
                'confidence': action['confidence'],
                'parameters': {}
            }
            
            # 移动动作
            if action['type'] == 'move' and mentioned_locations:
                action_detail['parameters']['target_location'] = mentioned_locations[0]
                action_detail['executable'] = True
            
            # 拾取动作
            elif action['type'] == 'take' and mentioned_items:
                action_detail['parameters']['item_id'] = mentioned_items[0]
                action_detail['executable'] = True
            
            # 使用动作
            elif action['type'] == 'use' and mentioned_items:
                action_detail['parameters']['item_id'] = mentioned_items[0]
                action_detail['executable'] = True
            
            # 查看动作
            elif action['type'] == 'look':
                if mentioned_locations:
                    action_detail['parameters']['target'] = mentioned_locations[0]
                    action_detail['parameters']['target_type'] = 'location'
                elif mentioned_items:
                    action_detail['parameters']['target'] = mentioned_items[0]
                    action_detail['parameters']['target_type'] = 'item'
                else:
                    action_detail['parameters']['target'] = 'current_location'
                    action_detail['parameters']['target_type'] = 'location'
                action_detail['executable'] = True
            
            # 对话动作
            elif action['type'] == 'talk':
                action_detail['parameters']['dialogue_type'] = 'general'
                action_detail['executable'] = True
            
            else:
                action_detail['executable'] = False
            
            determined_actions.append(action_detail)
        
        # 如果没有明确的游戏动作，根据动作类型添加默认动作
        if not determined_actions:
            if action_type == 'movement' and mentioned_locations:
                determined_actions.append({
                    'type': 'move',
                    'confidence': 0.6,
                    'parameters': {'target_location': mentioned_locations[0]},
                    'executable': True
                })
            elif action_type == 'item_interaction' and mentioned_items:
                determined_actions.append({
                    'type': 'take',
                    'confidence': 0.6,
                    'parameters': {'item_id': mentioned_items[0]},
                    'executable': True
                })
            elif action_type == 'exploration':
                determined_actions.append({
                    'type': 'look',
                    'confidence': 0.5,
                    'parameters': {'target': 'current_location', 'target_type': 'location'},
                    'executable': True
                })
        
        return determined_actions
    
    async def _execute_game_action(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """执行具体的游戏动作"""
        # 确保action不为None
        if action is None:
            return {
                'type': 'unknown',
                'success': False,
                'description': '动作参数为空',
                'error': 'null_action'
            }
        
        action_type = action.get('type', 'unknown')
        parameters = action.get('parameters', {})
        
        # 确保parameters不为None
        if parameters is None:
            parameters = {}
        
        # 检查必要的组件是否存在
        if not hasattr(self, 'game_state_manager') or self.game_state_manager is None:
            logger.error("game_state_manager未初始化")
            return {
                'type': action_type,
                'success': False,
                'description': '游戏状态管理器未初始化',
                'error': 'manager_not_initialized'
            }
        
        if not hasattr(self.game_state_manager, 'game_element_manager') or self.game_state_manager.game_element_manager is None:
            logger.error("game_element_manager未初始化")
            return {
                'type': action_type,
                'success': False,
                'description': '游戏要素管理器未初始化',
                'error': 'element_manager_not_initialized'
            }
        
        try:
            if action_type == 'move':
                target_location = parameters.get('target_location')
                success, message = self.game_state_manager.game_element_manager.move_to_location(
                    self.game_state, self.character_state, target_location
                )
                return {
                    'type': 'move',
                    'success': success,
                    'description': message,
                    'target': target_location
                }
            
            elif action_type == 'take':
                item_id = parameters.get('item_id')
                success, message = self.game_state_manager.game_element_manager.take_item(
                    self.game_state, self.character_state, item_id
                )
                return {
                    'type': 'take',
                    'success': success,
                    'description': message,
                    'item': item_id
                }
            
            elif action_type == 'use':
                item_id = parameters.get('item_id')
                success, message, effects = self.game_state_manager.game_element_manager.use_item(
                    self.character_state, item_id
                )
                # 应用物品使用效果
                if success and effects:
                    for effect_type, effect_value in effects.items():
                        if effect_type == 'health':
                            self.character_state.health = min(100.0, self.character_state.health + effect_value)
                        elif effect_type == 'stress':
                            self.character_state.stress = max(0.0, self.character_state.stress + effect_value)
                        elif effect_type == 'energy':
                            self.character_state.energy = min(100.0, self.character_state.energy + effect_value)
                
                return {
                    'type': 'use',
                    'success': success,
                    'description': message,
                    'item': item_id,
                    'effects': effects if success else {}
                }
            
            elif action_type == 'look':
                target = parameters.get('target')
                target_type = parameters.get('target_type', 'location')
                
                if target_type == 'location':
                    if target == 'current_location':
                        target = self.character_state.location
                    
                    try:
                        location_info = self.game_state_manager.game_element_manager.get_location_info(
                            self.game_state, target
                        )
                        
                        if location_info is None:
                            logger.error(f"get_location_info返回None，target: {target}")
                            return {
                                'type': 'look',
                                'success': False,
                                'description': f'无法获取地点信息：{target}',
                                'target': target
                            }
                    except Exception as e:
                        logger.error(f"调用get_location_info时出错: {e}")
                        return {
                            'type': 'look',
                            'success': False,
                            'description': f'获取地点信息时发生错误：{str(e)}',
                            'target': target
                        }
                    
                    if location_info.get('exists', False):
                        location_name = location_info.get('name', target)
                        description = f"你查看了{location_name}。{location_info.get('description', '没有特别的描述。')}"
                        if location_info.get('exits'):
                            description += f" 可用出口：{', '.join(location_info['exits'])}"
                        if location_info.get('items'):
                            item_names = []
                            for item in location_info['items']:
                                if item and isinstance(item, dict):
                                    item_name = item.get('name', item.get('id', '未知物品'))
                                    item_names.append(item_name)
                                elif item:
                                    item_names.append(str(item))
                            if item_names:
                                description += f" 这里有：{', '.join(item_names)}"
                    else:
                        description = f"你无法查看{target}，该地点不存在或无法访问。"
                    
                    return {
                        'type': 'look',
                        'success': location_info['exists'],
                        'description': description,
                        'target': target
                    }
                
                elif target_type == 'item':
                    # 查看物品详情
                    item_info = self.game_state.global_items.get(target, {})
                    if item_info:
                        description = f"你仔细查看了{item_info.get('name', target)}。{item_info.get('description', '没有特别的描述。')}"
                    else:
                        description = f"你无法找到{target}这个物品。"
                    
                    return {
                        'type': 'look',
                        'success': bool(item_info),
                        'description': description,
                        'target': target
                    }
            
            elif action_type == 'talk':
                # 对话动作通常不需要特殊处理，直接返回成功
                return {
                    'type': 'talk',
                    'success': True,
                    'description': '你开始了对话。',
                    'dialogue_type': parameters.get('dialogue_type', 'general')
                }
            
            else:
                return {
                    'type': action_type,
                    'success': False,
                    'description': f'未知的动作类型：{action_type}',
                    'error': 'unknown_action_type'
                }
        
        except Exception as e:
            logger.error(f"执行游戏动作时出错: {e}")
            return {
                'type': action_type,
                'success': False,
                'description': f'执行{action_type}动作时发生错误。',
                'error': str(e)
            }
    
    async def _decision_stage(self, cognition_result: CognitionResult, 
                            memory_result: MemoryResult, 
                            understanding_result: UnderstandingResult) -> DecisionResult:
        """决策阶段：生成多模态响应选项、计算行为效用评分、选择最优对话策略"""
        try:
            logger.info("开始决策阶段处理")
            
            # 检查是否有游戏动作需要决策
            game_actions = understanding_result.last_dialogue_intent.get('game_actions', [])
            logger.info(f"🎯 决策阶段分析:")
            logger.info(f"  - 需要决策的游戏动作: {len(game_actions)}个")
            
            if game_actions:
                for i, action in enumerate(game_actions):
                    logger.info(f"    动作{i+1}: {action.get('type', 'unknown')} -> {action.get('target', 'N/A')}")
                    logger.info(f"      置信度: {action.get('confidence', 0.0):.2f}")
            else:
                logger.info("  - 未识别到具体游戏动作，将进行对话响应")
            
            # 生成多模态响应选项
            available_branches = self.script_constrainer.get_available_branches(
                self.character_state, self.game_state
            )
            
            response_options = []
            
            # 选项1：基于剧情分支的响应
            if available_branches:
                response_options.append({
                    'id': 'story_branch',
                    'type': 'story_driven',
                    'description': '基于当前剧情分支的响应',
                    'branches': available_branches[:3]  # 限制分支数量
                })
            
            # 选项2：基于角色状态的响应
            response_options.append({
                'id': 'character_driven',
                'type': 'character_state',
                'description': '基于角色当前状态的响应',
                'character_focus': True
            })
            
            # 选项3：基于知识图谱的响应
            if memory_result.knowledge_graph_nodes:
                response_options.append({
                    'id': 'knowledge_driven',
                    'type': 'knowledge_based',
                    'description': '基于可用知识的响应',
                    'knowledge_nodes': memory_result.knowledge_graph_nodes[:5]
                })
            
            # 计算行为效用评分
            action_utility_score = {}
            for option in response_options:
                base_score = 0.5
                
                # 根据角色状态调整评分
                if option['type'] == 'character_state':
                    base_score += 0.2 if cognition_result.character_profile.get('health', 100) < 50 else 0.1
                
                # 根据剧情进展调整评分
                if option['type'] == 'story_driven' and available_branches:
                    base_score += 0.3
                
                # 根据知识可用性调整评分
                if option['type'] == 'knowledge_based' and memory_result.knowledge_graph_nodes:
                    base_score += 0.2
                
                action_utility_score[option['id']] = min(base_score, 1.0)
            
            # 确定游戏动作
            game_actions = self._determine_game_actions(understanding_result)
            logger.info(f"决策阶段 - 确定的游戏动作: {len(game_actions)}个")
            for i, action in enumerate(game_actions):
                logger.info(f"  动作{i+1}: 类型={action['type']}, 可执行={action.get('executable', False)}, 置信度={action.get('confidence', 0)}")
            
            # 选择最优对话策略
            if not action_utility_score:
                dialogue_strategy = "default"
                selected_option_id = "character_driven"
            else:
                selected_option_id = max(action_utility_score.keys(), key=lambda k: action_utility_score[k])
                
                if selected_option_id == 'story_branch':
                    dialogue_strategy = "story_progression"
                elif selected_option_id == 'character_driven':
                    dialogue_strategy = "character_interaction"
                elif selected_option_id == 'knowledge_driven':
                    dialogue_strategy = "information_sharing"
                else:
                    dialogue_strategy = "adaptive"
            
            result = DecisionResult(
                response_options=response_options,
                action_utility_score=action_utility_score,
                dialogue_strategy=dialogue_strategy,
                selected_option_id=selected_option_id,
                strategy_metadata={
                    'game_actions': game_actions,
                    'action_count': len(game_actions) if game_actions else 0
                }
            )
            
            logger.info(f"决策阶段完成，选择策略: {dialogue_strategy}")
            return result
            
        except Exception as e:
            logger.error(f"决策阶段处理错误: {e}")
            return DecisionResult(
                response_options=[],
                action_utility_score={},
                dialogue_strategy="error_fallback",
                selected_option_id="default"
            )
    
    async def _execution_stage(self, cognition_result: CognitionResult,
                             memory_result: MemoryResult,
                             understanding_result: UnderstandingResult,
                             decision_result: DecisionResult,
                             user_input: str) -> ExecutionResult:
        """执行阶段：先执行游戏动作操作，再通过LLM加工处理结果，输出自然语言响应"""
        try:
            start_time = time.time()
            logger.info(f"开始执行阶段处理，策略: {decision_result.dialogue_strategy}")
            
            # 第一步：执行游戏动作操作
            game_actions = decision_result.strategy_metadata.get('game_actions', [])
            game_action_results = []
            
            # 添加游戏动作执行的调试信息
            logger.info(f"⚡ 执行阶段 - 游戏动作处理:")
            logger.info(f"  - 待执行动作数量: {len(game_actions)}")
            
            for i, action in enumerate(game_actions):
                logger.info(f"  - 动作{i+1}: {action.get('type', 'unknown')} (可执行: {action.get('executable', False)})")
                if action.get('executable', False):
                    logger.info(f"    正在执行动作: {action.get('type')} -> {action.get('target', 'N/A')}")
                    action_result = await self._execute_game_action(action)
                    game_action_results.append(action_result)
                    logger.info(f"    执行结果: {'成功' if action_result['success'] else '失败'} - {action_result['description']}")
                else:
                    logger.info(f"    跳过不可执行动作: {action.get('type', 'unknown')}")
            
            logger.info(f"  - 成功执行动作数量: {len([r for r in game_action_results if r['success']])}")
            
            # 第二步：构建包含游戏动作结果的上下文
            system_prompt = self.character_controller.build_system_prompt(
                self.character_state, self.game_state, 
                memory_result.knowledge_graph_nodes, self.script_constrainer
            )
            
            # 根据决策结果和游戏动作结果构建上下文
            context_parts = []
            
            # 添加游戏动作结果上下文
            if game_action_results:
                action_context = "\n".join([result['description'] for result in game_action_results if result['success']])
                if action_context:
                    context_parts.append(f"游戏动作结果：{action_context}")
            
            # 添加记忆上下文
            if memory_result.long_term_memory:
                memory_context = "\n".join([mem['content'] for mem in memory_result.long_term_memory[:3]])
                context_parts.append(f"相关记忆：{memory_context}")
            
            # 添加理解上下文
            context_understanding = understanding_result.analysis_metadata.get('context_understanding', '无上下文信息')
            context_parts.append(f"当前理解：{context_understanding}")
            
            # 添加决策上下文
            context_parts.append(f"对话策略：{decision_result.dialogue_strategy}")
            
            context = "\n\n".join(context_parts)
            
            # 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"{context}\n\n用户输入：{user_input}"}
            ]
            
            # 第三步：调用LLM生成自然语言响应
            raw_response = await self.model_manager.call_deepseek_api(messages)
            if not raw_response:
                raw_response = "*系统故障* 抱歉，我现在无法正常响应..."
            
            # 应用角色约束
            nlp_output = self.character_controller.apply_character_constraints(
                raw_response, self.character_state
            )
            
            # 触发游戏行为指令
            game_action = {
                'type': 'dialogue_response',
                'strategy': decision_result.dialogue_strategy,
                'timestamp': time.time(),
                'character_state_changes': [],
                'story_progression': False
            }
            
            # 检查是否需要剧情推进
            if decision_result.dialogue_strategy == "story_progression" and decision_result.response_options:
                story_option = next((opt for opt in decision_result.response_options 
                                   if opt['type'] == 'story_driven'), None)
                if story_option and story_option.get('branches'):
                    game_action['story_progression'] = True
                    game_action['available_branches'] = story_option['branches']
            
            # 更新角色状态数据
            character_state_update = {
                'health_change': 0.0,
                'stress_change': 0.0,
                'energy_change': -1.0,  # 每次对话消耗少量能量
                'mood_change': None,
                'location_change': None,
                'timestamp': time.time()
            }
            
            # 根据对话内容调整状态变化
            if understanding_result.sentiment_shift.get('stress_level', 0) > 0.7:
                character_state_update['stress_change'] = 2.0
            
            if len(user_input) > 100:  # 长对话消耗更多能量
                character_state_update['energy_change'] = -2.0
            
            # 执行元数据
            processing_end_time = time.time()
            execution_metadata = {
                'processing_time': processing_end_time - start_time,
                'confidence_score': cognition_result.confidence_score,
                'memory_used': len(memory_result.long_term_memory),
                'knowledge_nodes_accessed': len(memory_result.knowledge_graph_nodes),
                'response_length': len(nlp_output),
                'strategy_effectiveness': decision_result.action_utility_score.get(
                    decision_result.selected_option_id, 0.5
                )
            }
            
            result = ExecutionResult(
                nlp_output=nlp_output,
                game_action=game_action,
                character_state_update=character_state_update,
                execution_metadata=execution_metadata
            )
            
            logger.info(f"执行阶段完成，响应长度: {len(nlp_output)}")
            return result
            
        except Exception as e:
            logger.error(f"执行阶段处理错误: {e}")
            return ExecutionResult(
                nlp_output="*系统错误* 发生了意外错误，请稍后再试...",
                game_action={'type': 'error', 'timestamp': time.time()},
                character_state_update={},
                execution_metadata={'error': str(e)}
            )
    
    async def process_dialogue(self, user_input: str) -> str:
        """处理用户输入并生成响应 - 五阶段架构流水线"""
        try:
            logger.info(f"开始处理用户输入: {user_input[:50]}...")
            
            # 阶段1：认知阶段 - 分析当前游戏场景状态、整合角色信息、评估交互历史
            cognition_result = await self._cognition_stage(user_input)
            
            # 阶段2：记忆阶段 - 检索长期记忆、更新短期对话缓存、关联知识图谱节点
            memory_result = await self._memory_stage(cognition_result, user_input)
            
            # 阶段3：理解阶段 - 解析对话意图、评估建议执行效果、识别情感倾向变化
            understanding_result = await self._understanding_stage(cognition_result, memory_result, user_input)
            
            # 阶段4：决策阶段 - 生成多模态响应选项、计算行为效用评分、选择最优对话策略
            decision_result = await self._decision_stage(cognition_result, memory_result, understanding_result)
            
            # 阶段5：执行阶段 - 输出自然语言响应、触发游戏行为指令、更新角色状态数据
            execution_result = await self._execution_stage(
                cognition_result, memory_result, understanding_result, decision_result, user_input
            )
            
            # 应用角色状态更新
            self._apply_character_state_updates(execution_result.character_state_update)
            
            # 存储对话记忆（增强版）
            self._store_enhanced_dialogue_memory(
                user_input, execution_result.nlp_output, 
                cognition_result, memory_result, understanding_result, 
                decision_result, execution_result
            )
            
            # 更新游戏状态
            self._update_game_state(user_input)
            
            # 记录五阶段处理统计信息
            logger.info(f"五阶段处理完成 - 策略: {decision_result.dialogue_strategy}, "
                       f"处理时间: {execution_result.execution_metadata.get('processing_time', 0):.2f}s, "
                       f"置信度: {cognition_result.confidence_score}")
            
            return execution_result.nlp_output
            
        except Exception as e:
            logger.error(f"五阶段处理流程出错: {e}")
            return "*系统错误* 五阶段处理流程发生错误，请稍后再试..."
    
    def _apply_character_state_updates(self, character_state_update: Dict[str, Any]):
        """应用角色状态更新"""
        try:
            if not character_state_update:
                return
            
            # 更新健康值
            health_change = character_state_update.get('health_change', 0.0)
            if health_change != 0.0:
                self.character_state.health = max(0.0, min(100.0, 
                    self.character_state.health + health_change))
            
            # 更新压力值
            stress_change = character_state_update.get('stress_change', 0.0)
            if stress_change != 0.0:
                self.character_state.stress = max(0.0, min(100.0, 
                    self.character_state.stress + stress_change))
            
            # 更新能量值
            energy_change = character_state_update.get('energy_change', 0.0)
            if energy_change != 0.0:
                self.character_state.energy = max(0.0, min(100.0, 
                    self.character_state.energy + energy_change))
            
            # 更新情绪
            mood_change = character_state_update.get('mood_change')
            if mood_change:
                self.character_state.mood = mood_change
            
            # 更新位置
            location_change = character_state_update.get('location_change')
            if location_change:
                self.character_state.location = location_change
            
            logger.debug(f"角色状态已更新: 健康{health_change:+.1f}, 压力{stress_change:+.1f}, 能量{energy_change:+.1f}")
            
        except Exception as e:
            logger.error(f"应用角色状态更新时出错: {e}")
    
    def _store_enhanced_dialogue_memory(self, user_input: str, response: str,
                                      cognition_result: CognitionResult,
                                      memory_result: MemoryResult,
                                      understanding_result: UnderstandingResult,
                                      decision_result: DecisionResult,
                                      execution_result: ExecutionResult):
        """存储增强版对话记忆，包含五阶段处理信息"""
        try:
            # 构建增强的对话内容
            dialogue_content = f"用户: {user_input}\n角色: {response}"
            
            # 构建增强的元数据
            enhanced_metadata = {
                'type': 'dialogue',
                'timestamp': int(time.time()),
                'character_name': self.character_state.name,
                'character_health': self.character_state.health,
                'character_location': self.character_state.location,
                'permission_level': self.game_state.permission_level,
                'current_location': self.game_state.current_location,
                
                # 五阶段处理信息
                'cognition_confidence': cognition_result.confidence_score,
                'memory_nodes_used': len(memory_result.knowledge_graph_nodes),
                'dialogue_strategy': decision_result.dialogue_strategy,
                'processing_time': execution_result.execution_metadata.get('processing_time', 0),
                'response_length': len(response),
                
                # 理解阶段信息
                'contains_question': understanding_result.last_dialogue_intent.get('contains_question', False),
                'contains_command': understanding_result.last_dialogue_intent.get('contains_command', False),
                'user_engagement': understanding_result.suggestion_feedback.get('user_engagement_level', 0),
                
                # 决策阶段信息
                'response_options_count': len(decision_result.response_options),
                'selected_strategy_score': decision_result.action_utility_score.get(
                    decision_result.selected_option_id, 0.5
                ),
                
                # 执行阶段信息
                'game_action_type': execution_result.game_action.get('type', 'dialogue_response'),
                'story_progression': execution_result.game_action.get('story_progression', False)
            }
            
            # 存储到记忆系统
            success = self.memory_system.store_memory(dialogue_content, enhanced_metadata)
            
            if success:
                logger.debug("增强版对话记忆存储成功")
            else:
                logger.warning("增强版对话记忆存储失败")
                
        except Exception as e:
            logger.error(f"存储增强版对话记忆时出错: {e}")
            # 回退到基础记忆存储
            try:
                self.memory_system.store_memory(
                    f"用户: {user_input}\n角色: {response}",
                    {
                        'type': 'dialogue',
                        'timestamp': int(time.time()),
                        'character_name': self.character_state.name,
                        'fallback': True
                    }
                )
            except Exception as fallback_error:
                logger.error(f"回退记忆存储也失败: {fallback_error}")
    
    def _update_game_state(self, user_input: str):
        """更新游戏状态"""
        # 增加游戏时间
        self.game_state.time_elapsed += 1
        
        # 检查是否发现新的数据碎片
        new_fragments = self._extract_fragments_from_input(user_input)
        if new_fragments:
            self.game_state = self.game_state_manager.update_permission(
                self.game_state, new_fragments
            )
            
            # 尝试解锁新知识
            for info_id in self.knowledge_graph.knowledge_nodes:
                self.knowledge_graph.unlock_information(info_id, self.game_state.data_fragments)
        
        # 触发事件
        triggered_events = self.game_state_manager.trigger_events(
            self.game_state, self.character_state
        )
        
        # 更新角色状态
        if triggered_events:
            self.character_state = self.character_controller.update_character_state(
                self.character_state, triggered_events
            )
    
    def _extract_fragments_from_input(self, user_input: str) -> List[str]:
        """从用户输入中提取数据碎片"""
        fragments = []
        fragment_keywords = {
            'engine_data': ['引擎', '发动机', '推进器'],
            'power_grid_info': ['电力', '能源', '电网'],
            'navigation_log': ['导航', '航行', '坐标'],
            'mission_briefing': ['任务', '使命', '目标'],
            'captain_key': ['船长', '钥匙', '密码'],
            'security_override': ['安全', '覆盖', '权限']
        }
        
        for fragment_id, keywords in fragment_keywords.items():
            if any(keyword in user_input for keyword in keywords):
                fragments.append(fragment_id)
        
        return fragments
    
    def process_data_fragment(self, fragment_name: str) -> Dict[str, Any]:
        """处理数据碎片"""
        try:
            # 添加数据碎片到游戏状态
            if fragment_name not in self.game_state.data_fragments:
                self.game_state.data_fragments.append(fragment_name)
                logger.info(f"获得数据碎片: {fragment_name}")
                
                # 检查是否解锁新知识
                unlocked_knowledge = []
                for info_id in self.knowledge_graph.knowledge_nodes:
                    if self.knowledge_graph.unlock_information(info_id, self.game_state.data_fragments):
                        unlocked_knowledge.append(info_id)
                
                # 更新权限等级
                old_permission = self.game_state.permission_level
                self.game_state = self.game_state_manager.update_permission(
                    self.game_state, [fragment_name]
                )
                
                return {
                    'success': True,
                    'fragment': fragment_name,
                    'unlocked_knowledge': unlocked_knowledge,
                    'permission_change': self.game_state.permission_level - old_permission,
                    'message': f"数据碎片 '{fragment_name}' 已处理"
                }
            else:
                return {
                    'success': False,
                    'fragment': fragment_name,
                    'message': f"数据碎片 '{fragment_name}' 已经存在"
                }
        except Exception as e:
            logger.error(f"处理数据碎片失败: {e}")
            return {
                'success': False,
                'fragment': fragment_name,
                'message': f"处理失败: {str(e)}"
            }
    
    def get_available_branches(self) -> List[Dict[str, Any]]:
        """获取当前可用的剧情分支"""
        try:
            return self.script_constrainer.get_available_branches(
                self.character_state, self.game_state
            )
        except Exception as e:
            logger.error(f"获取可用分支失败: {e}")
            return []
    
    def select_branch(self, branch_id: str) -> Dict[str, Any]:
        """选择剧情分支"""
        try:
            success = self.script_constrainer.advance_to_branch(
                branch_id, self.character_state, self.game_state
            )
            
            if success:
                # 存储分支选择记忆
                self.memory_system.store_memory(
                    f"选择了剧情分支: {branch_id}",
                    {
                        'type': 'branch_selection',
                        'branch_id': branch_id,
                        'timestamp': int(time.time()),
                        'story_node': self.game_state.current_story_node
                    }
                )
                
                return {
                    'success': True,
                    'branch_id': branch_id,
                    'new_node': self.game_state.current_story_node,
                    'message': f"成功选择分支: {branch_id}"
                }
            else:
                return {
                    'success': False,
                    'branch_id': branch_id,
                    'message': "分支选择失败，可能是条件不满足或分支不存在"
                }
                
        except Exception as e:
            logger.error(f"选择分支失败: {e}")
            return {
                'success': False,
                'branch_id': branch_id,
                'message': f"选择分支时发生错误: {str(e)}"
            }
    
    def get_story_progress(self) -> Dict[str, Any]:
        """获取剧情进度信息"""
        try:
            progress = self.script_constrainer.get_story_progress(self.game_state)
            current_node = self.script_constrainer.get_current_story_node(self.game_state)
            
            return {
                'current_node': {
                    'id': progress['current_node_id'],
                    'title': progress['current_node_title'],
                    'description': current_node.description if current_node else '无描述',
                    'character_situation': current_node.character_situation if current_node else '无情况描述'
                },
                'progress': {
                    'total_nodes': progress['total_nodes'],
                    'available_branches': progress['available_branches']
                },
                'game_state': {
                    'permission_level': self.game_state.permission_level,
                    'data_fragments_count': len(self.game_state.data_fragments),
                    'time_elapsed': self.game_state.time_elapsed,
                    'current_location': self.game_state.current_location
                }
            }
            
        except Exception as e:
            logger.error(f"获取剧情进度失败: {e}")
            return {
                'current_node': {'id': 'unknown', 'title': '未知', 'description': '无法获取', 'character_situation': '无法获取'},
                'progress': {'total_nodes': 0, 'available_branches': 0},
                'game_state': {'permission_level': 1, 'data_fragments_count': 0, 'time_elapsed': 0, 'current_location': 'unknown'}
            }
    
    def reset_story(self) -> Dict[str, Any]:
        """重置剧情到初始状态"""
        try:
            self.script_constrainer.reset_story(self.game_state)
            
            # 存储重置记忆
            self.memory_system.store_memory(
                "剧情已重置到初始状态",
                {
                    'type': 'story_reset',
                    'timestamp': int(time.time()),
                    'previous_node': self.game_state.current_story_node
                }
            )
            
            return {
                'success': True,
                'message': "剧情已重置到初始状态",
                'current_node': self.game_state.current_story_node
            }
            
        except Exception as e:
            logger.error(f"重置剧情失败: {e}")
            return {
                'success': False,
                'message': f"重置剧情时发生错误: {str(e)}"
            }
    
    def get_current_story_context(self) -> Dict[str, Any]:
        """获取当前剧情上下文信息"""
        try:
            current_node = self.script_constrainer.get_current_story_node(self.game_state)
            if not current_node:
                return {
                    "current_node": "unknown",
                    "title": "未知",
                    "description": "当前没有可用的剧情信息",
                    "character_situation": "未知",
                    "context_background": "未知",
                    "available_branches": []
                }
            
            # 获取可用分支信息
            available_branches = self.get_available_branches()
            
            return {
                "current_node": current_node.id,
                "title": current_node.title,
                "description": current_node.description,
                "character_situation": current_node.character_situation,
                "context_background": current_node.context_background,
                "available_branches": available_branches
            }
            
        except Exception as e:
            logger.error(f"获取剧情上下文失败: {e}")
            return {
                "current_node": "error",
                "title": "错误",
                "description": f"获取剧情上下文时出现错误: {e}",
                "character_situation": "错误",
                "context_background": "错误",
                "available_branches": []
            }
    
    def get_game_status(self) -> Dict[str, Any]:
        """获取当前游戏状态"""
        return {
            'character_state': asdict(self.character_state),
            'game_state': asdict(self.game_state),
            'available_knowledge': self.knowledge_graph.get_available_knowledge(
                self.game_state.permission_level
            )
        }
    
    def save_game_state(self, filepath: str = 'game_save.json'):
        """保存游戏状态"""
        try:
            save_data = {
                'character_state': asdict(self.character_state),
                'game_state': asdict(self.game_state),
                'timestamp': int(time.time())
            }
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"游戏状态已保存到: {filepath}")
            
        except Exception as e:
            logger.error(f"保存游戏状态失败: {e}")
    
    def load_game_state(self, filepath: str = 'game_save.json'):
        """加载游戏状态"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                save_data = json.load(f)
            
            self.character_state = CharacterState(**save_data['character_state'])
            self.game_state = GameState(**save_data['game_state'])
            
            logger.info(f"游戏状态已从 {filepath} 加载")
            
        except Exception as e:
            logger.error(f"加载游戏状态失败: {e}")


# 示例使用
if __name__ == "__main__":
    async def main():
        # 创建LLM核心实例
        llm_core = LLMCore()
        
        # 示例对话
        test_inputs = [
            "你好，我是飞船的AI系统，请报告你的当前状态。",
            "检查引擎系统的状态。",
            "我们需要前往工程舱检查电力系统。"
        ]
        
        for user_input in test_inputs:
            print(f"\n用户输入: {user_input}")
            response = await llm_core.process_input(user_input)
            print(f"角色响应: {response}")
            
            # 显示游戏状态
            status = llm_core.get_game_status()
            print(f"权限等级: {status['game_state']['permission_level']}")
            print(f"数据碎片: {len(status['game_state']['data_fragments'])}个")
            print(f"角色健康: {status['character_state']['health']:.1f}%")
        
        # 保存游戏状态
        llm_core.save_game_state()
    
    # 运行示例
    asyncio.run(main())