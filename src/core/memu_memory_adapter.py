"""
MemU记忆适配器模块

该模块封装了MemU框架（https://github.com/NevaMind-AI/memU），用于替代原有的基于LLM的自动记忆总结。
MemU提供了更高效的记忆管理机制，减少了长期运行的token成本。

MemU是一个为24/7主动智能体构建的记忆框架，能够持续捕获和理解用户意图，
即使没有命令，智能体也能判断用户即将做什么并自主行动。

致谢：
- MemU项目: https://github.com/NevaMind-AI/memU
- License: Apache 2.0
"""

import os
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

try:
    from memu.app import MemoryService
    MEMU_AVAILABLE = True
except ImportError:
    MEMU_AVAILABLE = False
    print("⚠ MemU未安装，将使用传统LLM总结方式")

load_dotenv()


class MemUAdapter:
    """
    MemU记忆适配器
    
    将MemU的记忆管理功能适配到Neo_Agent的记忆系统中。
    提供与原有长期记忆管理器兼容的接口。
    """
    
    def __init__(self, api_key: str = None, model_name: str = None):
        """
        初始化MemU适配器
        
        Args:
            api_key: OpenAI API密钥（MemU默认使用OpenAI）
            model_name: 使用的模型名称（默认使用gpt-4o-mini）
        """
        self.enabled = MEMU_AVAILABLE
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('SILICONFLOW_API_KEY')
        self.model_name = model_name or os.getenv('MEMU_MODEL_NAME', 'gpt-4o-mini')
        
        self.service = None
        self._initialized = False
        
        if not self.enabled:
            print("✗ MemU功能未启用（库未安装）")
            return
            
        if not self.api_key:
            print("⚠ MemU API密钥未配置，将在需要时提示")
            
        print(f"✓ MemU适配器已创建（模型: {self.model_name}）")
    
    async def _ensure_initialized(self):
        """确保MemU服务已初始化"""
        if self._initialized or not self.enabled:
            return
            
        if not self.api_key:
            raise ValueError("MemU需要API密钥。请设置OPENAI_API_KEY或SILICONFLOW_API_KEY环境变量")
        
        try:
            # 初始化MemU服务
            self.service = MemoryService(
                llm_profiles={
                    "default": {
                        "api_key": self.api_key,
                        "chat_model": self.model_name,
                    }
                },
                memorize_config={
                    "memory_categories": [
                        {
                            "name": "对话主题",
                            "description": "用户与助手之间的对话主题和内容概括"
                        },
                        {
                            "name": "用户偏好",
                            "description": "用户的喜好、习惯和个人特征"
                        }
                    ]
                }
            )
            self._initialized = True
            print("✓ MemU服务已初始化")
        except Exception as e:
            print(f"✗ MemU服务初始化失败: {e}")
            self.enabled = False
            raise
    
    def _sync_call(self, coro):
        """同步调用异步函数的辅助方法"""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已在运行，创建新任务
                return asyncio.create_task(coro)
            else:
                return loop.run_until_complete(coro)
        except RuntimeError:
            # 如果没有事件循环，创建新的
            return asyncio.run(coro)
    
    def generate_summary(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        使用MemU生成对话概括
        
        Args:
            messages: 对话消息列表，每条消息包含role和content
            
        Returns:
            概括文本，失败返回None
        """
        if not self.enabled:
            return None
        
        try:
            # 启动异步任务生成概括
            result = self._sync_call(self._generate_summary_async(messages))
            return result
        except Exception as e:
            print(f"✗ MemU生成概括时出错: {e}")
            return None
    
    async def _generate_summary_async(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        异步生成对话概括
        
        Args:
            messages: 对话消息列表
            
        Returns:
            概括文本
        """
        await self._ensure_initialized()
        
        if not self.service:
            return None
        
        try:
            # 将消息转换为MemU的对话格式
            conversation = []
            for msg in messages:
                conversation.append({
                    "role": msg['role'],
                    "content": msg['content']
                })
            
            # 使用MemU记忆化对话
            # 这会自动提取记忆并生成摘要
            result = await self.service.memorize(
                resource_data=conversation,
                modality="conversation"
            )
            
            # 从结果中提取摘要
            items = result.get("items", [])
            categories = result.get("categories", [])
            
            # 构建概括文本
            summary_parts = []
            
            # 从类别中提取摘要
            for cat in categories:
                if cat.get("summary"):
                    summary_parts.append(cat["summary"].strip())
            
            # 从记忆项中提取关键信息
            if items and len(items) > 0:
                for item in items[:3]:  # 只取前3个关键项
                    if item.get("summary"):
                        summary_parts.append(item["summary"].strip())
            
            if summary_parts:
                # 合并多个摘要部分
                summary = "; ".join(summary_parts)
                return summary[:200]  # 限制长度
            
            # 如果没有生成摘要，返回默认文本
            return f"对话记录 ({len(messages)} 条消息)"
            
        except Exception as e:
            print(f"✗ MemU异步生成概括出错: {e}")
            return None
    
    async def retrieve_relevant_memories(self, query: str, max_items: int = 5) -> List[Dict[str, Any]]:
        """
        检索与查询相关的记忆
        
        Args:
            query: 查询文本
            max_items: 返回的最大记忆数量
            
        Returns:
            相关记忆列表
        """
        await self._ensure_initialized()
        
        if not self.service:
            return []
        
        try:
            # 使用MemU检索相关记忆
            result = await self.service.retrieve(
                queries=[{"role": "user", "content": query}]
            )
            
            items = result.get("items", [])
            return items[:max_items]
            
        except Exception as e:
            print(f"✗ MemU检索记忆出错: {e}")
            return []
    
    def get_context_for_chat(self) -> str:
        """
        获取用于聊天的上下文（从MemU记忆中提取）
        
        Returns:
            格式化的上下文字符串
        """
        if not self.enabled or not self._initialized:
            return ""
        
        try:
            # 这是一个同步方法，但需要调用异步函数
            # 我们可以在这里返回空字符串，因为MemU会在检索时自动提供上下文
            return ""
        except Exception as e:
            print(f"✗ MemU获取上下文出错: {e}")
            return ""


# 为了向后兼容，提供一个简单的测试函数
async def test_memu_adapter():
    """测试MemU适配器"""
    print("=" * 60)
    print("MemU适配器测试")
    print("=" * 60)
    
    if not MEMU_AVAILABLE:
        print("✗ MemU未安装，无法测试")
        return
    
    adapter = MemUAdapter()
    
    # 测试消息
    test_messages = [
        {"role": "user", "content": "你好，我是小明"},
        {"role": "assistant", "content": "你好小明！很高兴认识你"},
        {"role": "user", "content": "我喜欢编程，尤其是Python"},
        {"role": "assistant", "content": "Python是一门很棒的语言！你都用Python做些什么项目呢？"}
    ]
    
    print("\n测试生成概括...")
    summary = adapter.generate_summary(test_messages)
    if summary:
        print(f"✓ 概括: {summary}")
    else:
        print("✗ 未能生成概括")
    
    print("\n✓ 测试完成")


if __name__ == '__main__':
    # 运行测试
    asyncio.run(test_memu_adapter())
