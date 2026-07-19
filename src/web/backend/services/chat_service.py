"""
Chat service module.
聊天服务模块 - 包装 ChatAgent，提供 Web 后端的同步/异步入口。

Stage A.3: 同步接口
Stage B.2: 异步流式接口 (chat_stream 返回字符串，stream_chat 返回 ChatChunk)
Stage B.3 / B.4: 在流式回复完成时，向 EventService 派发 emotion_update / timeline_update
事件，供前端 /ws/events 订阅并刷新 EmotionPanel / TimelineCanvas。
v3.1.0: 注入 ChatSessionRepository 持久化钩子（user/assistant 消息入库 + emotion_json 异步更新）。
"""

from __future__ import annotations

import asyncio
import re
import sys
import warnings
from pathlib import Path
from typing import Any, AsyncIterator, Dict, Optional

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.version import __version__


# ----------------------------------------------------------------------
# 工具：检查方法签名是否接受某个 keyword 参数
# ----------------------------------------------------------------------
def _method_accepts_kwarg(method: Any, kwarg_name: str) -> bool:
    """
    检查 callable 是否在其签名中接受 ``kwarg_name``。

    用途：ChatService.chat_stream 在调用 agent.chat_stream 时做向后兼容检测
    —— 当 agent 仍是老式签名 (user_input, context=None) 时，避免
    TypeError: got an unexpected keyword argument 'cancel_event'。

    Returns:
        True 表示方法接受该 kwarg（或 **kwargs）；False 表示不接收。
    """
    try:
        import inspect  # 延迟导入，inspect 是标准库但避免无谓加载
        sig = inspect.signature(method)
    except (TypeError, ValueError):
        # 内置 / C 实现的方法可能无法 inspect；保守地当作不接受
        return False

    if any(p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()):
        return True  # 接受 **kwargs ⇒ 任何 kwarg 都 OK
    return kwarg_name in sig.parameters


