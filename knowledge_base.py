"""
知识库管理模块
负责从对话中提取和管理知识性记忆
实现主体-定义-信息的三层绑定结构，支持冲突检测和置信度管理
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from base_knowledge import BaseKnowledge
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class KnowledgeBase:
    """
    知识库管理器
    每5轮对话提取一次知识，形成结构化的知识性记忆

    数据结构：
    - entities: 主体字典 {entity_uuid: entity_data}
      - 每个主体有唯一UUID
      - 每个主体只能有一个定义(definition)
      - 每个主体可以有多个相关信息(related_info)
    - knowledge_items: 为了向后兼容保留的旧格式知识列表
    """

    def __init__(self,
                 knowledge_file: str = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None,
                 base_knowledge_file: str = None):
        """
        初始化知识库管理器

        Args:
            knowledge_file: 知识库文件路径（默认knowledge_base.json）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
            base_knowledge_file: 基础知识库文件路径
        """
        # 文件路径配置
        self.knowledge_file = knowledge_file or 'knowledge_base.json'

        # API配置（用于提取知识）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 初始化基础知识库（最高优先级）
        self.base_knowledge = BaseKnowledge(base_knowledge_file)

        # 新的知识数据结构：主体字典
        self.entities: Dict[str, Dict[str, Any]] = {}

        # 主体名称到UUID的映射，方便查找
        self.entity_name_map: Dict[str, str] = {}

        # 旧的知识数据（向后兼容）
        self.knowledge_items: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

        # 加载现有知识库
        self.load_knowledge()

    def load_knowledge(self):
        """
        从文件加载知识库
        支持新旧格式兼容
        """
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                    # 加载新格式：主体字典
                    self.entities = data.get('entities', {})
                    self.entity_name_map = data.get('entity_name_map', {})

                    # 加载旧格式（向后兼容）
                    self.knowledge_items = data.get('knowledge_items', [])
                    self.metadata = data.get('metadata', {})

                    # 如果存在旧格式但没有新格式，尝试迁移
                    if self.knowledge_items and not self.entities:
                        print("○ 检测到旧格式知识库，开始迁移...")
                        self._migrate_old_knowledge()

                    print(f"✓ 成功加载知识库: {len(self.entities)} 个主体, {len(self.knowledge_items)} 条旧知识")
            else:
                print("○ 未找到知识库文件，创建新的知识库")
                self.entities = {}
                self.entity_name_map = {}
                self.knowledge_items = []
                self.metadata = {
                    'created_at': datetime.now().isoformat(),
                    'total_knowledge': 0,
                    'last_extraction': None,
                    'version': '2.0'  # 新版本标记
                }
        except Exception as e:
            print(f"✗ 加载知识库时出错: {e}")
            self.entities = {}
            self.entity_name_map = {}
            self.knowledge_items = []
            self.metadata = {}

    def _migrate_old_knowledge(self):
        """
        将旧格式知识迁移到新的主体-定义-信息结构
        """
        migrated_count = 0
        for old_item in self.knowledge_items:
            # 尝试从标题或内容中提取主体名称
            entity_name = old_item.get('title', '未知主体')

            # 将旧知识作为定义或相关信息添加
            if old_item.get('type') in ['个人信息', '事实', '定义']:
                # 作为定义添加
                self._add_or_update_entity_definition(
                    entity_name=entity_name,
                    definition=old_item.get('content', ''),
                    knowledge_type=old_item.get('type', '事实'),
                    source=old_item.get('source', ''),
                    created_at=old_item.get('created_at', datetime.now().isoformat()),
                    confidence=0.7  # 迁移的旧知识给予中等置信度
                )
            else:
                # 作为相关信息添加
                entity_uuid = self._find_or_create_entity(entity_name)
                if entity_uuid:
                    self.add_related_info_to_entity(
                        entity_uuid=entity_uuid,
                        info_content=old_item.get('content', ''),
                        info_type=old_item.get('type', '其他'),
                        source=old_item.get('source', '')
                    )
            migrated_count += 1

        print(f"✓ 已迁移 {migrated_count} 条旧知识到新格式")
        self.save_knowledge()

    def save_knowledge(self):
        """
        保存知识库到文件
        """
        try:
            data = {
                # 新格式
                'entities': self.entities,
                'entity_name_map': self.entity_name_map,

                # 旧格式（向后兼容）
                'knowledge_items': self.knowledge_items,
                'metadata': self.metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 知识库已保存: {len(self.entities)} 个主体, {len(self.knowledge_items)} 条旧知识")
        except Exception as e:
            print(f"✗ 保存知识库时出错: {e}")

    def _find_or_create_entity(self, entity_name: str) -> str:
        """
        查找或创建主体

        Args:
            entity_name: 主体名称

        Returns:
            主体UUID
        """
        # 标准化主体名称（去除空格，统一大小写）
        normalized_name = entity_name.strip().lower()

        # 查找是否已存在
        if normalized_name in self.entity_name_map:
            return self.entity_name_map[normalized_name]

        # 创建新主体
        entity_uuid = str(uuid.uuid4())
        self.entities[entity_uuid] = {
            'uuid': entity_uuid,
            'name': entity_name,  # 保留原始名称
            'normalized_name': normalized_name,
            'definition': None,  # 主体的定义（唯一）
            'related_info': [],  # 主体的相关信息列表（不限数量）
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        self.entity_name_map[normalized_name] = entity_uuid
        return entity_uuid

    def _add_or_update_entity_definition(self,
                                         entity_name: str,
                                         definition: str,
                                         knowledge_type: str = '定义',
                                         source: str = '',
                                         created_at: str = None,
                                         confidence: float = 1.0) -> str:
        """
        添加或更新主体的定义（每个主体只能有一个定义，新定义会覆盖旧定义）
        但基础知识库中的定义拥有最高优先级，不会被覆盖

        Args:
            entity_name: 主体名称
            definition: 定义内容
            knowledge_type: 知识类型
            source: 来源
            created_at: 创建时间（用于迁移旧数据）
            confidence: 置信度（0-1之间，定义的置信度高于相关信息）

        Returns:
            主体UUID
        """
        # 检查是否与基础知识冲突
        if self.base_knowledge.check_conflict_with_base(entity_name, definition):
            print(f"⚠ 由于与基础知识冲突，拒绝添加/更新定义: {entity_name}")
            print(f"  → 保持基础知识不变")

            # 如果实体不存在，创建它但使用基础知识作为定义
            base_fact = self.base_knowledge.get_base_fact(entity_name)
            if base_fact:
                entity_uuid = self._find_or_create_entity(entity_name)
                entity = self.entities[entity_uuid]

                # 使用基础知识作为定义
                if entity['definition'] is None:
                    entity['definition'] = {
                        'content': base_fact['content'],
                        'type': '基础知识',
                        'source': '基础知识库',
                        'confidence': 1.0,  # 基础知识100%置信度
                        'priority': 100,  # 最高优先级
                        'is_base_knowledge': True,  # 标记为基础知识
                        'created_at': base_fact['created_at'],
                        'updated_at': datetime.now().isoformat()
                    }

                return entity_uuid

        entity_uuid = self._find_or_create_entity(entity_name)
        entity = self.entities[entity_uuid]

        # 检查当前定义是否为基础知识
        if entity['definition'] is not None and entity['definition'].get('is_base_knowledge', False):
            print(f"⚠ 主体 '{entity_name}' 的定义来自基础知识库，不可更改")
            print(f"  基础知识: {entity['definition']['content']}")
            print(f"  尝试更新为: {definition}")
            print(f"  → 保持基础知识不变（优先级100）")
            return entity_uuid

        # 检查是否存在旧定义
        if entity['definition'] is not None:
            old_def = entity['definition']
            print(f"⚠ 主体 '{entity_name}' 的定义发生冲突:")
            print(f"  旧定义: {old_def.get('content', '')[:50]}...")
            print(f"  新定义: {definition[:50]}...")
            print(f"  → 采用新定义（置信度: {confidence}）")

            # 将旧定义标记为过时并移到历史记录
            if 'definition_history' not in entity:
                entity['definition_history'] = []

            old_def['obsolete'] = True
            old_def['obsolete_at'] = datetime.now().isoformat()
            old_def['replaced_by'] = {
                'content': definition,
                'time': created_at or datetime.now().isoformat()
            }
            entity['definition_history'].append(old_def)

        # 设置新定义
        entity['definition'] = {
            'content': definition,
            'type': knowledge_type,
            'source': source,
            'confidence': confidence,  # 定义的置信度
            'is_base_knowledge': False,  # 非基础知识
            'created_at': created_at or datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        entity['updated_at'] = datetime.now().isoformat()
        return entity_uuid

    def add_related_info_to_entity(self,
                                   entity_uuid: str = None,
                                   entity_name: str = None,
                                   info_content: str = '',
                                   info_type: str = '相关信息',
                                   source: str = '',
                                   confidence: float = 0.8) -> Optional[str]:
        """
        为主体添加相关信息（不限数量）

        Args:
            entity_uuid: 主体UUID（优先使用）
            entity_name: 主体名称（如果没有UUID则使用名称查找）
            info_content: 信息内容
            info_type: 信息类型
            source: 来源
            confidence: 置信度（相关信息的置信度低于定义）

        Returns:
            信息UUID，失败返回None
        """
        # 确定主体UUID
        if entity_uuid is None and entity_name is None:
            print("✗ 必须提供entity_uuid或entity_name")
            return None

        if entity_uuid is None:
            entity_uuid = self._find_or_create_entity(entity_name)

        if entity_uuid not in self.entities:
            print(f"✗ 主体UUID {entity_uuid} 不存在")
            return None

        entity = self.entities[entity_uuid]

        # 创建相关信息
        info_uuid = str(uuid.uuid4())
        info_item = {
            'uuid': info_uuid,
            'content': info_content,
            'type': info_type,
            'source': source,
            'confidence': confidence,  # 相关信息的置信度
            'created_at': datetime.now().isoformat(),
            'obsolete': False  # 是否已过时
        }

        entity['related_info'].append(info_item)
        entity['updated_at'] = datetime.now().isoformat()

        return info_uuid

    def mark_related_info_obsolete(self, entity_uuid: str, info_uuid: str, reason: str = '') -> bool:
        """
        标记某条相关信息为过时（当用户纠正错误时）

        Args:
            entity_uuid: 主体UUID
            info_uuid: 信息UUID
            reason: 标记原因

        Returns:
            是否成功标记
        """
        if entity_uuid not in self.entities:
            return False

        entity = self.entities[entity_uuid]

        for info in entity['related_info']:
            if info['uuid'] == info_uuid:
                info['obsolete'] = True
                info['obsolete_at'] = datetime.now().isoformat()
                info['obsolete_reason'] = reason
                print(f"✓ 已将信息标记为过时: {info['content'][:50]}...")
                return True

        return False

    def cleanup_obsolete_info(self):
        """
        清理所有被标记为过时的相关信息
        清理旧定义历史中过时的定义（保留最近3个历史定义）
        """
        cleaned_count = 0

        for entity_uuid, entity in self.entities.items():
            # 清理过时的相关信息
            original_count = len(entity['related_info'])
            entity['related_info'] = [
                info for info in entity['related_info']
                if not info.get('obsolete', False)
            ]
            cleaned_count += original_count - len(entity['related_info'])

            # 清理过多的定义历史（只保留最近3个）
            if 'definition_history' in entity and len(entity['definition_history']) > 3:
                entity['definition_history'] = entity['definition_history'][-3:]

        if cleaned_count > 0:
            print(f"✓ 已清理 {cleaned_count} 条过时信息")
            self.save_knowledge()

        return cleaned_count

    def extract_knowledge(self, messages: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        从最近的对话中提取知识
        提取主体、定义和相关信息的结构化知识

        Args:
            messages: 最近5轮的对话消息列表

        Returns:
            提取的知识列表，每个知识包含entity(主体)、is_definition(是否为定义)、content等
        """
        try:
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                role_name = "用户" if msg['role'] == 'user' else "助手"
                conversation_text += f"{role_name}: {msg['content']}\n"

            # 构建知识提取请求（新版提示词，关注主体-定义-信息结构）
            extraction_prompt = f"""请从以下对话中提取用户提到的关键信息和知识点。

重要要求：
1. 识别对话中的**主体**（entity）：如人名、物品名、概念名等
2. 对每个主体，区分以下两类信息：
   - **定义**（definition）：主体的核心定义、本质属性（如"是什么"）
   - **相关信息**（related_info）：主体的其他属性、特征、用途等（不限数量）
3. 每个主体只应有一个定义，如果对话中有冲突的定义，以最新的为准
4. 如果用户纠正了之前的错误信息，标记old_info_correction=true
5. 知识类型包括：个人信息、偏好、事实、经历、观点、定义等
6. 只提取明确的、有价值的信息，避免重复和模糊的内容
7. 如果没有值得记录的知识，返回空列表

返回JSON格式（只返回JSON数组，不要其他文字）：
[
  {{
    "entity_name": "主体名称",
    "is_definition": true,
    "content": "定义内容或相关信息内容",
    "type": "知识类型",
    "source": "来源概述",
    "confidence": 0.9,
    "is_correction": false
  }}
]

对话内容：
{conversation_text}

请提取知识点（只返回JSON数组）："""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的知识提取助手，擅长识别主体、定义和相关信息。你只返回JSON格式的数据，不添加任何解释。'},
                    {'role': 'user', 'content': extraction_prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 1500,
                'stream': False
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                # 尝试解析JSON
                # 清理可能的markdown代码块标记
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                content = content.strip()

                try:
                    knowledge_list = json.loads(content)
                    if isinstance(knowledge_list, list):
                        return knowledge_list
                    else:
                        print(f"✗ 返回的不是列表格式: {type(knowledge_list)}")
                        return None
                except json.JSONDecodeError as e:
                    print(f"✗ JSON解析失败: {e}")
                    print(f"原始内容: {content[:200]}...")
                    return None
            else:
                print("✗ 未能获取有效的知识提取结果")
                return None

        except Exception as e:
            print(f"✗ 提取知识时出错: {e}")
            return None

    def extract_entities_from_query(self, query: str) -> List[str]:
        """
        从用户查询中提取相关主体

        Args:
            query: 用户输入的查询文本

        Returns:
            提取到的主体名称列表
        """
        try:
            # 构建实体提取请求
            extraction_prompt = f"""请从以下用户输入中提取所有可能相关的主体（实体）名称。

主体可以是：人名、物品名、概念名、地点名、事件名等。

用户输入：
{query}

请以JSON数组格式返回主体名称列表（只返回JSON，不要其他文字）：
["主体1", "主体2", ...]

如果没有明确的主体，返回空数组 []"""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的实体识别助手，只返回JSON格式数据。'},
                    {'role': 'user', 'content': extraction_prompt}
                ],
                'temperature': 0.2,
                'max_tokens': 500,
                'stream': False
            }

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=15
            )

            response.raise_for_status()
            result = response.json()

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                # 清理markdown代码块
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                content = content.strip()

                try:
                    entities = json.loads(content)
                    if isinstance(entities, list):
                        result = [e for e in entities if isinstance(e, str)]
                        debug_logger.log_info('KnowledgeBase', '实体提取成功', {
                            'query': query,
                            'entities': result
                        })
                        return result
                    else:
                        debug_logger.log_info('KnowledgeBase', '实体提取结果不是列表', {'content': content})
                        return []
                except json.JSONDecodeError as e:
                    print(f"✗ 实体提取JSON解析失败")
                    debug_logger.log_error('KnowledgeBase', 'JSON解析失败', e)
                    return []
            else:
                debug_logger.log_info('KnowledgeBase', 'API响应中没有choices')
                return []

        except Exception as e:
            print(f"✗ 提取实体时出错: {e}")
            debug_logger.log_error('KnowledgeBase', '提取实体时出错', e)
            return []

    def get_relevant_knowledge_for_query(self, query: str, max_items: int = 10) -> Dict[str, Any]:
        """
        根据用户查询获取相关知识（理解阶段使用）
        按优先级返回：基础知识（最高优先级100） > 定义（高置信度） > 相关信息（中置信度）

        Args:
            query: 用户查询
            max_items: 最多返回的知识条目数

        Returns:
            包含实体和相关知识的字典
        """
        debug_logger.log_module('KnowledgeBase', '开始检索相关知识', f'查询: {query}')

        # 1. 提取查询中的主体
        entities = self.extract_entities_from_query(query)

        if not entities:
            debug_logger.log_info('KnowledgeBase', '未识别到实体')
            return {
                'query': query,
                'entities_found': [],
                'knowledge_items': [],
                'base_knowledge_items': [],
                'summary': '未在查询中识别到相关主体。'
            }

        # 2. 对每个主体，查找对应的知识
        knowledge_items = []
        base_knowledge_items = []
        entities_found = []

        for entity_name in entities:
            normalized_name = entity_name.strip().lower()

            debug_logger.log_info('KnowledgeBase', f'查找实体: {entity_name}', {
                'normalized_name': normalized_name
            })

            # 首先检查基础知识库（最高优先级）
            base_fact = self.base_knowledge.get_base_fact(entity_name)
            if base_fact:
                debug_logger.log_info('KnowledgeBase', f'找到基础知识: {entity_name}', {
                    'content': base_fact['content']
                })
                base_knowledge_items.append({
                    'entity_name': entity_name,
                    'type': '基础知识',
                    'content': base_fact['content'],
                    'confidence': 1.0,  # 100%置信度
                    'priority': 0,  # 最高优先级（数字越小优先级越高）
                    'is_base_knowledge': True,
                    'created_at': base_fact['created_at']
                })
                entities_found.append(entity_name)
            else:
                debug_logger.log_info('KnowledgeBase', f'未找到基础知识: {entity_name}')

            # 查找主体是否存在于普通知识库
            if normalized_name in self.entity_name_map:
                entity_uuid = self.entity_name_map[normalized_name]
                entity = self.entities[entity_uuid]

                if entity_name not in entities_found:
                    entities_found.append(entity_name)

                # 添加定义（次优先级）
                if entity['definition']:
                    definition = entity['definition']

                    # 如果定义来自基础知识，跳过（已经在基础知识中添加了）
                    if not definition.get('is_base_knowledge', False):
                        knowledge_items.append({
                            'entity_name': entity['name'],
                            'type': '定义',
                            'content': definition['content'],
                            'confidence': definition['confidence'],
                            'priority': 1,  # 次优先级
                            'created_at': definition['created_at']
                        })

                # 添加相关信息（第三优先级，只取最新的几条）
                active_info = [
                    info for info in entity['related_info']
                    if not info.get('obsolete', False)
                ]

                # 按创建时间降序排序，取最新的3条
                active_info.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                for info in active_info[:3]:
                    knowledge_items.append({
                        'entity_name': entity['name'],
                        'type': info['type'],
                        'content': info['content'],
                        'confidence': info['confidence'],
                        'priority': 2,  # 第三优先级
                        'created_at': info['created_at']
                    })

        # 3. 合并基础知识和普通知识，按优先级和置信度排序
        all_knowledge = base_knowledge_items + knowledge_items
        all_knowledge.sort(key=lambda x: (x['priority'], -x['confidence']))

        # 4. 限制返回数量
        all_knowledge = all_knowledge[:max_items]

        # 5. 生成摘要
        summary = self._generate_knowledge_summary(entities_found, all_knowledge)

        debug_logger.log_info('KnowledgeBase', '知识检索完成', {
            'entities_found': entities_found,
            'base_knowledge_count': len(base_knowledge_items),
            'normal_knowledge_count': len(knowledge_items),
            'total_knowledge': len(all_knowledge)
        })

        return {
            'query': query,
            'entities_found': entities_found,
            'knowledge_items': knowledge_items,
            'base_knowledge_items': base_knowledge_items,
            'all_knowledge': all_knowledge,
            'summary': summary
        }

    def _generate_knowledge_summary(self, entities: List[str], knowledge_items: List[Dict]) -> str:
        """
        生成知识摘要文本

        Args:
            entities: 识别到的实体列表
            knowledge_items: 知识项列表

        Returns:
            摘要文本
        """
        if not entities:
            return '未找到相关主体。'

        if not knowledge_items:
            return f'识别到主体：{", ".join(entities)}，但知识库中暂无相关信息。'

        # 按主体分组
        by_entity = {}
        for item in knowledge_items:
            entity_name = item['entity_name']
            if entity_name not in by_entity:
                by_entity[entity_name] = []
            by_entity[entity_name].append(item)

        summary_parts = [f'识别到 {len(entities)} 个相关主体：{", ".join(entities)}。']
        summary_parts.append('\n相关知识：')

        for entity_name, items in by_entity.items():
            definitions = [i for i in items if i['type'] == '定义']
            others = [i for i in items if i['type'] != '定义']

            if definitions:
                summary_parts.append(f'\n• {entity_name}: {definitions[0]["content"]}')

            if others:
                for item in others[:2]:  # 最多显示2条相关信息
                    summary_parts.append(f'  - {item["type"]}: {item["content"][:50]}...')

        return ''.join(summary_parts)

    def add_knowledge(self, knowledge_data: Dict[str, Any], source_messages: List[Dict[str, Any]]) -> str:
        """
        添加一条知识到知识库（新版：支持主体-定义-信息结构）

        Args:
            knowledge_data: 知识数据（包含entity_name, is_definition, content, type等）
            source_messages: 来源消息列表

        Returns:
            知识的UUID（主体UUID或信息UUID）
        """
        entity_name = knowledge_data.get('entity_name', '未知主体')
        is_definition = knowledge_data.get('is_definition', False)
        content = knowledge_data.get('content', '')
        knowledge_type = knowledge_data.get('type', '其他')
        source = knowledge_data.get('source', '对话记录')
        confidence = knowledge_data.get('confidence', 0.9 if is_definition else 0.8)
        is_correction = knowledge_data.get('is_correction', False)

        # 如果是纠正信息，尝试标记旧信息为过时
        if is_correction:
            self._handle_knowledge_correction(entity_name, content)

        if is_definition:
            # 添加或更新定义
            entity_uuid = self._add_or_update_entity_definition(
                entity_name=entity_name,
                definition=content,
                knowledge_type=knowledge_type,
                source=source,
                confidence=confidence
            )
            result_uuid = entity_uuid
        else:
            # 添加相关信息
            info_uuid = self.add_related_info_to_entity(
                entity_name=entity_name,
                info_content=content,
                info_type=knowledge_type,
                source=source,
                confidence=confidence
            )
            result_uuid = info_uuid

        # 同时以旧格式保存（向后兼容）
        old_format_uuid = str(uuid.uuid4())
        knowledge_item = {
            'uuid': old_format_uuid,
            'title': f"{entity_name}{'的定义' if is_definition else ''}",
            'content': content,
            'type': knowledge_type,
            'source': source,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'source_time_range': {
                'start': source_messages[0].get('timestamp', '') if source_messages else '',
                'end': source_messages[-1].get('timestamp', '') if source_messages else ''
            },
            'tags': self._generate_tags(knowledge_data),
            'entity_name': entity_name,
            'is_definition': is_definition,
            'confidence': confidence
        }

        self.knowledge_items.append(knowledge_item)
        self.metadata['total_knowledge'] = len(self.knowledge_items)
        self.metadata['last_extraction'] = datetime.now().isoformat()

        return result_uuid

    def _handle_knowledge_correction(self, entity_name: str, new_content: str):
        """
        处理知识纠正：标记旧的错误信息为过时

        Args:
            entity_name: 主体名称
            new_content: 新的正确内容
        """
        normalized_name = entity_name.strip().lower()
        if normalized_name not in self.entity_name_map:
            return

        entity_uuid = self.entity_name_map[normalized_name]
        entity = self.entities[entity_uuid]

        # 标记所有相关信息为可能过时（实际应该通过更智能的方式判断）
        # 这里简化处理：标记最近的一条相关信息
        if entity['related_info']:
            # 找到最近添加的信息
            latest_info = max(entity['related_info'],
                            key=lambda x: x.get('created_at', ''),
                            default=None)
            if latest_info and not latest_info.get('obsolete', False):
                self.mark_related_info_obsolete(
                    entity_uuid,
                    latest_info['uuid'],
                    reason=f"用户提供了新的信息: {new_content[:30]}..."
                )

    def _generate_tags(self, knowledge_data: Dict[str, Any]) -> List[str]:
        """
        根据知识数据生成标签

        Args:
            knowledge_data: 知识数据

        Returns:
            标签列表
        """
        tags = []

        # 根据类型添加标签
        knowledge_type = knowledge_data.get('type', '')
        if knowledge_type:
            tags.append(knowledge_type)

        # 可以根据内容添加更多标签
        # 这里简化处理

        return tags

    def search_knowledge(self, keyword: str = None, knowledge_type: str = None,
                        entity_name: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            keyword: 关键词
            knowledge_type: 知识类型
            entity_name: 主体名称

        Returns:
            匹配的知识列表（按置信度排序）
        """
        results = self.get_all_knowledge(sort_by_confidence=True)

        # 按主体名称筛选
        if entity_name:
            entity_lower = entity_name.lower()
            results = [
                k for k in results
                if entity_lower in k.get('entity_name', '').lower()
            ]

        # 按关键词筛选
        if keyword:
            keyword_lower = keyword.lower()
            results = [
                k for k in results
                if keyword_lower in k.get('title', '').lower() or
                   keyword_lower in k.get('content', '').lower() or
                   keyword_lower in k.get('entity_name', '').lower()
            ]

        # 按类型筛选
        if knowledge_type:
            results = [k for k in results if k.get('type', '') == knowledge_type]

        return results

    def get_all_knowledge(self, sort_by_confidence: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有知识（新版：返回结构化的主体-定义-信息列表）

        Args:
            sort_by_confidence: 是否按置信度排序（定义优先于相关信息）

        Returns:
            知识列表，包含主体、定义、相关信息等
        """
        result = []

        for entity_uuid, entity in self.entities.items():
            # 添加主体的定义
            if entity['definition']:
                definition = entity['definition']
                result.append({
                    'uuid': entity_uuid,
                    'entity_name': entity['name'],
                    'title': f"{entity['name']}的定义",
                    'content': definition['content'],
                    'type': definition['type'],
                    'source': definition['source'],
                    'confidence': definition['confidence'],
                    'is_definition': True,
                    'created_at': definition['created_at'],
                    'updated_at': definition.get('updated_at', definition['created_at'])
                })

            # 添加主体的相关信息（过滤掉过时的）
            for info in entity['related_info']:
                if not info.get('obsolete', False):
                    result.append({
                        'uuid': info['uuid'],
                        'entity_name': entity['name'],
                        'title': f"{entity['name']}的{info['type']}",
                        'content': info['content'],
                        'type': info['type'],
                        'source': info['source'],
                        'confidence': info['confidence'],
                        'is_definition': False,
                        'created_at': info['created_at'],
                        'updated_at': info.get('created_at')
                    })

        # 按置信度排序（定义优先）
        if sort_by_confidence:
            result.sort(key=lambda x: (x['confidence'], x['is_definition']), reverse=True)

        return result

    def get_knowledge_by_uuid(self, knowledge_uuid: str) -> Optional[Dict[str, Any]]:
        """
        根据UUID获取知识

        Args:
            knowledge_uuid: 知识UUID

        Returns:
            知识项，如果不存在返回None
        """
        for item in self.knowledge_items:
            if item.get('uuid') == knowledge_uuid:
                return item
        return None

    def get_base_knowledge_prompt(self) -> str:
        """
        获取基础知识提示词文本，用于嵌入到系统提示词中
        这些知识具有最高优先级，AI必须严格遵循

        Returns:
            基础知识提示词文本
        """
        return self.base_knowledge.generate_base_knowledge_prompt()

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        # 统计各类型知识数量
        type_counts = {}
        definition_count = 0
        related_info_count = 0

        all_knowledge = self.get_all_knowledge(sort_by_confidence=False)

        for item in all_knowledge:
            item_type = item.get('type', '其他')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

            if item.get('is_definition', False):
                definition_count += 1
            else:
                related_info_count += 1

        # 统计置信度分布
        high_confidence = sum(1 for k in all_knowledge if k.get('confidence', 0) >= 0.9)
        medium_confidence = sum(1 for k in all_knowledge if 0.7 <= k.get('confidence', 0) < 0.9)
        low_confidence = sum(1 for k in all_knowledge if k.get('confidence', 0) < 0.7)

        # 获取基础知识库统计
        base_kb_stats = self.base_knowledge.get_statistics()

        return {
            'total_entities': len(self.entities),
            'total_definitions': definition_count,
            'total_related_info': related_info_count,
            'total_knowledge': len(all_knowledge),
            'base_knowledge_facts': base_kb_stats['total_facts'],  # 基础知识数量
            'type_distribution': type_counts,
            'confidence_distribution': {
                'high (>=0.9)': high_confidence,
                'medium (0.7-0.9)': medium_confidence,
                'low (<0.7)': low_confidence
            },
            'last_extraction': self.metadata.get('last_extraction', 'Never'),
            'created_at': self.metadata.get('created_at', 'Unknown'),
            'knowledge_file': self.knowledge_file,
            'base_knowledge_file': self.base_knowledge.base_knowledge_file,
            'version': self.metadata.get('version', '2.0')
        }

    def clear_knowledge(self):
        """
        清空知识库（包括主体字典和旧格式知识）
        """
        self.entities = {}
        self.entity_name_map = {}
        self.knowledge_items = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'total_knowledge': 0,
            'last_extraction': None,
            'version': '2.0'
        }
        self.save_knowledge()
        print("✓ 知识库已清空（包括所有主体和知识）")

    def delete_knowledge(self, knowledge_uuid: str) -> bool:
        """
        删除指定的知识

        Args:
            knowledge_uuid: 知识UUID

        Returns:
            是否删除成功
        """
        for i, item in enumerate(self.knowledge_items):
            if item.get('uuid') == knowledge_uuid:
                del self.knowledge_items[i]
                self.metadata['total_knowledge'] = len(self.knowledge_items)
                self.save_knowledge()
                print(f"✓ 已删除知识: {item.get('title', '')}")
                return True
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("知识库管理器测试")
    print("=" * 60)

    kb = KnowledgeBase()

    print("\n当前知识库统计:")
    stats = kb.get_statistics()
    print(f"总知识数: {stats['total_knowledge']}")
    print(f"类型分布: {stats['type_distribution']}")

    if kb.knowledge_items:
        print("\n知识列表:")
        for i, knowledge in enumerate(kb.knowledge_items, 1):
            print(f"{i}. [{knowledge['type']}] {knowledge['title']}")
            print(f"   内容: {knowledge['content'][:50]}...")
            print(f"   UUID: {knowledge['uuid']}")

