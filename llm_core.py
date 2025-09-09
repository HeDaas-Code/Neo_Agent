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
    
    def __post_init__(self):
        if self.permissions is None:
            self.permissions = []


@dataclass
class GameState:
    """游戏状态数据类"""
    permission_level: int = 1
    data_fragments: List[str] = None
    current_location: str = "bridge"
    time_elapsed: int = 0
    events_triggered: List[str] = None
    character_health: float = 100.0
    character_stress: float = 0.0
    
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
        self.prompt_templates = config.get('prompts', {})
        
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
                          available_knowledge: List[str]) -> str:
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

行为指导：
1. 保持角色一致性，根据当前状态调整语气和行为
2. 如果健康状况不佳，表现出相应的虚弱或痛苦
3. 如果压力过高，可能表现出焦虑、恐慌或判断力下降
4. 根据权限等级限制你能执行的操作
5. 对未知或超出权限的请求表示无法执行
6. 保持对话的连贯性和真实感
"""
        
        return base_prompt + cognitive_constraints + knowledge_prompt + behavior_guide
    
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
        # 这里应该与KnowledgeGraph集成，简化实现
        basic_knowledge = ["basic_ship_layout", "emergency_protocols"]
        return knowledge_id in basic_knowledge


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


class GameStateManager:
    """游戏状态管理类"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.events_config = config.get('events', {})
    
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
    
    def __init__(self, config_path: str = 'config.json'):
        # 加载配置
        self.config = self._load_config(config_path)
        
        # 初始化各个组件
        self.model_manager = ModelManager(self.config.get('model', {}))
        self.memory_system = MemorySystem(self.config.get('memory', {}), self.model_manager)
        self.character_controller = CharacterController(self.config.get('character', {}))
        self.knowledge_graph = KnowledgeGraph(self.config.get('knowledge', {}))
        self.game_state_manager = GameStateManager(self.config.get('game', {}))
        
        # 初始化游戏状态
        self.character_state = CharacterState(
            name=self.character_controller.character_info['name'],
            location="bridge"
        )
        self.game_state = GameState()
        
        logger.info("LLM驱动核心初始化完成")
    
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
    
    async def process_dialogue(self, user_input: str) -> str:
        """处理用户输入并生成响应"""
        try:
            # 1. 检索相关记忆
            memories = self.memory_system.retrieve_memories(user_input, limit=3)
            context = "\n".join([mem['content'] for mem in memories])
            
            # 2. 获取可用知识
            available_knowledge = self.knowledge_graph.get_available_knowledge(
                self.game_state.permission_level
            )
            
            # 3. 构建系统提示词
            system_prompt = self.character_controller.build_system_prompt(
                self.character_state, self.game_state, available_knowledge
            )
            
            # 4. 构建消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"上下文记忆：{context}\n\n用户输入：{user_input}"}
            ]
            
            # 5. 调用LLM生成响应
            response = await self.model_manager.call_deepseek_api(messages)
            if not response:
                return "*系统故障* 抱歉，我现在无法正常响应..."
            
            # 6. 应用角色约束
            filtered_response = self.character_controller.apply_character_constraints(
                response, self.character_state
            )
            
            # 7. 存储对话记忆
            self.memory_system.store_memory(
                f"用户: {user_input}\n角色: {filtered_response}",
                {
                    'type': 'dialogue',
                    'timestamp': int(time.time()),
                    'character_name': self.character_state.name,
                    'character_health': self.character_state.health,
                    'character_location': self.character_state.location,
                    'permission_level': self.game_state.permission_level,
                    'current_location': self.game_state.current_location
                }
            )
            
            # 8. 更新游戏状态
            self._update_game_state(user_input)
            
            return filtered_response
            
        except Exception as e:
            logger.error(f"处理用户输入时出错: {e}")
            return "*系统错误* 发生了意外错误，请稍后再试..."
    
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