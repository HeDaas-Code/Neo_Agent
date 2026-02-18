"""
MemU记忆适配器模块

该模块封装了MemU框架（https://github.com/NevaMind-AI/memU），用于替代原有的基于LLM的自动记忆总结。
MemU提供了更高效的记忆管理机制，减少了长期运行的token成本。

MemU是一个为24/7主动智能体构建的记忆框架，能够持续捕获和理解用户意图，
即使没有命令，智能体也能判断用户即将做什么并自主行动。

致谢：
- MemU项目: https://github.com/NevaMind-AI/memU
- License: Apache 2.0

注意：本适配器使用MemU的PyPI版本(memu-py)，API可能与GitHub最新版本略有不同。
"""

import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv

try:
    from memu import MemuClient
    from memu.llm import OpenAIClient
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
    
    def __init__(self, api_key: str = None, model_name: str = None, base_url: str = None):
        """
        初始化MemU适配器
        
        Args:
            api_key: OpenAI API密钥或MemU API密钥
            model_name: 使用的模型名称（默认使用gpt-4o-mini）
            base_url: MemU API服务器地址（如果使用自部署服务）
        """
        self.enabled = MEMU_AVAILABLE
        self.api_key = api_key or os.getenv('OPENAI_API_KEY') or os.getenv('SILICONFLOW_API_KEY')
        self.model_name = model_name or os.getenv('MEMU_MODEL_NAME', 'gpt-4o-mini')
        
        # MemU API服务配置（支持自部署）
        self.memu_base_url = base_url or os.getenv('MEMU_API_URL', None)
        self.use_memu_api = self.memu_base_url is not None
        self.user_id = os.getenv('MEMU_USER_ID', 'neo_agent_user')
        self.agent_id = os.getenv('MEMU_AGENT_ID', 'neo_agent')
        
        self.llm_client = None
        self.memu_client = None
        
        if not self.enabled:
            print("✗ MemU功能未启用（库未安装）")
            return
            
        if not self.api_key:
            print("⚠ MemU API密钥未配置，功能已禁用")
            self.enabled = False
            return
        
        try:
            if self.use_memu_api:
                # 使用自部署的MemU API服务
                self.memu_client = MemuClient(
                    base_url=self.memu_base_url,
                    api_key=self.api_key
                )
                print(f"✓ MemU API客户端已创建（服务器: {self.memu_base_url}）")
            else:
                # 使用直接LLM客户端进行总结
                self.llm_client = OpenAIClient(
                    api_key=self.api_key,
                    base_url=os.getenv('OPENAI_API_BASE', None),
                    model=self.model_name
                )
                print(f"✓ MemU LLM客户端已创建（模型: {self.model_name}）")
        except Exception as e:
            print(f"⚠ MemU客户端创建失败: {e}")
            self.enabled = False
    
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
            if self.use_memu_api and self.memu_client:
                # 使用MemU API服务生成总结
                return self._generate_summary_via_api(messages)
            elif self.llm_client:
                # 使用直接LLM客户端生成总结
                return self._generate_summary_via_llm(messages)
            else:
                return None
            
        except Exception as e:
            print(f"✗ MemU生成概括时出错: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _generate_summary_via_api(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        通过MemU API服务生成总结
        
        Args:
            messages: 对话消息列表
            
        Returns:
            概括文本
        """
        try:
            # 构建对话文本用于请求
            last_message = messages[-1]['content'] if messages else "总结对话"
            
            # 调用MemU API的chat接口（会自动记忆和总结）
            response = self.memu_client.chat(
                user_id=self.user_id,
                agent_id=self.agent_id,
                message=f"请总结以下对话的主题：共{len(messages)}条消息",
                system="你是一个专业的对话分析助手，擅长总结对话主题。",
                model=self.model_name
            )
            
            if response and hasattr(response, 'message'):
                return response.message.strip()
            elif isinstance(response, dict) and 'message' in response:
                return response['message'].strip()
            else:
                print(f"✗ MemU API返回了意外的响应格式: {type(response)}")
                return None
                
        except Exception as e:
            print(f"✗ 通过MemU API生成总结失败: {e}")
            return None
    
    def _generate_summary_via_llm(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        通过直接LLM客户端生成总结
        
        Args:
            messages: 对话消息列表
            
        Returns:
            概括文本
        """
        try:
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                role_name = "用户" if msg['role'] == 'user' else "助手"
                conversation_text += f"{role_name}: {msg['content']}\n"
            
            # 构建总结提示
            summary_prompt = f"""请对以下对话进行主题概括，要求：
1. 用一句话总结对话的主要主题和内容
2. 提炼关键信息和讨论要点
3. 简洁明了，不超过100字
4. 只返回概括内容，不要有其他说明

对话内容：
{conversation_text}

请给出主题概括："""
            
            # 使用LLM生成总结
            response = self.llm_client.chat(
                messages=[
                    {"role": "system", "content": "你是一个专业的对话分析助手，擅长总结对话主题。"},
                    {"role": "user", "content": summary_prompt}
                ],
                temperature=0.3,
                max_tokens=200
            )
            
            if response and hasattr(response, 'content'):
                summary = response.content.strip()
                return summary
            elif isinstance(response, dict) and 'content' in response:
                summary = response['content'].strip()
                return summary
            else:
                print(f"✗ MemU LLM返回了意外的响应格式: {type(response)}")
                return None
                
        except Exception as e:
            print(f"✗ 通过LLM生成总结失败: {e}")
            return None
    
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取MemU系统状态信息
        
        Returns:
            包含状态信息的字典
        """
        status = {
            'enabled': self.enabled,
            'api_configured': self.api_key is not None,
            'mode': 'API服务' if self.use_memu_api else 'LLM客户端',
            'model': self.model_name,
            'api_url': self.memu_base_url if self.use_memu_api else 'N/A',
            'user_id': self.user_id if self.use_memu_api else 'N/A',
            'agent_id': self.agent_id if self.use_memu_api else 'N/A',
        }
        return status
    
    def get_context_for_chat(self) -> str:
        """
        获取用于聊天的上下文（从MemU记忆中提取）
        
        注意：当前实现返回空字符串，因为MemU会在检索时自动提供上下文。
        此方法保留用于未来扩展。
        
        Returns:
            格式化的上下文字符串
        """
        if not self.enabled:
            return ""
        
        # MemU会在检索时自动提供上下文
        # 这里返回空字符串，因为上下文会在实际对话时注入
        return ""


# 为了向后兼容，提供一个简单的测试函数
def test_memu_adapter():
    """测试MemU适配器"""
    print("=" * 60)
    print("MemU适配器测试")
    print("=" * 60)
    
    if not MEMU_AVAILABLE:
        print("✗ MemU未安装，无法测试")
        return
    
    adapter = MemUAdapter()
    
    if not adapter.enabled:
        print("✗ MemU未启用，无法测试")
        return
    
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
    test_memu_adapter()

