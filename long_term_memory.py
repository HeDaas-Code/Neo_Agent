"""
长效记忆管理模块
实现分层记忆系统：短期记忆（最近20轮）+ 长期概括记忆
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

load_dotenv()


class LongTermMemoryManager:
    """
    长效记忆管理器
    负责管理短期详细记忆和长期概括记忆的分层存储
    """

    def __init__(self,
                 short_term_file: str = None,
                 long_term_file: str = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化长效记忆管理器

        Args:
            short_term_file: 短期记忆文件路径（默认memory_data.json）
            long_term_file: 长期记忆文件路径（默认longmemory_data.json）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 文件路径配置
        self.short_term_file = short_term_file or os.getenv('MEMORY_FILE', 'memory_data.json')
        self.long_term_file = long_term_file or 'longmemory_data.json'

        # 短期记忆最大轮数（一轮 = 一对user+assistant消息）
        self.max_short_term_rounds = 20
        self.max_short_term_messages = self.max_short_term_rounds * 2  # user + assistant

        # API配置（用于生成概括）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 记忆数据
        self.short_term_messages: List[Dict[str, Any]] = []
        self.short_term_metadata: Dict[str, Any] = {}
        self.long_term_summaries: List[Dict[str, Any]] = []
        self.long_term_metadata: Dict[str, Any] = {}

        # 加载现有记忆
        self.load_all_memory()

    def load_all_memory(self):
        """
        加载所有记忆（短期和长期）
        """
        self._load_short_term_memory()
        self._load_long_term_memory()

    def _load_short_term_memory(self):
        """
        从文件加载短期记忆
        """
        try:
            if os.path.exists(self.short_term_file):
                with open(self.short_term_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.short_term_messages = data.get('messages', [])
                    self.short_term_metadata = data.get('metadata', {})
                    print(f"✓ 成功加载短期记忆: {len(self.short_term_messages)} 条消息")
            else:
                print("○ 未找到短期记忆文件，创建新的记忆")
                self.short_term_messages = []
                self.short_term_metadata = {
                    'created_at': datetime.now().isoformat(),
                    'total_conversations': 0
                }
        except Exception as e:
            print(f"✗ 加载短期记忆时出错: {e}")
            self.short_term_messages = []
            self.short_term_metadata = {}

    def _load_long_term_memory(self):
        """
        从文件加载长期概括记忆
        """
        try:
            if os.path.exists(self.long_term_file):
                with open(self.long_term_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.long_term_summaries = data.get('summaries', [])
                    self.long_term_metadata = data.get('metadata', {})
                    print(f"✓ 成功加载长期记忆: {len(self.long_term_summaries)} 个主题概括")
            else:
                print("○ 未找到长期记忆文件，创建新的记忆")
                self.long_term_summaries = []
                self.long_term_metadata = {
                    'created_at': datetime.now().isoformat(),
                    'total_summaries': 0
                }
        except Exception as e:
            print(f"✗ 加载长期记忆时出错: {e}")
            self.long_term_summaries = []
            self.long_term_metadata = {}

    def _save_short_term_memory(self):
        """
        保存短期记忆到文件
        """
        try:
            data = {
                'messages': self.short_term_messages,
                'metadata': self.short_term_metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.short_term_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 短期记忆已保存: {len(self.short_term_messages)} 条消息")
        except Exception as e:
            print(f"✗ 保存短期记忆时出错: {e}")

    def _save_long_term_memory(self):
        """
        保存长期记忆到文件
        """
        try:
            data = {
                'summaries': self.long_term_summaries,
                'metadata': self.long_term_metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.long_term_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 长期记忆已保存: {len(self.long_term_summaries)} 个概括")
        except Exception as e:
            print(f"✗ 保存长期记忆时出错: {e}")

    def add_message(self, role: str, content: str):
        """
        添加新消息到短期记忆

        Args:
            role: 角色类型 ('user' 或 'assistant')
            content: 消息内容
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        self.short_term_messages.append(message)

        # 更新元数据
        if role == 'user':
            self.short_term_metadata['total_conversations'] = self.short_term_metadata.get('total_conversations', 0) + 1

        # 检查是否需要归档
        self._check_and_archive()

    def _check_and_archive(self):
        """
        检查短期记忆是否超过限制，如果超过则归档旧记忆
        """
        # 计算当前对话轮数
        user_count = sum(1 for msg in self.short_term_messages if msg['role'] == 'user')

        # 如果超过20轮，将最早的20轮归档
        if user_count > self.max_short_term_rounds:
            print(f"\n⚠ 短期记忆已达 {user_count} 轮，开始归档...")
            self._archive_old_messages()

    def _archive_old_messages(self):
        """
        将最早的20轮对话归档为概括记忆
        """
        # 找出前20轮对话（40条消息）
        messages_to_archive = []
        user_count = 0

        for msg in self.short_term_messages:
            messages_to_archive.append(msg)
            if msg['role'] == 'user':
                user_count += 1
                if user_count >= self.max_short_term_rounds:
                    break

        # 生成概括
        summary = self._generate_summary(messages_to_archive)

        if summary:
            # 创建长期记忆条目
            summary_entry = {
                'uuid': str(uuid.uuid4()),
                'created_at': messages_to_archive[0]['timestamp'] if messages_to_archive else datetime.now().isoformat(),
                'ended_at': messages_to_archive[-1]['timestamp'] if messages_to_archive else datetime.now().isoformat(),
                'rounds': user_count,
                'summary': summary,
                'message_count': len(messages_to_archive)
            }

            # 保存到长期记忆
            self.long_term_summaries.append(summary_entry)
            self.long_term_metadata['total_summaries'] = len(self.long_term_summaries)
            self._save_long_term_memory()

            # 从短期记忆中移除已归档的消息
            self.short_term_messages = self.short_term_messages[len(messages_to_archive):]
            self._save_short_term_memory()

            print(f"✓ 已归档 {user_count} 轮对话（{len(messages_to_archive)} 条消息）")
            print(f"✓ 生成主题概括: {summary[:50]}...")

    def _generate_summary(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        使用LLM生成对话概括

        Args:
            messages: 要概括的消息列表

        Returns:
            概括文本，失败返回None
        """
        try:
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                role_name = "用户" if msg['role'] == 'user' else "助手"
                conversation_text += f"{role_name}: {msg['content']}\n"

            # 构建概括请求
            summary_prompt = f"""请对以下对话进行主题概括，要求：
1. 用一句话总结对话的主要主题和内容
2. 提炼关键信息和讨论要点
3. 简洁明了，不超过100字
4. 只返回概括内容，不要有其他说明

对话内容：
{conversation_text}

请给出主题概括："""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的对话分析助手，擅长总结对话主题。'},
                    {'role': 'user', 'content': summary_prompt}
                ],
                'temperature': 0.3,  # 使用较低温度以获得更稳定的概括
                'max_tokens': 200,
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
                summary = result['choices'][0]['message']['content'].strip()
                return summary
            else:
                print("✗ 未能获取有效的概括结果")
                return None

        except Exception as e:
            print(f"✗ 生成概括时出错: {e}")
            # 返回一个默认概括
            return f"对话记录 ({len(messages)} 条消息)"

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """
        获取最近的N条短期记忆消息

        Args:
            count: 要获取的消息数量

        Returns:
            消息列表
        """
        recent = self.short_term_messages[-count:] if len(self.short_term_messages) > count else self.short_term_messages
        return [{'role': msg['role'], 'content': msg['content']} for msg in recent]

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """
        获取所有长期记忆概括

        Returns:
            概括列表
        """
        return self.long_term_summaries

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            统计信息字典
        """
        short_user = sum(1 for msg in self.short_term_messages if msg['role'] == 'user')
        short_assistant = sum(1 for msg in self.short_term_messages if msg['role'] == 'assistant')

        return {
            'short_term': {
                'total_messages': len(self.short_term_messages),
                'user_messages': short_user,
                'assistant_messages': short_assistant,
                'rounds': short_user,
                'file': self.short_term_file
            },
            'long_term': {
                'total_summaries': len(self.long_term_summaries),
                'total_archived_rounds': sum(s.get('rounds', 0) for s in self.long_term_summaries),
                'total_archived_messages': sum(s.get('message_count', 0) for s in self.long_term_summaries),
                'file': self.long_term_file
            },
            'total_conversations': self.short_term_metadata.get('total_conversations', 0),
            'created_at': self.short_term_metadata.get('created_at', 'Unknown')
        }

    def clear_all_memory(self):
        """
        清空所有记忆（短期和长期）
        """
        self.short_term_messages = []
        self.short_term_metadata = {
            'created_at': datetime.now().isoformat(),
            'total_conversations': 0
        }
        self.long_term_summaries = []
        self.long_term_metadata = {
            'created_at': datetime.now().isoformat(),
            'total_summaries': 0
        }
        self._save_short_term_memory()
        self._save_long_term_memory()
        print("✓ 所有记忆已清空")

    def save_all_memory(self):
        """
        保存所有记忆
        """
        self._save_short_term_memory()
        self._save_long_term_memory()

    def get_context_for_chat(self, recent_count: int = 10) -> str:
        """
        获取用于聊天的上下文（包含长期记忆概括和短期记忆）

        Args:
            recent_count: 最近消息数量

        Returns:
            格式化的上下文字符串
        """
        context_parts = []

        # 添加长期记忆概括（如果有）
        if self.long_term_summaries:
            context_parts.append("【历史对话主题回顾】")
            for i, summary in enumerate(self.long_term_summaries[-5:], 1):  # 只取最近5个概括
                context_parts.append(f"{i}. {summary['summary']}")
            context_parts.append("")

        return "\n".join(context_parts) if context_parts else ""


if __name__ == '__main__':
    print("=" * 60)
    print("长效记忆管理器测试")
    print("=" * 60)

    manager = LongTermMemoryManager()

    print("\n当前记忆统计:")
    stats = manager.get_statistics()
    print(f"短期记忆: {stats['short_term']['rounds']} 轮对话")
    print(f"长期记忆: {stats['long_term']['total_summaries']} 个主题概括")

    if manager.long_term_summaries:
        print("\n长期记忆概括:")
        for i, summary in enumerate(manager.long_term_summaries, 1):
            print(f"{i}. [{summary['created_at'][:10]}] {summary['summary']}")