class ChatService:
    """
    聊天服务（Web 后端侧）

    设计要点：
    1. 懒加载 ChatAgent：避免 Web 启动时强制初始化 LLM / DB
    2. try/except 保护：LLM 库缺失或配置错误时不阻断 Web 启动
    3. chat() 委托给 agent.chat()；chat_stream() 透传字符串 chunk；
       stream_chat() 在 Stage B.2 新增，包装 chat_stream 为 Pydantic ChatChunk
    4. 全局单例：chat_service = ChatService()
    """

    def __init__(self, agent: Optional[Any] = None) -> None:
        """
        初始化服务。

        Args:
            agent: 可选，预注入的 ChatAgent 实例。为 None 时延后到
                   get_agent() 调用时再尝试实例化。
        """
        self._agent: Optional[Any] = None

        # v3.1.0: 当前绑定会话（由 set_session_id() 注入）
        self._session_id: Optional[int] = None
        # v3.1.0: 刚写入的 assistant 消息 id（供 on_emotion 异步更新 emotion_json）
        self._last_assistant_message_id: Optional[int] = None

        if agent is not None:
            self._agent = agent
        else:
            # 尝试立即懒加载；若失败则保持 None
            self._try_init_agent()

    # ------------------------------------------------------------------
    # v3.1.0: 会话绑定
    # ------------------------------------------------------------------
    def set_session_id(self, session_id: Optional[int]) -> None:
        """
        显式绑定一个 session_id；之后 chat_stream 内会自动把 user/assistant
        消息写到该 session 下。

        传 None 时解绑。
        """
        if session_id is None:
            self._session_id = None
            return
        try:
            self._session_id = int(session_id)
        except (TypeError, ValueError):
            self._session_id = None

    def get_session_id(self) -> Optional[int]:
        """返回当前绑定的 session_id（可能为 None）。"""
        return self._session_id

    def _get_repo(self) -> Optional[Any]:
        """
        懒加载 ChatSessionRepository；DB 不可用时返回 None（不抛）。
        """
        try:
            from src.core.database_manager import DatabaseManager
            # 复用 agent 已建好的 db_manager，避免重复打开
            db_manager = None
            if self._agent is not None and hasattr(self._agent, "db"):
                db_manager = getattr(self._agent, "db", None)
            if db_manager is None:
                # 注意：保留模块全局单例避免每个 chat 一次新连接
                if not hasattr(self, "_db_singleton") or self._db_singleton is None:
                    self._db_singleton = DatabaseManager()
                db_manager = self._db_singleton
            return db_manager.get_chat_session_repository()
        except Exception:  # noqa: BLE001
            return None

    def on_emotion(self, emotion_payload: Optional[Dict[str, Any]]) -> None:
        """
        由 ws/chat.py 在 emotion_update 帧派发时调用；
        把情感数据写入最近一条 assistant 消息的 emotion_json 字段。
        """
        if not emotion_payload or self._last_assistant_message_id is None:
            return
        try:
            import json as _json
            repo = self._get_repo()
            if repo is None:
                return
            repo.update_message_emotion(
                self._last_assistant_message_id,
                _json.dumps(emotion_payload, ensure_ascii=False),
            )
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------
    # 内部：懒加载 ChatAgent
    # ------------------------------------------------------------------
    def _try_init_agent(self) -> None:
        """
        尝试实例化 ChatAgent，失败时记录 warning 并保持 _agent = None。

        设计意图：ChatAgent 初始化会创建 DatabaseManager / LongTermMemoryManager /
        SiliconFlowLLM / ProactiveEngine 等重型组件，依赖未安装或环境变量缺失时
        可能会抛异常。Web 端必须能在 ChatAgent 不可用时继续运行（健康检查等）。
        """
        try:
            from src.core.chat_agent import ChatAgent  # type: ignore

            self._agent = ChatAgent()
        except Exception as exc:  # noqa: BLE001
            warnings.warn(
                f"[ChatService] ChatAgent 初始化失败，将以无 agent 模式运行: {exc}",
                RuntimeWarning,
                stacklevel=2,
            )
            self._agent = None

    # ------------------------------------------------------------------
    # 同步入口
    # ------------------------------------------------------------------
    def get_agent(self) -> Any:
        """
        同步获取（必要时懒加载）ChatAgent 实例。

        Returns:
            ChatAgent 实例；若 LLM / DB 不可用则返回 None。
        """
        if self._agent is None:
            self._try_init_agent()
        return self._agent

    def set_agent(self, agent: Optional[Any]) -> None:
        """
        注入 agent（用于测试或自定义场景）。
        传入 None 时，重置为 lazy 模式，下次 get_agent() 时再尝试初始化。
        """
        self._agent = agent

    def chat(self, user_input: str, context: Optional[Dict] = None) -> str:
        """
        同步聊天入口。

        Args:
            user_input: 用户输入
            context: 可选上下文（不直接传给 agent，保留供未来扩展）

        Returns:
            完整回复文本

        Raises:
            RuntimeError: 当 agent 不可用时
        """
        agent = self.get_agent()
        if agent is None:
            raise RuntimeError(
                "ChatAgent not initialized. Check LLM / DB dependencies."
            )
        return agent.chat(user_input)

    # ------------------------------------------------------------------
    # 流式入口（Stage B.2 实现）
    # ------------------------------------------------------------------
    async def chat_stream(
        self,
        user_input: str,
        context: Optional[Dict] = None,
        cancel_event: Optional[Any] = None,
    ) -> AsyncIterator[str]:
        """
        流式聊天入口（字符串 chunk 透传）。

        降级策略（按优先级）：
        1. agent 可用且有 chat_stream → 委托给 agent.chat_stream(user_input, context=context, cancel_event=cancel_event)
        2. agent 可用但没有 chat_stream（或其失败） →
           loop.run_in_executor(None, agent.chat, user_input) 拿到完整回复后
           按"非空白词 + 尾部空白"切片模拟流式输出（40ms 间隔），
           每个 token 前检查 cancel_event.is_set() 实现早退
        3. agent 不可用 → yield 一次性回执 "[ChatAgent 不可用] 收到: {user_input}" 后退出

        Args:
            user_input: 用户输入
            context: 透传给 agent 的额外上下文（agent 不感知则忽略）
            cancel_event: 取消事件（透传给 agent；同步降级路径中在每片前检查）

        Yields:
            字符串 chunk；最坏情况下 yield 一次回执
        """
        # 取得 agent（可能为 None）
        try:
            agent = self.get_agent()
        except Exception as e:  # noqa: BLE001
            warnings.warn(
                f"[ChatService] get_agent 失败，按无 agent 处理: {e}",
                RuntimeWarning,
                stacklevel=2,
            )
            agent = None

        # ===== v3.1.0: 前置持久化 — 确保 session + 写 user 消息 =====
        # 1) 若 _session_id 仍空但 context 里有 session_id → 使用之
        if self._session_id is None and isinstance(context, dict):
            ctx_sid = context.get("session_id")
            if ctx_sid is not None:
                try:
                    self.set_session_id(int(ctx_sid))
                except (TypeError, ValueError):
                    pass
        # 2) 仍空 → 自动创建新 session（title 取 user_input 前 30 字）
        if self._session_id is None:
            try:
                repo = self._get_repo()
                if repo is not None:
                    initial_title = (user_input or "新会话")[:30] or "新会话"
                    new_sid = repo.create(user_id="default", title=initial_title)
                    if new_sid:
                        self._session_id = int(new_sid)
            except Exception:  # noqa: BLE001
                self._session_id = None
        # 3) 写 user 消息
        if self._session_id is not None:
            try:
                repo = self._get_repo()
                if repo is not None:
                    repo.add_message(self._session_id, "user", user_input or "")
                    self._last_assistant_message_id = None
            except Exception:  # noqa: BLE001
                pass

        # 收集 assistant 全文（用于流结束后持久化）
        collected_chunks: list[str] = []
        collect_failed = False

        # ===== 策略 1：委托给 agent.chat_stream =====
        if agent is not None and hasattr(agent, "chat_stream"):
            # 兼容性：仅当 agent 的 chat_stream 接受 cancel_event 时才透传
            _supports_cancel = _method_accepts_kwarg(agent.chat_stream, "cancel_event")
            _supports_user_id = _method_accepts_kwarg(agent.chat_stream, "user_id")
            try:
                kwargs: Dict[str, Any] = {"context": context}
                if _supports_cancel and cancel_event is not None:
                    kwargs["cancel_event"] = cancel_event
                if _supports_user_id:
                    kwargs["user_id"] = "default"
                async for chunk in agent.chat_stream(user_input, **kwargs):
                    collected_chunks.append(chunk or "")
                    yield chunk
            except asyncio.CancelledError:
                collect_failed = True
                raise
            except Exception as e:  # noqa: BLE001
                # agent.chat_stream 异常不向消费者直接抛；尝试降级到同步 chat()
                collect_failed = True
                warnings.warn(
                    f"[ChatService] agent.chat_stream 失败，降级到同步 chat(): {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
            else:
                # v3.1.0: 正常结束 → 持久化 assistant
                self._persist_assistant("".join(collected_chunks))
                return
            # 走到策略 2
            if collect_failed:
                # 失败时也尝试持久化已经收集到的部分
                self._persist_assistant("".join(collected_chunks))
                collected_chunks = []
                collect_failed = False

        # ===== 策略 2：run_in_executor + 同步 chat() + 切分 =====
        if agent is not None and hasattr(agent, "chat"):
            try:
                loop = asyncio.get_event_loop()
                full_response = await loop.run_in_executor(
                    None, agent.chat, user_input
                )
            except asyncio.CancelledError:
                # 取消信号直接向上传播
                self._persist_assistant("".join(collected_chunks))
                raise
            except Exception as e:  # noqa: BLE001
                warnings.warn(
                    f"[ChatService] 同步 chat() 降级失败: {e}",
                    RuntimeWarning,
                    stacklevel=2,
                )
                # 走到策略 3
                full_response = None

            if full_response:
                try:
                    tokens = re.findall(r"\S+\s*|\s+", full_response)
                    if not tokens:
                        tokens = [full_response[i:i + 2]
                                  for i in range(0, len(full_response), 2)]
                        if not tokens:
                            tokens = list(full_response)
                    for token in tokens:
                        # 取消检查（前置 + 让出事件循环）
                        if cancel_event is not None and cancel_event.is_set():
                            self._persist_assistant("".join(collected_chunks))
                            return
                        # 让出事件循环，便于取消信号传播
                        await asyncio.sleep(0)
                        collected_chunks.append(token or "")
                        yield token
                        # 40ms 间隔（30-50ms 区间内），避免网络洪水
                        await asyncio.sleep(0.04)
                    self._persist_assistant("".join(collected_chunks))
                    return
                except asyncio.CancelledError:
                    self._persist_assistant("".join(collected_chunks))
                    raise
                except Exception as e:  # noqa: BLE001
                    warnings.warn(
                        f"[ChatService] 分片失败: {e}",
                        RuntimeWarning,
                        stacklevel=2,
                    )
                    # 兜底：一次性把全部内容推出去
                    collected_chunks.append(full_response or "")
                    yield full_response
                    self._persist_assistant("".join(collected_chunks))
                    return

        # ===== 策略 3：最终降级 — 一次性回执 =====
        try:
            fallback = f"[ChatAgent 不可用] 收到: {user_input}"
            collected_chunks.append(fallback)
            yield fallback
        except Exception:
            # 连 yield 都失败时静默退出，不影响 WS 端点的清理流程
            pass
        # 兜底：尝试持久化（即便 agent 不可用也保留草稿）
        self._persist_assistant("".join(collected_chunks))

    def _persist_assistant(self, content: str) -> None:
        """
        v3.1.0: 把 assistant 完整回复写入 chat_messages；记录 message_id
        供后续 on_emotion() 异步更新 emotion_json。
        """
        if not content:
            return
        if self._session_id is None:
            return
        try:
            repo = self._get_repo()
            if repo is None:
                return
            mid = repo.add_message(self._session_id, "assistant", content)
            if mid:
                self._last_assistant_message_id = int(mid)
        except Exception:  # noqa: BLE001
            pass

    async def stream_chat(
        self,
        user_input: str,
        user_id: str = "default",
        cancel_event: Optional[Any] = None,
    ) -> AsyncIterator[Any]:
        """
        流式聊天入口（Pydantic ChatChunk）。

        包装 ChatAgent.chat_stream，产出 Pydantic ChatChunk。
        - 正常路径：每个字符串 chunk → ChatChunk(type='chunk', chunk=text, done=False)
        - 错误路径：ChatChunk(type='error', chunk=str(e), done=True)
        - 末尾：    ChatChunk(type='done', chunk='', done=True)

        Args:
            user_input: 用户输入
            user_id: 用户标识（透传给 agent）
            cancel_event: 取消事件（透传给 agent）

        Yields:
            ChatChunk 实例
        """
        from src.web.backend.schemas.chat import ChatChunk  # 延迟导入避免循环

        agent = self.get_agent()
        if agent is None:
            # agent 不可用也要走错误 chunk 协议（不抛），便于 WS 单边关闭
            yield ChatChunk(type="error", chunk="ChatAgent not initialized", done=True)
            return

        try:
            async for text in agent.chat_stream(
                user_input,
                user_id=user_id,
                cancel_event=cancel_event,
            ):
                # 跳过空字符串 chunk（前端没有内容可显示）
                if text is None or text == "":
                    continue
                yield ChatChunk(type="chunk", chunk=text, done=False)
        except asyncio.CancelledError:
            # 消费者主动断开时，安静地退出（不发送 error）
            return
        except Exception as e:  # noqa: BLE001
            # 异常路径：优雅 yield error chunk 后结束
            try:
                import traceback
                debug_msg = f"{type(e).__name__}: {e}"
            except Exception:
                debug_msg = str(e)
            yield ChatChunk(type="error", chunk=debug_msg, done=True)
            return

        # 末尾：done chunk
        # Stage B.3 / B.4: 流式成功结束后，通知前端情感雷达 / 话题时间线刷新
        try:
            self._emit_post_chat_updates(user_id=user_id)
        except Exception:  # noqa: BLE001
            pass
        yield ChatChunk(type="done", chunk="", done=True)

    # ------------------------------------------------------------------
    # 统计
    # ------------------------------------------------------------------
    def _emit_post_chat_updates(self, user_id: str = "default") -> None:
        """
        Stage B.3 / B.4: 在聊天流程结束后，把"最新情感 + 最新话题"作为
        emotion_update / timeline_update 事件派发到 EventService。

        设计要点：
        1. 内部每个调用都用 try/except 包裹，绝不向上抛异常
        2. 任何子模块（analyzer / memory / event_service）不可用时静默跳过
        3. 不修改现有 chat() / stream_chat() 公开签名
        """
        try:
            from src.web.backend.services.event_service import get_event_service
            es = get_event_service()
        except Exception:  # noqa: BLE001
            return
        if es is None:
            return

        # 1) 情感雷达
        try:
            from src.core.emotion_analyzer import EmotionRelationshipAnalyzer
            analyzer = EmotionRelationshipAnalyzer()
            payload = analyzer.get_latest_for_user(user_id) or {}
        except Exception:  # noqa: BLE001
            payload = {}
        try:
            es.emit_event('emotion_update', {
                'user_id': user_id,
                'data': payload.get('plutchik') or {},
                'additive_scores': payload.get('additive_scores') or {},
                'dominant': payload.get('dominant'),
                'timestamp': payload.get('timestamp'),
            })
        except Exception:  # noqa: BLE001
            pass

        # 2) 话题时间线
        try:
            from src.core.long_term_memory import LongTermMemoryManager
            mgr = LongTermMemoryManager()
            topics = mgr.list_topics(user_id=user_id, days=7) or []
        except Exception:  # noqa: BLE001
            topics = []
        try:
            from datetime import datetime as _dt
            ts_now = _dt.now().isoformat()
        except Exception:  # noqa: BLE001
            ts_now = ''
        try:
            es.emit_event('timeline_update', {
                'user_id': user_id,
                'days': 7,
                'topics': topics,
                'replace': True,
                'timestamp': ts_now,
            })
        except Exception:  # noqa: BLE001
            pass

    def get_stats(self) -> Dict[str, Any]:
        """
        返回服务状态、版本号与能力声明。
        """
        return {
            "agent_loaded": self._agent is not None,
            "version": __version__,
            "path": "v3_chat_agent",
            "capabilities": {
                "streaming": True,
                "tool_calling": False,
                "memory": True,
                "emotion": True,
                "schedule": True,
                "session_persistence": True,
            },
        }


# 全局单例
chat_service = ChatService()


__all__ = ["ChatService", "chat_service"]
