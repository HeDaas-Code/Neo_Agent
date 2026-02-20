"""
Cognee 智能记忆管理模块
基于 Cognee 实现持久化动态 AI 记忆，结合向量搜索和图数据库
将对话、知识转化为可搜索、可关联的智能记忆

Cognee: https://docs.cognee.ai/
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()

# Cognee 配置
COGNEE_ENABLED = os.getenv('COGNEE_ENABLED', 'true').lower() == 'true'
# 优先使用 SILICONFLOW_API_KEY，然后是 LLM_API_KEY
COGNEE_LLM_API_KEY = os.getenv('SILICONFLOW_API_KEY') or os.getenv('LLM_API_KEY')


class CogneeMemoryManager:
    """
    Cognee 智能记忆管理器
    
    将原始数据（对话、文档、知识）转化为智能体的持久动态记忆：
    1. 使用向量搜索实现语义检索
    2. 使用图数据库建立知识关联
    3. 支持动态更新和演化
    
    功能：
    - 对话记忆：存储和检索对话历史
    - 知识图谱：自动构建实体关系图
    - 语义搜索：基于含义的智能检索
    - 模块化知识：支持自定义知识块
    """
    
    def __init__(
        self,
        api_key: str = None,
        enabled: bool = COGNEE_ENABLED
    ):
        """
        初始化 Cognee 记忆管理器
        
        Args:
            api_key: LLM API 密钥
            enabled: 是否启用 Cognee
        """
        self.enabled = enabled
        self.api_key = api_key or COGNEE_LLM_API_KEY
        self._initialized = False
        self._cognee = None
        
        if self.enabled:
            self._setup_cognee()
        else:
            debug_logger.log_info('CogneeMemoryManager', 'Cognee 已禁用')
    
    def _setup_cognee(self):
        """配置 Cognee 环境"""
        try:
            import cognee
            
            # 设置 API 密钥
            if self.api_key:
                os.environ['LLM_API_KEY'] = self.api_key
            
            self._cognee = cognee
            self._initialized = True
            
            debug_logger.log_info('CogneeMemoryManager', 'Cognee 初始化成功')
            print("✓ Cognee 智能记忆系统已初始化")
            
        except ImportError as e:
            debug_logger.log_error('CogneeMemoryManager', 
                f'Cognee 未安装，请运行: pip install cognee', e)
            self.enabled = False
            self._initialized = False
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', 
                f'Cognee 初始化失败: {str(e)}', e)
            self.enabled = False
            self._initialized = False
    
    async def add_memory(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        添加记忆到 Cognee
        
        Args:
            content: 要存储的内容
            memory_type: 记忆类型（conversation/knowledge/worldview）
            metadata: 附加元数据
            
        Returns:
            是否成功添加
        """
        if not self._initialized:
            debug_logger.log_warning('CogneeMemoryManager', 'Cognee 未初始化，跳过添加记忆')
            return False
        
        try:
            # 格式化内容，添加类型标记便于检索
            formatted_content = f"[{memory_type}] {content}"
            if metadata:
                metadata_str = " | ".join([f"{k}: {v}" for k, v in metadata.items()])
                formatted_content += f" ({metadata_str})"
            
            # 添加到 Cognee
            await self._cognee.add(formatted_content)
            
            debug_logger.log_info('CogneeMemoryManager', f'记忆已添加: {memory_type}', {
                'content_length': len(content)
            })
            
            return True
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'添加记忆失败: {str(e)}', e)
            return False
    
    async def add_conversation(
        self,
        messages: List[Dict[str, str]],
        session_id: str = None
    ) -> bool:
        """
        添加对话记录到记忆系统
        
        Args:
            messages: 对话消息列表 [{"role": "user/assistant", "content": "..."}]
            session_id: 会话ID
            
        Returns:
            是否成功添加
        """
        if not self._initialized:
            return False
        
        try:
            # 格式化对话
            conversation_text = "\n".join([
                f"{'用户' if msg['role'] == 'user' else '助手'}: {msg['content']}"
                for msg in messages
            ])
            
            metadata = {
                "session_id": session_id or datetime.now().strftime("%Y%m%d%H%M%S"),
                "timestamp": datetime.now().isoformat(),
                "message_count": len(messages)
            }
            
            return await self.add_memory(conversation_text, "conversation", metadata)
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'添加对话失败: {str(e)}', e)
            return False
    
    async def add_knowledge(
        self,
        entity_name: str,
        knowledge_content: str,
        knowledge_type: str = "fact",
        source: str = "conversation"
    ) -> bool:
        """
        添加知识到记忆系统
        
        Args:
            entity_name: 实体名称
            knowledge_content: 知识内容
            knowledge_type: 知识类型（fact/definition/relation）
            source: 知识来源
            
        Returns:
            是否成功添加
        """
        if not self._initialized:
            return False
        
        try:
            content = f"关于 {entity_name}: {knowledge_content}"
            metadata = {
                "entity": entity_name,
                "type": knowledge_type,
                "source": source,
                "timestamp": datetime.now().isoformat()
            }
            
            return await self.add_memory(content, "knowledge", metadata)
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'添加知识失败: {str(e)}', e)
            return False
    
    async def add_worldview(
        self,
        worldview_content: str,
        category: str = "general"
    ) -> bool:
        """
        添加世界观内容到记忆系统
        
        Args:
            worldview_content: 世界观内容
            category: 分类（general/rules/locations/characters/events）
            
        Returns:
            是否成功添加
        """
        if not self._initialized:
            return False
        
        try:
            metadata = {
                "category": category,
                "timestamp": datetime.now().isoformat()
            }
            
            return await self.add_memory(worldview_content, "worldview", metadata)
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'添加世界观失败: {str(e)}', e)
            return False
    
    async def cognify(self) -> bool:
        """
        处理并构建知识图谱
        将添加的内容转化为可查询的知识图谱
        
        Returns:
            是否成功处理
        """
        if not self._initialized:
            return False
        
        try:
            await self._cognee.cognify()
            
            debug_logger.log_info('CogneeMemoryManager', '知识图谱构建完成')
            print("✓ Cognee 知识图谱已更新")
            
            return True
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'构建知识图谱失败: {str(e)}', e)
            return False
    
    async def memify(self) -> bool:
        """
        应用记忆算法
        为图谱添加记忆算法，优化检索效果
        
        Returns:
            是否成功应用
        """
        if not self._initialized:
            return False
        
        try:
            await self._cognee.memify()
            
            debug_logger.log_info('CogneeMemoryManager', '记忆算法已应用')
            
            return True
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'应用记忆算法失败: {str(e)}', e)
            return False
    
    async def search(
        self,
        query: str,
        memory_type: str = None,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        搜索记忆
        
        Args:
            query: 搜索查询
            memory_type: 限制搜索的记忆类型（可选）
            max_results: 最大结果数量
            
        Returns:
            搜索结果列表
        """
        if not self._initialized:
            debug_logger.log_warning('CogneeMemoryManager', 'Cognee 未初始化，返回空结果')
            return []
        
        try:
            # 如果指定了记忆类型，添加到查询中
            search_query = query
            if memory_type:
                search_query = f"[{memory_type}] {query}"
            
            # 执行搜索
            results = await self._cognee.search(search_query)
            
            # 格式化结果
            formatted_results = []
            for i, result in enumerate(results[:max_results]):
                formatted_results.append({
                    "index": i + 1,
                    "content": str(result),
                    # 相关度从 1.0 递减，每步 0.1，并在 0.0 处做下限裁剪，避免出现负数
                    "relevance": max(0.0, 1.0 - (i * 0.1))
                })
            
            debug_logger.log_info('CogneeMemoryManager', f'搜索完成: {query}', {
                'results_count': len(formatted_results)
            })
            
            return formatted_results
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'搜索失败: {str(e)}', e)
            return []
    
    async def search_conversations(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """搜索对话记忆"""
        return await self.search(query, memory_type="conversation", max_results=max_results)
    
    async def search_knowledge(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """搜索知识记忆"""
        return await self.search(query, memory_type="knowledge", max_results=max_results)
    
    async def search_worldview(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """搜索世界观记忆"""
        return await self.search(query, memory_type="worldview", max_results=max_results)
    
    async def get_related_knowledge(
        self,
        entity_name: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        获取与实体相关的知识
        
        Args:
            entity_name: 实体名称
            max_results: 最大结果数量
            
        Returns:
            相关知识列表
        """
        if not self._initialized:
            return []
        
        try:
            query = f"关于 {entity_name} 的所有信息和关联"
            return await self.search(query, max_results=max_results)
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', 
                f'获取相关知识失败: {str(e)}', e)
            return []
    
    async def process_and_store(
        self,
        content: str,
        memory_type: str = "conversation",
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        一站式处理：添加内容并更新知识图谱
        
        Args:
            content: 要处理的内容
            memory_type: 记忆类型
            metadata: 附加元数据
            
        Returns:
            是否成功处理
        """
        try:
            # 添加内容
            if not await self.add_memory(content, memory_type, metadata):
                return False
            
            # 构建知识图谱
            if not await self.cognify():
                return False
            
            # 应用记忆算法
            await self.memify()
            
            return True
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', 
                f'一站式处理失败: {str(e)}', e)
            return False
    
    async def clear_all_memory(self) -> bool:
        """
        清空所有记忆
        
        Returns:
            是否成功清空
        """
        if not self._initialized:
            return False
        
        try:
            # Cognee 删除所有数据
            await self._cognee.prune.prune_data()
            await self._cognee.prune.prune_system(metadata=True)
            
            debug_logger.log_info('CogneeMemoryManager', '所有记忆已清空')
            print("✓ Cognee 记忆已清空")
            
            return True
            
        except Exception as e:
            debug_logger.log_error('CogneeMemoryManager', f'清空记忆失败: {str(e)}', e)
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆系统统计信息
        
        Returns:
            统计信息字典
        """
        return {
            "enabled": self.enabled,
            "initialized": self._initialized,
            "api_key_configured": bool(self.api_key),
            "backend": "cognee"
        }


# 同步包装器，方便在非异步环境中使用
class CogneeMemorySyncWrapper:
    """
    Cognee 记忆管理器的同步包装器
    在非异步环境中提供便捷的同步接口
    """
    
    def __init__(self, manager: CogneeMemoryManager = None):
        """
        初始化同步包装器
        
        Args:
            manager: CogneeMemoryManager 实例
        """
        self.manager = manager or CogneeMemoryManager()
    
    def _run_async(self, coro):
        """运行异步协程"""
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        return loop.run_until_complete(coro)
    
    def add_memory(self, content: str, memory_type: str = "conversation", 
                   metadata: Dict[str, Any] = None) -> bool:
        """同步添加记忆"""
        return self._run_async(self.manager.add_memory(content, memory_type, metadata))
    
    def add_conversation(self, messages: List[Dict[str, str]], 
                        session_id: str = None) -> bool:
        """同步添加对话"""
        return self._run_async(self.manager.add_conversation(messages, session_id))
    
    def add_knowledge(self, entity_name: str, knowledge_content: str,
                     knowledge_type: str = "fact", source: str = "conversation") -> bool:
        """同步添加知识"""
        return self._run_async(
            self.manager.add_knowledge(entity_name, knowledge_content, knowledge_type, source)
        )
    
    def add_worldview(self, worldview_content: str, category: str = "general") -> bool:
        """同步添加世界观"""
        return self._run_async(self.manager.add_worldview(worldview_content, category))
    
    def cognify(self) -> bool:
        """同步构建知识图谱"""
        return self._run_async(self.manager.cognify())
    
    def memify(self) -> bool:
        """同步应用记忆算法"""
        return self._run_async(self.manager.memify())
    
    def search(self, query: str, memory_type: str = None, 
               max_results: int = 10) -> List[Dict[str, Any]]:
        """同步搜索"""
        return self._run_async(self.manager.search(query, memory_type, max_results))
    
    def process_and_store(self, content: str, memory_type: str = "conversation",
                         metadata: Dict[str, Any] = None) -> bool:
        """同步一站式处理"""
        return self._run_async(self.manager.process_and_store(content, memory_type, metadata))
    
    def clear_all_memory(self) -> bool:
        """同步清空记忆"""
        return self._run_async(self.manager.clear_all_memory())
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return self.manager.get_statistics()


# 全局实例
_global_cognee_manager: Optional[CogneeMemoryManager] = None


def get_cognee_manager() -> CogneeMemoryManager:
    """
    获取全局 Cognee 记忆管理器实例（单例模式）
    
    Returns:
        CogneeMemoryManager 实例
    """
    global _global_cognee_manager
    if _global_cognee_manager is None:
        _global_cognee_manager = CogneeMemoryManager()
    return _global_cognee_manager


def get_cognee_sync_wrapper() -> CogneeMemorySyncWrapper:
    """
    获取 Cognee 同步包装器
    
    Returns:
        CogneeMemorySyncWrapper 实例
    """
    return CogneeMemorySyncWrapper(get_cognee_manager())


if __name__ == '__main__':
    print("=" * 60)
    print("Cognee 智能记忆管理器测试")
    print("=" * 60)
    
    async def test():
        manager = CogneeMemoryManager()
        
        print("\n统计信息:")
        stats = manager.get_statistics()
        print(f"  启用: {stats['enabled']}")
        print(f"  已初始化: {stats['initialized']}")
        print(f"  API密钥配置: {stats['api_key_configured']}")
        
        if manager._initialized:
            # 测试添加记忆
            print("\n测试添加对话...")
            await manager.add_conversation([
                {"role": "user", "content": "你好，我叫小明"},
                {"role": "assistant", "content": "你好小明！很高兴认识你"}
            ])
            
            # 测试添加知识
            print("测试添加知识...")
            await manager.add_knowledge("小明", "用户的名字是小明", "fact", "conversation")
            
            # 构建知识图谱
            print("构建知识图谱...")
            await manager.cognify()
            
            # 测试搜索
            print("测试搜索...")
            results = await manager.search("小明")
            print(f"找到 {len(results)} 条结果")
            for r in results:
                print(f"  - {r['content'][:50]}...")
    
    asyncio.run(test())
    print("\n✓ 测试完成")
