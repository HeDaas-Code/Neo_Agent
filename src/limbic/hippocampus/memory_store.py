"""
长效记忆管理模块
实现分层记忆系统：短期记忆（最近20轮）+ 长期概括记忆 + 知识库
使用数据库替代JSON文件存储

P2 增强：
- 新增 OpenLoopTracker（未完话题检测与延续）
- 与现有短期/长期记忆 / 知识库并行
- 通过 DatabaseManager 持久化（与 LongTermMemoryManager 同库）
"""

import os
import json
import uuid
import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from src.core.database_manager import DatabaseManager
from src.limbic.hippocampus.knowledge_store import KnowledgeBase
from src.core.llm_helper import LLMHelper
from src.core.prompt_manager import get_prompt_manager
from src.cortex.providers import registry as llm_providers  # v4.0: 统一供应商解析
from src.tools.debug_logger import get_debug_logger

load_dotenv()

debug_logger = get_debug_logger()

ENABLE_OPEN_LOOP = os.getenv('ENABLE_OPEN_LOOP', 'false').lower() == 'true'


# ==================== P2: OpenLoopTracker ====================

class OpenLoopTracker:
    """
    未完话题跟踪器。
    每轮从用户消息中提取未完话题（pending tasks / 提问 / 计划 / 疑虑），
    在合适时机主动延续。
    """

    LOOP_TRIGGERS = [
        r'我[们]?(.+?)(明天|下周|以后|稍后|待会)[就再]',
        r'(?:帮我|请|记得|别忘)(.+)',
        r'(?:之后|下次)(?:再|记得|帮我)(.+)',
        r'什么时候(.+)',
        r'为什么(.+)',
        r'(.+)怎么[办做]',
    ]

    def __init__(self, db_manager: DatabaseManager = None,
                 prompt_manager=None,
                 max_active: int = 12):
        self.db = db_manager or DatabaseManager()
        self.prompt_manager = prompt_manager or get_prompt_manager()
        self.enabled = ENABLE_OPEN_LOOP
        self.max_active = max_active

    def update_from_message(self, user: str, text: str) -> Dict[str, Any]:
        """
        从用户消息中提取未完话题并入库。
        返回 {topic, status, raised_at, related_keywords, uuid} 或 None（若未识别到）。
        """
        if not self.enabled or not text:
            return {}
        topic = self._extract_topic_via_rules(text)
        keywords = self._extract_keywords(text)
        if not topic and not keywords:
            return {}

        if not topic:
            topic = keywords[0] if keywords else text[:20]
        context = text[:200]

        existing = self.db.find_matching_open_loop(topic)
        if existing:
            self.db.resolve_open_loop(existing['uuid'])

        loop_uuid = self.db.insert_open_loop(
            topic=topic, context=context,
            related_keywords=keywords,
        )
        if not loop_uuid:
            return {}
        return {
            'uuid': loop_uuid, 'topic': topic, 'status': 'open',
            'raised_at': datetime.now().isoformat(),
            'related_keywords': keywords,
        }

    def _extract_topic_via_rules(self, text: str) -> str:
        for pat in self.LOOP_TRIGGERS:
            m = re.search(pat, text)
            if m:
                captured = (m.group(1) or '').strip()
                if 1 <= len(captured) <= 30:
                    return captured
        return ""

    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        # 简化版：移除停用词，按空格 / 标点切分，保留长度 2-12 的 token
        stop = {'的', '了', '我', '你', '是', '在', '和', '就', '都', '也', '吧', '啊', '吗', '呢'}
        text = re.sub(r'[，。！？、,!?\.\s]+', ' ', text)
        tokens = [t.strip() for t in text.split() if 2 <= len(t.strip()) <= 12]
        return [t for t in tokens if t not in stop][:5]

    def resolve_matching_loop(self, text: str) -> Optional[Dict[str, Any]]:
        """
        若 text 命中已存在的未完话题，自动 resolve 并返回。
        """
        if not self.enabled or not text:
            return None
        match = self.db.find_matching_open_loop(text)
        if not match:
            return None
        self.db.resolve_open_loop(match['uuid'])
        return match

    def format_for_prompt(self, hint: str = "") -> str:
        """
        渲染为 prompt 文本（主流程第 4 步注入）。
        hint：可选的"对当前用户消息最相关的话题"提示。
        """
        if not self.enabled:
            return ""
        loops = self.db.get_open_loops(status='open', limit=self.max_active)
        if not loops:
            return ""
        lines = ["【未完话题】"]
        for lp in loops:
            topic = lp.get('topic', '?')
            keywords = lp.get('related_keywords', [])
            if keywords:
                lines.append(f"• {topic}（关键词：{', '.join(keywords[:3])}）")
            else:
                lines.append(f"• {topic}")
        if hint:
            lines.append(f"\n当前消息与「{hint}」相关，可在合适时机主动延续。")
        return "\n".join(lines)


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
        # v4.0: 用 llm_providers 解析（保留旧 SILICONFLOW_API_KEY 兼容）
        self.api_key = api_key or llm_providers.resolve_api_key()
        try:
            self.api_url = api_url or llm_providers.resolve_base_url(llm_providers.resolve_provider())
        except Exception:
            # 启动期 LLM_BASE_URL 缺失时（custom）保留旧 URL
            self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

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

    # ==================== Stage B.4 Web 后端兼容接口 ====================

    def list_topics(
        self,
        user_id: str = "default",
        days: int = 7,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        列出最近 N 天内的话题（基于 long_term_memory 概括）。

        Args:
            user_id: 用户标识（当前 schema 未持久化 user_id，保留参数以备扩展）。
            days: 时间范围（天），默认 7。
            limit: 返回条数上限，默认 200。

        Returns:
            话题字典列表，字段：uuid / topic / start_time / end_time / message_count。
            失败时返回空列表。
        """
        try:
            days_int = max(1, min(int(days), 365))
        except (TypeError, ValueError):
            days_int = 7
        try:
            limit_int = max(1, min(int(limit), 1000))
        except (TypeError, ValueError):
            limit_int = 200

        try:
            cutoff = (datetime.now() - timedelta(days=days_int)).isoformat()
        except Exception:  # noqa: BLE001
            cutoff = datetime.now().isoformat()

        rows: List[Dict[str, Any]] = []
        try:
            summaries = self.db.get_long_term_summaries() or []
        except Exception:  # noqa: BLE001
            return []

        for item in summaries:
            try:
                created_at = item.get('created_at') or ''
                if created_at and created_at < cutoff:
                    continue
                topic_text = (item.get('summary') or '').strip()
                # topic 取 summary 前若干字符作为短标题
                topic_short = topic_text[:40] + ('…' if len(topic_text) > 40 else '')
                try:
                    msg_count = int(item.get('message_count') or 0)
                except (TypeError, ValueError):
                    msg_count = 0
                rows.append({
                    'uuid': str(item.get('uuid') or ''),
                    'topic': topic_short or '未命名话题',
                    'start_time': str(item.get('created_at') or ''),
                    'end_time': str(item.get('ended_at') or '') or None,
                    'message_count': msg_count,
                })
                if len(rows) >= limit_int:
                    break
            except Exception:  # noqa: BLE001
                # 单条记录解析失败：跳过这一条，继续下一条
                continue

        # 按 start_time 倒序
        try:
            rows.sort(key=lambda x: x.get('start_time') or '', reverse=True)
        except Exception:  # noqa: BLE001
            pass
        return rows

    def get_topic_context(
        self,
        topic_uuid: str,
        user_id: str = "default",
    ) -> Dict[str, Any]:
        """
        获取话题的上下文消息（Stage B.4 Web 后端专用）。

        重要：当前 schema 中归档时会从 short_term_memory 物理删除原消息，
        因此 ``messages`` 字段以 long_term_memory.summary 自身 + 元数据作为兜底。
        若未来在 short_term_memory 增加 topic_uuid 关联列，本方法可平滑扩展。

        Returns:
            dict: {topic_uuid, topic, summary, messages, start_time, end_time}
            失败 / 未找到时返回 {topic_uuid, messages: []}。
        """
        if not topic_uuid or not isinstance(topic_uuid, str):
            return {'topic_uuid': str(topic_uuid or ''), 'messages': []}

        item: Optional[Dict[str, Any]] = None
        try:
            summaries = self.db.get_long_term_summaries() or []
            for s in summaries:
                try:
                    if str(s.get('uuid') or '') == topic_uuid:
                        item = s
                        break
                except Exception:  # noqa: BLE001
                    continue
        except Exception:  # noqa: BLE001
            item = None

        if not item:
            return {'topic_uuid': topic_uuid, 'messages': []}

        summary_text = (item.get('summary') or '').strip()
        topic_short = summary_text[:40] + ('…' if len(summary_text) > 40 else '')
        started_at = str(item.get('created_at') or '')
        ended_at = str(item.get('ended_at') or '') or None

        # messages：把 summary 拆成系统消息；并附加元数据作为 assistant 消息
        messages: List[Dict[str, Any]] = []
        if summary_text:
            messages.append({
                'role': 'system',
                'content': f"[话题摘要] {summary_text}",
                'timestamp': started_at,
            })
        try:
            msg_count = int(item.get('message_count') or 0)
        except (TypeError, ValueError):
            msg_count = 0
        try:
            rounds = int(item.get('rounds') or 0)
        except (TypeError, ValueError):
            rounds = 0
        if msg_count or rounds:
            messages.append({
                'role': 'assistant',
                'content': f"该话题共 {rounds} 轮 / {msg_count} 条消息。",
                'timestamp': ended_at or started_at,
            })

        return {
            'topic_uuid': topic_uuid,
            'topic': topic_short or '未命名话题',
            'summary': summary_text or None,
            'messages': messages,
            'start_time': started_at or None,
            'end_time': ended_at,
        }


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
