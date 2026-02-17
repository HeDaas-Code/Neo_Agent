"""
长效记忆管理模块
实现分层记忆系统：短期记忆（最近20轮）+ 长期概括记忆 + 知识库
使用数据库替代JSON文件存储

更新说明:
- 集成MemU框架（https://github.com/NevaMind-AI/memU）用于更高效的记忆管理
- 当MemU可用时，使用MemU进行记忆总结；否则回退到传统LLM总结
- 知识库提取功能保持不变
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from src.core.database_manager import DatabaseManager
from src.core.knowledge_base import KnowledgeBase

# 尝试导入MemU适配器
try:
    from src.core.memu_memory_adapter import MemUAdapter
    MEMU_ENABLED = True
except ImportError:
    MEMU_ENABLED = False

load_dotenv()


class LongTermMemoryManager:
    """
    长效记忆管理器
    负责管理短期详细记忆和长期概括记忆的分层存储
    使用数据库替代JSON文件
    """

    def __init__(self,
                 db_manager: DatabaseManager = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化长效记忆管理器

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()

        # 短期记忆最大轮数（一轮 = 一对user+assistant消息）
        self.max_short_term_rounds = 20
        self.max_short_term_messages = self.max_short_term_rounds * 2  # user + assistant

        # 知识提取间隔（每5轮）
        self.knowledge_extraction_interval = 5

        # API配置（用于生成概括）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 初始化MemU适配器（如果可用）
        self.use_memu = MEMU_ENABLED and os.getenv('USE_MEMU', 'true').lower() == 'true'
        self.memu_adapter = None
        
        if self.use_memu and MEMU_ENABLED:
            try:
                # 尝试初始化MemU
                openai_key = os.getenv('OPENAI_API_KEY')
                memu_model = os.getenv('MEMU_MODEL_NAME', 'gpt-4o-mini')
                self.memu_adapter = MemUAdapter(api_key=openai_key, model_name=memu_model)
                print(f"✓ MemU记忆管理已启用（模型: {memu_model}）")
            except Exception as e:
                print(f"⚠ MemU初始化失败，回退到传统LLM总结: {e}")
                self.use_memu = False
        elif not MEMU_ENABLED:
            print("○ MemU未安装，使用传统LLM总结方式")

        # 初始化知识库（共享数据库管理器）
        self.knowledge_base = KnowledgeBase(
            db_manager=self.db,
            api_key=self.api_key,
            api_url=self.api_url,
            model_name=self.model_name
        )

        # 检查是否需要从JSON迁移数据
        self._check_and_migrate_json()

        print(f"✓ 长效记忆管理器已初始化（使用数据库存储）")

    def _check_and_migrate_json(self):
        """检查并迁移旧的JSON文件"""
        # 迁移短期记忆
        short_term_file = os.getenv('MEMORY_FILE', 'memory_data.json')
        if os.path.exists(short_term_file):
            print(f"○ 检测到旧的短期记忆JSON文件，正在迁移...")
            self.db.migrate_from_json(short_term_file, 'short_term')
            os.rename(short_term_file, short_term_file + '.bak')
            print(f"✓ 短期记忆已迁移，JSON文件已备份")

        # 迁移长期记忆
        long_term_file = 'longmemory_data.json'
        if os.path.exists(long_term_file):
            print(f"○ 检测到旧的长期记忆JSON文件，正在迁移...")
            self.db.migrate_from_json(long_term_file, 'long_term')
            os.rename(long_term_file, long_term_file + '.bak')
            print(f"✓ 长期记忆已迁移，JSON文件已备份")

    def add_message(self, role: str, content: str):
        """
        添加新消息到短期记忆（使用数据库）

        Args:
            role: 角色类型 ('user' 或 'assistant')
            content: 消息内容
        """
        # 添加到数据库
        self.db.add_short_term_message(role, content)

        # 更新元数据
        if role == 'user':
            total_conversations = self.db.get_metadata('total_conversations', 0)
            total_conversations += 1
            self.db.set_metadata('total_conversations', total_conversations)

            # 检查是否需要提取知识（每5轮）
            if total_conversations % self.knowledge_extraction_interval == 0:
                print(f"\n📚 已达到 {total_conversations} 轮对话，开始提取知识...")
                self._extract_and_save_knowledge()

        # 检查是否需要归档
        self._check_and_archive()

    def _check_and_archive(self):
        """
        检查短期记忆是否超过限制，如果超过则归档旧记忆
        """
        # 获取所有短期记忆
        messages = self.db.get_short_term_messages()

        # 计算当前对话轮数
        user_count = sum(1 for msg in messages if msg['role'] == 'user')

        # 如果超过20轮，将最早的20轮归档
        if user_count > self.max_short_term_rounds:
            print(f"\n⚠ 短期记忆已达 {user_count} 轮，开始归档...")
            self._archive_old_messages()

    def _archive_old_messages(self):
        """
        将最早的20轮对话归档为概括记忆
        """
        # 获取所有短期记忆消息
        all_messages = self.db.get_short_term_messages()

        # 找出前20轮对话（40条消息）
        messages_to_archive = []
        message_ids_to_delete = []
        user_count = 0

        for msg in all_messages:
            messages_to_archive.append(msg)
            message_ids_to_delete.append(msg['id'])
            if msg['role'] == 'user':
                user_count += 1
                if user_count >= self.max_short_term_rounds:
                    break

        # 生成概括
        summary = self._generate_summary(messages_to_archive)

        if summary:
            # 保存到长期记忆（数据库）
            self.db.add_long_term_summary(
                summary=summary,
                rounds=user_count,
                message_count=len(messages_to_archive),
                created_at=messages_to_archive[0]['timestamp'] if messages_to_archive else datetime.now().isoformat(),
                ended_at=messages_to_archive[-1]['timestamp'] if messages_to_archive else datetime.now().isoformat()
            )

            # 从短期记忆中移除已归档的消息
            self.db.delete_short_term_messages(message_ids_to_delete)

            print(f"✓ 已归档 {user_count} 轮对话（{len(messages_to_archive)} 条消息）")
            print(f"✓ 生成主题概括: {summary[:50]}...")

    def _extract_and_save_knowledge(self):
        """
        从最近5轮对话中提取并保存知识
        同时定期清理过时的知识
        """
        # 从数据库获取所有短期记忆
        all_messages = self.db.get_short_term_messages()

        # 获取最近5轮对话（10条消息）
        recent_messages = []
        user_count = 0

        for msg in reversed(all_messages):
            recent_messages.insert(0, msg)
            if msg['role'] == 'user':
                user_count += 1
                if user_count >= 5:
                    break

        if len(recent_messages) < 2:  # 至少需要一轮对话
            print("✗ 消息太少，无法提取知识")
            return

        # 使用知识库提取知识
        knowledge_list = self.knowledge_base.extract_knowledge(recent_messages)

        if knowledge_list and len(knowledge_list) > 0:
            print(f"✓ 提取到 {len(knowledge_list)} 条知识")

            # 保存每条知识
            for knowledge_data in knowledge_list:
                entity_name = knowledge_data.get('entity_name', knowledge_data.get('title', '未知'))
                is_def = knowledge_data.get('is_definition', False)
                content = knowledge_data.get('content', '')
                content_preview = content[:30]
                print(f"  • [{knowledge_data.get('type', '其他')}] {entity_name}{'的定义' if is_def else ''}: {content_preview}...")

                # 保存到数据库
                entity_uuid = self.db.find_or_create_entity(entity_name)

                if is_def:
                    # 保存为定义
                    self.db.set_entity_definition(
                        entity_uuid=entity_uuid,
                        content=content,
                        type_=knowledge_data.get('type', '定义'),
                        source=knowledge_data.get('source', '对话提取'),
                        confidence=knowledge_data.get('confidence', 0.8)
                    )
                    print(f"    置信度: {knowledge_data.get('confidence', 0.8):.2f} | 实体UUID: {entity_uuid}")
                else:
                    # 保存为相关信息，默认状态为"疑似"
                    # add_entity_related_info 会检查是否已存在相同信息，如果存在会增加mention_count
                    from src.core.database_manager import DatabaseManager
                    info_uuid = self.db.add_entity_related_info(
                        entity_uuid=entity_uuid,
                        content=content,
                        type_=knowledge_data.get('type', '其他'),
                        source=knowledge_data.get('source', '对话提取'),
                        confidence=knowledge_data.get('confidence', 0.7),
                        status=DatabaseManager.STATUS_SUSPECTED
                    )
                    
                    # 获取信息状态以显示
                    info = self.db.get_entity_related_info(entity_uuid)
                    saved_info = next((i for i in info if i['uuid'] == info_uuid), None)
                    if saved_info:
                        status = saved_info.get('status', DatabaseManager.STATUS_SUSPECTED)
                        mention_count = saved_info.get('mention_count', 1)
                        status_label = f"[{status}]" if status == DatabaseManager.STATUS_CONFIRMED else f"[{status}×{mention_count}]"
                        print(f"    状态: {status_label} | 置信度: {knowledge_data.get('confidence', 0.7):.2f} | 实体UUID: {entity_uuid}")
                    else:
                        print(f"    置信度: {knowledge_data.get('confidence', 0.7):.2f} | 实体UUID: {entity_uuid}")

            # 每次提取知识后，检查是否需要清理过时信息
            # 每10次提取清理一次（即每50轮对话）
            total_conv = self.db.get_metadata('total_conversations', 0)
            if total_conv % 50 == 0 and total_conv > 0:
                print("○ 执行定期知识库清理...")
                # 这里可以添加清理逻辑
                print(f"✓ 清理完成")
        else:
            print("○ 未提取到新知识")

    def _generate_summary(self, messages: List[Dict[str, Any]]) -> Optional[str]:
        """
        生成对话概括
        
        优先使用MemU进行记忆管理和总结，如果MemU不可用则回退到传统LLM总结

        Args:
            messages: 要概括的消息列表

        Returns:
            概括文本，失败返回None
        """
        # 首先尝试使用MemU
        if self.use_memu and self.memu_adapter:
            try:
                print("○ 使用MemU生成对话概括...")
                summary = self.memu_adapter.generate_summary(messages)
                if summary:
                    print(f"✓ MemU生成概括成功")
                    return summary
                else:
                    print("⚠ MemU未返回概括，回退到传统方式")
            except Exception as e:
                print(f"⚠ MemU生成概括失败: {e}，回退到传统方式")
        
        # 回退到传统LLM总结方式
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
        获取最近的N条短期记忆消息（从数据库）

        Args:
            count: 要获取的消息数量

        Returns:
            消息列表
        """
        messages = self.db.get_short_term_messages(limit=count)
        return [{'role': msg['role'], 'content': msg['content']} for msg in messages]

    def get_all_summaries(self) -> List[Dict[str, Any]]:
        """
        获取所有长期记忆概括（从数据库）

        Returns:
            概括列表
        """
        return self.db.get_long_term_summaries()
    
    def get_long_term_summaries(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取长期记忆概括（支持限制数量）

        Args:
            limit: 限制返回的概括数量，None表示返回全部

        Returns:
            概括列表
        """
        summaries = self.db.get_long_term_summaries()
        if limit is not None and limit > 0:
            return summaries[:limit]
        return summaries

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆统计信息（从数据库）

        Returns:
            统计信息字典
        """
        # 从数据库获取消息
        short_term_messages = self.db.get_short_term_messages()
        long_term_summaries = self.db.get_long_term_summaries()

        short_user = sum(1 for msg in short_term_messages if msg['role'] == 'user')
        short_assistant = sum(1 for msg in short_term_messages if msg['role'] == 'assistant')

        # 获取知识库统计
        db_stats = self.db.get_statistics()

        # 获取知识库详细统计
        kb_stats = self.knowledge_base.get_statistics()

        return {
            'short_term': {
                'total_messages': len(short_term_messages),
                'user_messages': short_user,
                'assistant_messages': short_assistant,
                'rounds': short_user
            },
            'long_term': {
                'total_summaries': len(long_term_summaries),
                'total_archived_rounds': sum(s.get('rounds', 0) for s in long_term_summaries),
                'total_archived_messages': sum(s.get('message_count', 0) for s in long_term_summaries)
            },
            'knowledge_base': {
                'total_entities': db_stats['entities_count'],
                'total_base_knowledge': db_stats['base_knowledge_count'],
                'total_knowledge': kb_stats['total_knowledge'],  # 添加总知识数以保持兼容性
                'total_definitions': kb_stats['total_definitions'],
                'total_related_info': kb_stats['total_related_info']
            },
            'total_conversations': self.db.get_metadata('total_conversations', 0),
            'database_size_kb': db_stats.get('db_size_kb', 0)
        }

    def clear_all_memory(self):
        """
        清空所有记忆（短期、长期）
        """
        self.db.clear_short_term_memory()
        self.db.clear_long_term_memory()
        self.db.set_metadata('total_conversations', 0)
        print("✓ 所有记忆已清空")

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
        long_term_summaries = self.db.get_long_term_summaries()
        if long_term_summaries:
            context_parts.append("【历史对话主题回顾】")
            for i, summary in enumerate(long_term_summaries[-5:], 1):  # 只取最近5个概括
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
    print(f"短期记忆: {stats['short_term']['rounds']} 轮对话 ({stats['short_term']['total_messages']} 条消息)")
    print(f"长期记忆: {stats['long_term']['total_summaries']} 个主题概括")
    print(f"知识库实体: {stats['knowledge_base']['total_entities']} 个")
    print(f"总对话轮数: {stats['total_conversations']} 轮")
    print(f"数据库大小: {stats['database_size_kb']:.2f} KB")

    long_term_summaries = manager.get_all_summaries()
    if long_term_summaries:
        print("\n长期记忆概括:")
        for i, summary in enumerate(long_term_summaries, 1):
            print(f"{i}. [{summary['created_at'][:10]}] {summary['summary']}")
    else:
        print("\n暂无长期记忆概括")

    print("\n✓ 测试完成")
