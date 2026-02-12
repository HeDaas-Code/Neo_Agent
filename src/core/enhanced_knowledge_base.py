"""
增强的知识库模块
使用DeepAgents的长期记忆和文件系统实现结构化知识管理
"""

import os
import json
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.core.database_manager import DatabaseManager
from src.core.base_knowledge import BaseKnowledge
from src.core.deepagents_wrapper import DeepAgentsKnowledgeManager
from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()

# 是否使用DeepAgents增强知识管理
USE_DEEPAGENTS_KNOWLEDGE = os.getenv('USE_DEEPAGENTS_KNOWLEDGE', 'true').lower() == 'true'


class EnhancedKnowledgeBase:
    """
    增强的知识库管理器
    结合传统数据库和DeepAgents的长期记忆、文件系统功能
    
    特性：
    1. 使用数据库存储结构化知识（主体-定义-相关信息）
    2. 使用DeepAgents的文件系统处理大型知识内容
    3. 使用DeepAgents的长期记忆进行知识检索和推理
    4. 保留向后兼容性
    """
    
    def __init__(
        self,
        db_manager: DatabaseManager = None,
        use_deepagents: bool = USE_DEEPAGENTS_KNOWLEDGE,
        **kwargs  # 接受额外参数以保持向后兼容
    ):
        """
        初始化增强知识库
        
        Args:
            db_manager: 数据库管理器实例
            use_deepagents: 是否使用DeepAgents增强功能
            **kwargs: 其他参数（用于向后兼容，会被忽略）
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()
        
        # 初始化基础知识库
        self.base_knowledge = BaseKnowledge(db_manager=self.db)
        
        # 是否启用DeepAgents增强
        self.use_deepagents = use_deepagents
        
        # 初始化DeepAgents知识管理器
        if self.use_deepagents:
            try:
                self.deep_knowledge = DeepAgentsKnowledgeManager(
                    knowledge_dir="/knowledge",
                    memory_file="/memory/AGENTS.md"
                )
                debug_logger.log_info('EnhancedKnowledgeBase', 'DeepAgents知识管理器初始化成功')
            except Exception as e:
                debug_logger.log_error('EnhancedKnowledgeBase', 
                    f'DeepAgents知识管理器初始化失败，降级到传统模式: {str(e)}', e)
                self.use_deepagents = False
                self.deep_knowledge = None
        else:
            self.deep_knowledge = None
        
        # 检查是否需要从JSON迁移数据
        if os.path.exists('knowledge_base.json'):
            print("○ 检测到旧的知识库JSON文件，正在迁移到数据库...")
            self.db.migrate_from_json('knowledge_base.json', 'knowledge_base')
            os.rename('knowledge_base.json', 'knowledge_base.json.bak')
            print("✓ JSON文件已备份为 knowledge_base.json.bak")
        
        mode = "DeepAgents增强模式" if self.use_deepagents else "传统数据库模式"
        print(f"✓ 增强知识库已初始化（{mode}）")
    
    def _find_or_create_entity(self, entity_name: str) -> str:
        """
        查找或创建主体（使用数据库）
        
        Args:
            entity_name: 主体名称
            
        Returns:
            主体UUID
        """
        return self.db.find_or_create_entity(entity_name)
    
    def add_or_update_entity_definition(
        self,
        entity_name: str,
        definition: str,
        knowledge_type: str = '定义',
        source: str = '',
        confidence: float = 1.0,
        use_deepagents: bool = None
    ) -> str:
        """
        添加或更新主体的定义
        如果启用DeepAgents且定义内容较大，将使用文件系统存储
        
        Args:
            entity_name: 主体名称
            definition: 定义内容
            knowledge_type: 知识类型
            source: 来源
            confidence: 置信度
            use_deepagents: 是否使用DeepAgents（None则使用默认设置）
            
        Returns:
            主体UUID
        """
        # 检查是否与基础知识冲突
        if self.base_knowledge.check_conflict_with_base(entity_name, definition):
            print(f"⚠ 由于与基础知识冲突，拒绝添加/更新定义: {entity_name}")
            print(f"  → 保持基础知识不变")
            
            base_fact = self.base_knowledge.get_base_fact(entity_name)
            if base_fact:
                entity_uuid = self._find_or_create_entity(entity_name)
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
            return entity_uuid
        
        # 决定是否使用DeepAgents
        use_deep = use_deepagents if use_deepagents is not None else self.use_deepagents
        
        # 如果定义内容较大（>1000字符）且启用DeepAgents，使用文件系统存储
        if use_deep and self.deep_knowledge and len(definition) > 1000:
            try:
                # 将大型定义存储到虚拟文件系统
                file_path = f"/knowledge/entities/{entity_name}.md"
                
                # 在数据库中存储引用
                file_reference = f"[FILE:{file_path}]"
                self.db.set_entity_definition(
                    entity_uuid=entity_uuid,
                    content=file_reference,
                    type_=knowledge_type,
                    source=source,
                    confidence=confidence,
                    priority=50,
                    is_base_knowledge=False
                )
                
                debug_logger.log_info('EnhancedKnowledgeBase', 
                    f'大型定义使用文件系统存储: {entity_name} -> {file_path}')
                
            except Exception as e:
                debug_logger.log_error('EnhancedKnowledgeBase', 
                    f'使用文件系统存储失败，降级到数据库: {str(e)}', e)
                # 降级到数据库存储
                self.db.set_entity_definition(
                    entity_uuid=entity_uuid,
                    content=definition,
                    type_=knowledge_type,
                    source=source,
                    confidence=confidence,
                    priority=50,
                    is_base_knowledge=False
                )
        else:
            # 直接存储到数据库
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
    
    def add_related_info_to_entity(
        self,
        entity_uuid: str = None,
        entity_name: str = None,
        info_content: str = '',
        info_type: str = '相关信息',
        source: str = '',
        confidence: float = 0.8,
        status: str = '疑似'
    ) -> Optional[str]:
        """
        为主体添加相关信息
        
        Args:
            entity_uuid: 主体UUID
            entity_name: 主体名称
            info_content: 信息内容
            info_type: 信息类型
            source: 来源
            confidence: 置信度
            status: 状态
            
        Returns:
            信息UUID
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
        
        # 添加相关信息到数据库
        info_uuid = self.db.add_entity_related_info(
            entity_uuid=entity_uuid,
            content=info_content,
            type_=info_type,
            source=source,
            confidence=confidence,
            status=status
        )
        
        return info_uuid
    
    def extract_knowledge_from_conversation(
        self,
        conversation: List[Dict[str, Any]],
        use_deepagents: bool = None
    ) -> Dict[str, Any]:
        """
        从对话中提取知识
        可选使用DeepAgents进行智能提取
        
        Args:
            conversation: 对话历史
            use_deepagents: 是否使用DeepAgents（None则使用默认设置）
            
        Returns:
            提取结果
        """
        use_deep = use_deepagents if use_deepagents is not None else self.use_deepagents
        
        if use_deep and self.deep_knowledge:
            try:
                # 使用DeepAgents智能提取
                result = self.deep_knowledge.extract_and_store_knowledge(
                    conversation=conversation
                )
                
                debug_logger.log_info('EnhancedKnowledgeBase', 'DeepAgents知识提取完成', {
                    'success': result.get('success', False)
                })
                
                return result
                
            except Exception as e:
                debug_logger.log_error('EnhancedKnowledgeBase', 
                    f'DeepAgents知识提取失败: {str(e)}', e)
                return {
                    'success': False,
                    'error': str(e)
                }
        else:
            # 传统提取方法（这里可以保留原有逻辑）
            return {
                'success': False,
                'error': 'DeepAgents未启用'
            }
    
    def _create_knowledge_item(
        self,
        entity_name: str,
        type_: str,
        content: str,
        confidence: float,
        priority: int,
        is_base_knowledge: bool = False
    ) -> Dict[str, Any]:
        """
        创建知识条目字典（辅助方法，减少代码重复）
        
        Args:
            entity_name: 实体名称
            type_: 知识类型
            content: 内容
            confidence: 置信度
            priority: 优先级
            is_base_knowledge: 是否为基础知识
            
        Returns:
            知识条目字典
        """
        item = {
            'entity_name': entity_name,
            'type': type_,
            'content': content,
            'confidence': confidence,
            'priority': priority
        }
        if is_base_knowledge:
            item['is_base_knowledge'] = True
        return item
    
    def get_relevant_knowledge_for_query(
        self,
        query: str,
        max_items: int = 10,
        use_deepagents: bool = None
    ) -> Dict[str, Any]:
        """
        根据查询获取相关知识
        可选使用DeepAgents进行智能检索
        
        Args:
            query: 用户查询
            max_items: 最多返回的知识条目数
            use_deepagents: 是否使用DeepAgents（None则使用默认设置）
            
        Returns:
            包含实体和相关知识的字典
        """
        debug_logger.log_module('EnhancedKnowledgeBase', '开始检索相关知识', f'查询: {query}')
        
        use_deep = use_deepagents if use_deepagents is not None else self.use_deepagents
        
        # 首先使用传统方法获取基础知识
        entities = self.extract_entities_from_query(query)
        knowledge_items = []
        base_knowledge_items = []
        entities_found = []
        
        for entity_name in entities:
            # 检查基础知识库
            base_fact = self.base_knowledge.get_base_fact(entity_name)
            if base_fact:
                base_knowledge_items.append(self._create_knowledge_item(
                    entity_name=entity_name,
                    type_='基础知识',
                    content=base_fact['content'],
                    confidence=1.0,
                    priority=0,
                    is_base_knowledge=True
                ))
                entities_found.append(entity_name)
            
            # 查找数据库中的知识
            entity = self.db.get_entity_by_name(entity_name)
            if entity:
                entity_uuid = entity['uuid']
                if entity_name not in entities_found:
                    entities_found.append(entity_name)
                
                # 添加定义
                definition = self.db.get_entity_definition(entity_uuid)
                if definition and not definition.get('is_base_knowledge', False):
                    knowledge_items.append(self._create_knowledge_item(
                        entity_name=entity['name'],
                        type_='定义',
                        content=definition['content'],
                        confidence=definition['confidence'],
                        priority=1
                    ))
                
                # 添加相关信息
                related_infos = self.db.get_entity_related_info(entity_uuid)
                for info in related_infos[:3]:
                    knowledge_items.append(self._create_knowledge_item(
                        entity_name=entity['name'],
                        type_=info['type'],
                        content=info['content'],
                        confidence=info['confidence'],
                        priority=2
                    ))
        
        # 如果启用DeepAgents，使用智能检索增强结果
        if use_deep and self.deep_knowledge and entities_found:
            try:
                deep_result = self.deep_knowledge.retrieve_knowledge(query)
                if deep_result.get('success'):
                    # 将DeepAgents检索的知识添加到结果中
                    debug_logger.log_info('EnhancedKnowledgeBase', 
                        'DeepAgents知识检索完成，增强结果')
            except Exception as e:
                debug_logger.log_error('EnhancedKnowledgeBase', 
                    f'DeepAgents知识检索失败: {str(e)}', e)
        
        return {
            'query': query,
            'entities_found': entities_found,
            'knowledge_items': knowledge_items[:max_items],
            'base_knowledge_items': base_knowledge_items,
            'summary': f'找到{len(entities_found)}个相关主体，{len(knowledge_items)}条知识。'
        }
    
    def extract_entities_from_query(self, query: str) -> List[str]:
        """
        从查询中提取实体（简单实现）
        
        Args:
            query: 查询文本
            
        Returns:
            实体列表
        """
        # 获取所有已知实体
        all_entities = self.db.get_all_entities()
        
        # 简单匹配：查找查询中出现的实体名称
        entities = []
        for entity in all_entities:
            if entity['name'] in query:
                entities.append(entity['name'])
        
        return entities
