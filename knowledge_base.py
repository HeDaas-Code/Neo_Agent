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
from database_manager import DatabaseManager
from base_knowledge import BaseKnowledge
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class KnowledgeBase:
    """
    知识库管理器
    每5轮对话提取一次知识，形成结构化的知识性记忆
    使用数据库替代JSON文件存储

    数据结构：
    - entities: 主体字典 {entity_uuid: entity_data}
      - 每个主体有唯一UUID
      - 每个主体只能有一个定义(definition)
      - 每个主体可以有多个相关信息(related_info)
    """

    def __init__(self,
                 db_manager: DatabaseManager = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化知识库管理器

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()

        # API配置（用于提取知识）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 初始化基础知识库（共享数据库管理器）
        self.base_knowledge = BaseKnowledge(db_manager=self.db)

        # 检查是否需要从JSON迁移数据
        if os.path.exists('knowledge_base.json'):
            print("○ 检测到旧的知识库JSON文件，正在迁移到数据库...")
            self.db.migrate_from_json('knowledge_base.json', 'knowledge_base')
            os.rename('knowledge_base.json', 'knowledge_base.json.bak')
            print("✓ JSON文件已备份为 knowledge_base.json.bak")

        print(f"✓ 知识库已初始化（使用数据库存储）")



    def _find_or_create_entity(self, entity_name: str) -> str:
        """
        查找或创建主体（使用数据库）

        Args:
            entity_name: 主体名称

        Returns:
            主体UUID
        """
        return self.db.find_or_create_entity(entity_name)

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
        使用数据库存储

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

                # 使用基础知识作为定义（存入数据库）
                existing_def = self.db.get_entity_definition(entity_uuid)
                if not existing_def:
                    self.db.set_entity_definition(
                        entity_uuid=entity_uuid,
                        content=base_fact['content'],
                        type_='基础知识',
                        source='基础知识库',
                        confidence=1.0,
                        priority=100,
                        is_base_knowledge=True
                    )
                return entity_uuid

        # 查找或创建实体
        entity_uuid = self._find_or_create_entity(entity_name)

        # 检查当前定义是否为基础知识
        existing_def = self.db.get_entity_definition(entity_uuid)
        if existing_def and existing_def.get('is_base_knowledge'):
            print(f"⚠ 主体 '{entity_name}' 的定义来自基础知识库，不可更改")
            print(f"  基础知识: {existing_def['content']}")
            print(f"  尝试更新为: {definition}")
            print(f"  → 保持基础知识不变（优先级100）")
            return entity_uuid

        # 检查是否存在旧定义
        if existing_def:
            print(f"⚠ 主体 '{entity_name}' 的定义发生冲突:")
            print(f"  旧定义: {existing_def.get('content', '')[:50]}...")
            print(f"  新定义: {definition[:50]}...")
            print(f"  → 采用新定义（置信度: {confidence}）")

        # 设置新定义（会覆盖旧定义）
        self.db.set_entity_definition(
            entity_uuid=entity_uuid,
            content=definition,
            type_=knowledge_type,
            source=source,
            confidence=confidence,
            priority=50,
            is_base_knowledge=False
        )

        return entity_uuid

    def add_related_info_to_entity(self,
                                   entity_uuid: str = None,
                                   entity_name: str = None,
                                   info_content: str = '',
                                   info_type: str = '相关信息',
                                   source: str = '',
                                   confidence: float = 0.8,
                                   status: str = '疑似') -> Optional[str]:
        """
        为主体添加相关信息（不限数量，使用数据库）
        新添加的信息默认标记为"疑似"状态

        Args:
            entity_uuid: 主体UUID（优先使用）
            entity_name: 主体名称（如果没有UUID则使用名称查找）
            info_content: 信息内容
            info_type: 信息类型
            source: 来源
            confidence: 置信度（相关信息的置信度低于定义）
            status: 状态（疑似/确认），默认为"疑似"

        Returns:
            信息UUID，失败返回None
        """
        # 确定主体UUID
        if entity_uuid is None and entity_name is None:
            print("✗ 必须提供entity_uuid或entity_name")
            return None

        if entity_uuid is None:
            entity_uuid = self._find_or_create_entity(entity_name)

        # 验证实体是否存在
        entity = self.db.get_entity_by_uuid(entity_uuid)
        if not entity:
            print(f"✗ 主体UUID {entity_uuid} 不存在")
            return None

        # 添加相关信息到数据库（包含状态字段）
        info_uuid = self.db.add_entity_related_info(
            entity_uuid=entity_uuid,
            content=info_content,
            type_=info_type,
            source=source,
            confidence=confidence,
            status=status
        )

        return info_uuid

    def get_relevant_knowledge_for_query(self, query: str, max_items: int = 10) -> Dict[str, Any]:
        """
        根据用户查询获取相关知识（理解阶段使用）
        按优先级返回：基础知识（最高优先级100） > 定义（高置信度） > 相关信息（中置信度）
        使用数据库查询

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
            debug_logger.log_info('KnowledgeBase', f'查找实体: {entity_name}')

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
                    'confidence': 1.0,
                    'priority': 0,
                    'is_base_knowledge': True,
                    'created_at': base_fact['created_at']
                })
                entities_found.append(entity_name)
            else:
                debug_logger.log_info('KnowledgeBase', f'未找到基础知识: {entity_name}')

            # 查找主体是否存在于普通知识库（数据库）
            entity = self.db.get_entity_by_name(entity_name)
            if entity:
                entity_uuid = entity['uuid']

                if entity_name not in entities_found:
                    entities_found.append(entity_name)

                # 添加定义（次优先级）
                definition = self.db.get_entity_definition(entity_uuid)
                if definition and not definition.get('is_base_knowledge', False):
                    knowledge_items.append({
                        'entity_name': entity['name'],
                        'type': '定义',
                        'content': definition['content'],
                        'confidence': definition['confidence'],
                        'priority': 1,
                        'created_at': definition['created_at']
                    })

                # 添加相关信息（第三优先级，优先确认状态的知识）
                related_infos = self.db.get_entity_related_info(entity_uuid)
                
                # 分离确认和疑似的知识
                confirmed = [i for i in related_infos if i.get('status') == DatabaseManager.STATUS_CONFIRMED]
                suspected = [i for i in related_infos if i.get('status') != DatabaseManager.STATUS_CONFIRMED]
                
                # 确认的按时间倒序，疑似的也按时间倒序
                confirmed.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                suspected.sort(key=lambda x: x.get('created_at', ''), reverse=True)
                
                # 合并：确认的在前，疑似的在后，取前3条
                related_infos_sorted = confirmed + suspected
                
                for info in related_infos_sorted[:3]:
                    knowledge_items.append({
                        'entity_name': entity['name'],
                        'type': info['type'],
                        'content': info['content'],
                        'confidence': info['confidence'],
                        'status': info.get('status', '疑似'),
                        'mention_count': info.get('mention_count', 1),
                        'priority': 2,
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
        添加一条知识到知识库（新版：支持主体-定义-信息结构，使用数据库）

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

        return result_uuid

    def extract_knowledge(self, messages: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        从最近的对话中提取知识
        只从用户的语句中提取信息，不从助手的回复中提取
        
        Args:
            messages: 最近5轮的对话消息列表

        Returns:
            提取的知识列表，每个知识包含entity(主体)、is_definition(是否为定义)、content等
        """
        try:
            # 只提取用户消息
            user_messages = [msg for msg in messages if msg.get('role') == 'user']
            
            if not user_messages:
                print("○ 没有用户消息，无法提取知识")
                return None
            
            # 构建用户对话文本
            user_text = ""
            for msg in user_messages:
                user_text += f"用户: {msg['content']}\n"

            # 构建知识提取请求（新版提示词，只关注用户的陈述）
            extraction_prompt = f"""请从以下用户的语句中提取关键信息和知识点。

重要要求：
1. **只提取用户明确陈述的信息**，不要推断或假设
2. 识别用户提到的**主体**（entity）：如人名、物品名、概念名等
3. 对每个主体，区分以下两类信息：
   - **定义**（definition）：主体的核心定义、本质属性（如"是什么"）
   - **相关信息**（related_info）：主体的其他属性、特征、用途、偏好等（不限数量）
4. 每个主体只应有一个定义，如果用户多次提到冲突的定义，以最新的为准
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
    "source": "用户陈述",
    "confidence": 0.9
  }}
]

用户语句：
{user_text}

请提取知识点（只返回JSON数组）："""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的知识提取助手，擅长从用户的陈述中识别主体、定义和相关信息。你只从用户明确说出的内容中提取信息，不进行推断。你只返回JSON格式的数据，不添加任何解释。'},
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
        获取所有知识（新版：返回结构化的主体-定义-信息列表，从数据库）

        Args:
            sort_by_confidence: 是否按置信度排序（定义优先于相关信息）

        Returns:
            知识列表，包含主体、定义、相关信息等
        """
        result = []

        # 从数据库获取所有实体
        entities = self.db.get_all_entities()

        for entity in entities:
            entity_uuid = entity['uuid']
            entity_name = entity['name']

            # 获取并添加主体的定义
            definition = self.db.get_entity_definition(entity_uuid)
            if definition:
                result.append({
                    'uuid': entity_uuid,
                    'entity_name': entity_name,
                    'title': f"{entity_name}的定义",
                    'content': definition['content'],
                    'type': definition['type'],
                    'source': definition.get('source', ''),
                    'confidence': definition['confidence'],
                    'is_definition': True,
                    'created_at': definition['created_at'],
                    'updated_at': definition.get('updated_at', definition['created_at'])
                })

            # 获取并添加主体的相关信息
            related_infos = self.db.get_entity_related_info(entity_uuid)
            for info in related_infos:
                result.append({
                    'uuid': info['uuid'],
                    'entity_name': entity_name,
                    'title': f"{entity_name}的{info['type']}",
                    'content': info['content'],
                    'type': info['type'],
                    'source': info.get('source', ''),
                    'confidence': info['confidence'],
                    'status': info.get('status', '疑似'),
                    'mention_count': info.get('mention_count', 1),
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
        获取知识库统计信息（从数据库）

        Returns:
            统计信息字典
        """
        # 从数据库获取所有知识
        all_knowledge = self.get_all_knowledge(sort_by_confidence=False)

        # 统计各类型知识数量
        type_counts = {}
        definition_count = 0
        related_info_count = 0

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

        # 获取数据库统计
        db_stats = self.db.get_statistics()
        
        # 统计知识状态分布（仅对相关信息）
        status_counts = {
            DatabaseManager.STATUS_SUSPECTED: 0,
            DatabaseManager.STATUS_CONFIRMED: 0
        }
        for item in all_knowledge:
            if not item.get('is_definition', False):
                status = item.get('status', DatabaseManager.STATUS_SUSPECTED)
                status_counts[status] = status_counts.get(status, 0) + 1

        return {
            'total_entities': db_stats['entities_count'],
            'total_definitions': definition_count,
            'total_related_info': related_info_count,
            'total_knowledge': len(all_knowledge),
            'base_knowledge_facts': base_kb_stats['total_facts'],
            'type_distribution': type_counts,
            'confidence_distribution': {
                'high (>=0.9)': high_confidence,
                'medium (0.7-0.9)': medium_confidence,
                'low (<0.7)': low_confidence
            },
            'status_distribution': status_counts,
            'database_size_kb': db_stats.get('db_size_kb', 0)
        }

    def clear_knowledge(self):
        """
        清空知识库（清空数据库中的实体和知识）
        """
        # 这里需要实现清空数据库实体的方法
        # 暂时只打印提示
        print("⚠ 清空知识库功能需要实现数据库级联删除")
        print("  建议手动删除数据库文件重新开始")

    def search_knowledge(self, keyword: str = None, knowledge_type: str = None,
                        entity_name: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库（使用数据库）

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


if __name__ == '__main__':
    print("=" * 60)
    print("知识库管理器测试")
    print("=" * 60)

    kb = KnowledgeBase()

    print("\n当前知识库统计:")
    stats = kb.get_statistics()
    print(f"总实体数: {stats['total_entities']}")
    print(f"总知识数: {stats['total_knowledge']}")
    print(f"定义数: {stats['total_definitions']}")
    print(f"相关信息数: {stats['total_related_info']}")
    print(f"基础知识数: {stats['base_knowledge_facts']}")
    print(f"类型分布: {stats['type_distribution']}")
    print(f"数据库大小: {stats['database_size_kb']:.2f} KB")

    all_knowledge = kb.get_all_knowledge()
    if all_knowledge:
        print(f"\n知识列表 (前5条):")
        for i, knowledge in enumerate(all_knowledge[:5], 1):
            print(f"{i}. [{knowledge['type']}] {knowledge['title']}")
            print(f"   内容: {knowledge['content'][:50]}...")
            print(f"   置信度: {knowledge['confidence']:.2f}")
    else:
        print("\n知识库为空")

    print("\n✓ 测试完成")
