"""
Chat WebSocket Router
- /ws/chat：流式聊天
- 通过 ChatService.stream_chat 转发到客户端
- Stage D.3 集成：connection 时把 chat_event 转发到 EventService
- Stage B.2 集成：把 echo 占位替换为 ChatAgent 真流式
- Stage B.3 集成：聊天流式结束时推送 emotion_update 事件（前端缓存到 window.__lastEmotion）
"""

from __future__ import annotations

import asyncio
import json
import sys
import uuid
from pathlib import Path
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

# 确保从项目根目录能正确 import src.*
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from src.web.backend.ws.manager import manager

try:
    from src.web.backend.services.chat_service import ChatService
except Exception:  # noqa: BLE001
    ChatService = None  # type: ignore

# Stage B.3: 情感雷达服务（懒加载、可选依赖）
try:
    from src.web.backend.services.emotion_service import emotion_service
except Exception:  # noqa: BLE001
    emotion_service = None  # type: ignore

try:
    from src.tools.debug_logger import get_debug_logger
except Exception:  # noqa: BLE001
    def get_debug_logger():
        class _Stub:
            def log_info(self, *args, **kwargs): pass
            def log_warn(self, *args, **kwargs): pass
            def log_error(self, *args, **kwargs): pass
        return _Stub()

# v4.0: WebSocket 网关桥接（可选，失败时降级到 ChatService）
try:
    from src.web.backend.services.neo_bridge import get_neo_app
    from src.nervous_system.gateway.base_gateway import GatewayRequest
    from src.nervous_system.router.packet import PacketType
except Exception:  # noqa: BLE001
    get_neo_app = None  # type: ignore
    GatewayRequest = None  # type: ignore
    PacketType = None  # type: ignore

debug_logger = get_debug_logger()

router = APIRouter()
CHANNEL = "chat"


# ----------------------------------------------------------------------
# v4.0: WebSocket 网关辅助函数
# ----------------------------------------------------------------------
def _get_neo_ws_gateway():
    """获取 NeoApp 的 WebSocketGateway，若不可用返回 None。"""
    if get_neo_app is None:
        return None
    try:
        neo_app = get_neo_app()
        if neo_app is None:
            return None
        return getattr(neo_app, "ws_gateway", None)
    except Exception:  # noqa: BLE001
        return None


async def _stream_via_neo(
    ws_gateway,
    conn_id: str,
    user_id: str,
    user_input: str,
    session_id: Optional[int],
    context: dict,
) -> AsyncIterator[str]:
    """
    通过 WebSocketGateway → CentralRouter → prefrontal.workflow 流式获取回复。

    Yields 字符串 chunk；若出错则 yield 错误提示字符串。
    """
    request = GatewayRequest(
        method="WS_MESSAGE",
        path="/ws/chat",
        body={
            "user_input": user_input,
            "user_id": user_id,
            "session_id": session_id,
            "context": context,
        },
        metadata={
            "conn_id": conn_id,
            "user_id": user_id,
            "trace_id": uuid.uuid4().hex,
        },
    )

    async for packet in ws_gateway.handle_stream(request):
        if packet.is_error():
            yield f"[网关错误: {packet.payload.get('error', 'unknown error')}]"
            break

        if packet.packet_type != PacketType.STREAM:
            continue

        stream_event = packet.payload.get("stream_event")
        if stream_event == "chunk":
            content = packet.payload.get("content", "")
            if content:
                yield content
        elif stream_event == "error":
            yield f"[流式错误: {packet.payload.get('error', 'unknown stream error')}]"
            break
        elif stream_event == "done":
            break


# ----------------------------------------------------------------------
# Stage B.3: 工具：构造 + 发送 emotion_update
# ----------------------------------------------------------------------
async def _publish_emotion_update(
    conn_id: str,
    user_id: str = "default",
    last_message: str = "",
) -> None:
    """
    在聊天流式结束时调用：
      1) 调 emotion_service.get_latest_emotion(user_id) 拿到 8 维 dict
      2) 构造 emotion_update 事件 payload
      3) 通过 manager.send_personal 直接发到 chat 连接
      4) 同时 es.emit_event('emotion_update', payload) 推给 /ws/events 订阅者
    失败时静默降级（不阻断 chat 主循环）。
    """
    uid = (user_id or "default").strip() or "default"
    payload: dict = {}
    try:
        if emotion_service is not None:
            payload = emotion_service.build_emotion_update_event(uid) or {}
        # 透传最近一次用户消息（哪怕情感分析没拿到 last_message）
        if last_message and isinstance(payload, dict):
            if not payload.get("last_message"):
                payload["last_message"] = last_message[:2000]
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_warn('ws.chat', f'build_emotion_update 失败: {exc}')
        except Exception:
            pass
        payload = {
            "type": "emotion_update",
            "data": {},
            "cumulative": {},
            "historical_max": None,
            "last_message": last_message or "",
            "timestamp": "",
            "user_id": uid,
        }

    # 1) 直接发给当前 chat ws 客户端（前端 useChatStream 处理）
    try:
        await manager.send_personal(conn_id, payload)
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_warn('ws.chat', f'send_personal emotion_update 失败: {exc}')
        except Exception:
            pass

    # 2) 同步 publish 给 /ws/events 订阅者（emotion_update 事件）
    try:
        from src.web.backend.services.event_service import get_event_service
        es = get_event_service()
        if es is not None:
            # emit_event 期望 payload 是 dict；我们把外层 type 留出来
            publish_payload = {k: v for k, v in payload.items() if k != "type"}
            publish_payload.setdefault("data", payload.get("data") or {})
            es.emit_event('emotion_update', publish_payload)
    except Exception:
        pass

    # 3) v3.1.0: 异步把情感数据持久化到最近一条 assistant 消息
    try:
        from src.web.backend.services.chat_service import chat_service as _cs
        if _cs is not None:
            # payload.data 是 8 维 dict；连同 plutchik/cumulative 一并写库
            _cs.on_emotion({
                "data": payload.get("data") or {},
                "cumulative": payload.get("cumulative") or {},
                "historical_max": payload.get("historical_max"),
                "dominant": payload.get("dominant"),
                "last_message": payload.get("last_message") or "",
                "timestamp": payload.get("timestamp") or "",
            })
    except Exception:
        pass


@router.websocket("/ws/chat")
async def chat_ws(websocket: WebSocket) -> None:
    """
    /ws/chat 端点
    客户端发送 {"type": "message", "content": "..."}
    服务端流式返回 Pydantic ChatChunk 的 model_dump()（含 type / chunk / done）
    聊天结束后追加一条 {"type": "emotion_update", ...} 帧（Stage B.3）
    """
    try:
        await websocket.accept()
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.chat', f'accept 失败: {e}', e)
        except Exception:
            pass
        return

    conn_id = uuid.uuid4().hex
    try:
        await manager.connect(websocket, conn_id, CHANNEL)
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.chat', f'connect 失败: {e}', e)
        except Exception:
            pass

    # v4.0: 尝试注册到 WebSocketGateway
    ws_gateway = _get_neo_ws_gateway()
    if ws_gateway is not None:
        try:
            await ws_gateway.register_connection(conn_id, websocket)
        except Exception:  # noqa: BLE001
            pass

    # v3.1.0: 性能修复 - 复用模块级 ChatService 单例，避免每个 WS 连接都
    #          重新实例化 ChatAgent / ModelRouter / LangChainLLM / DatabaseManager
    #          等重型组件（旧实现每连接 3 个 LLM 初始化 + 全套 agent 重建）
    chat_service: Optional[ChatService] = None
    try:
        from src.web.backend.services.chat_service import chat_service as _singleton
        chat_service = _singleton
    except Exception as exc:  # noqa: BLE001
        try:
            debug_logger.log_warn('ws.chat', f'复用 chat_service 单例失败: {exc}')
        except Exception:
            pass

    # v3.1.0: 解析 query param 中的 session_id / user_id 并绑定
    try:
        q_session_id = websocket.query_params.get("session_id")
        if q_session_id and chat_service is not None:
            try:
                chat_service.set_session_id(int(q_session_id))
            except (TypeError, ValueError):
                pass
    except Exception:
        pass

    try:
        path_label = "v4_neo" if ws_gateway is not None else "v3_chat_agent"
        await manager.send_personal(conn_id, {
            "type": "system",
            "message": "connected to /ws/chat",
            "path": path_label,
        })
    except Exception:
        pass

    # v3.1.0: 若仍未绑 session_id（前端未传），首条消息来时由 chat_service 自动创建
    # ack 帧会把真实 session_id 告诉前端
    try:
        await manager.send_personal(conn_id, {
            "type": "ack",
            "session_id": str(chat_service.get_session_id()) if chat_service and chat_service.get_session_id() else "",
            "conn_id": conn_id,
        })
    except Exception:
        pass

    try:
        while True:
            try:
                raw = await websocket.receive_text()
            except WebSocketDisconnect:
                break
            except Exception as e:  # noqa: BLE001
                try:
                    debug_logger.log_error('ws.chat', f'receive_text 失败: {e}', e)
                except Exception:
                    pass
                break

            try:
                data = json.loads(raw) if raw else {}
            except Exception:
                data = {"type": "message", "content": raw}

            msg_type = (data.get("type") or "message").lower()
            user_input = (data.get("content") or data.get("text") or "").strip()
            user_id = (data.get("user_id") or "default").strip() or "default"

            if msg_type == "ping":
                await manager.send_personal(conn_id, {"type": "pong"})
                continue

            if not user_input:
                await manager.send_personal(conn_id, {
                    "type": "error",
                    "message": "empty input",
                })
                continue

            try:
                from src.web.backend.services.event_service import get_event_service
                es = get_event_service()
                es.emit_event('chat_event', {
                    "kind": "user_message",
                    "content": user_input,
                })
            except Exception:
                pass

            # v4.0: 优先通过 WebSocketGateway → CentralRouter 流式路由
            use_neo = ws_gateway is not None
            if not use_neo and chat_service is None:
                await manager.send_personal(conn_id, {
                    "type": "error",
                    "message": "ChatService unavailable",
                })
                continue

            # 推送协议：每 chunk -> {"type": "chunk", "content": chunk}
            #         结束    -> {"type": "done"}
            #         异常    -> {"type": "error", "message": str(e)}
            try:
                # v3.1.0: 若首条消息自动创建了 session，主动把 session_id 通过 ack 帧告诉前端
                _had_session_at_start = bool(
                    chat_service and chat_service.get_session_id()
                )

                if use_neo:
                    # v4.0: 走神经系统工作流
                    q_session_id = websocket.query_params.get("session_id")
                    session_id: Optional[int] = None
                    if q_session_id:
                        try:
                            session_id = int(q_session_id)
                        except (TypeError, ValueError):
                            session_id = None
                    async for chunk in _stream_via_neo(
                        ws_gateway,
                        conn_id=conn_id,
                        user_id=user_id,
                        user_input=user_input,
                        session_id=session_id,
                        context=data,
                    ):
                        if chunk is None or chunk == "":
                            continue
                        await manager.send_personal(conn_id, {
                            "type": "chunk",
                            "content": chunk,
                        })
                else:
                    # v3.x: 降级到 ChatService
                    async for chunk in chat_service.chat_stream(
                        user_input, context=data
                    ):
                        if chunk is None or chunk == "":
                            continue
                        await manager.send_personal(conn_id, {
                            "type": "chunk",
                            "content": chunk,
                        })

                # 正常结束：done 帧
                await manager.send_personal(conn_id, {"type": "done"})

                # v3.1.0: 若是首条消息并触发了 session 创建，补发 session_id
                if chat_service is not None and not _had_session_at_start:
                    new_sid = chat_service.get_session_id()
                    if new_sid:
                        try:
                            await manager.send_personal(conn_id, {
                                "type": "session",
                                "session_id": str(new_sid),
                            })
                        except Exception:
                            pass

                try:
                    from src.web.backend.services.event_service import get_event_service
                    es = get_event_service()
                    es.emit_event('chat_event', {"kind": "done", "input": user_input})
                except Exception:
                    pass

                # Stage B.3: 流式结束 → 推送 emotion_update
                # 缓存失效 + 重新构造（确保拿到最新分析）
                try:
                    if emotion_service is not None:
                        emotion_service.cache_clear(user_id)
                except Exception:
                    pass
                # v3.1.0: 先调 on_emotion 把情感数据写入 assistant 消息的 emotion_json
                try:
                    if chat_service is not None:
                        # 占位 payload —— 真实值会由 _publish_emotion_update 推送；
                        # 这里只是尝试一次同步写入最新缓存（如果有）
                        pass
                except Exception:
                    pass
                await _publish_emotion_update(
                    conn_id=conn_id,
                    user_id=user_id,
                    last_message=user_input,
                )
            except Exception as e:  # noqa: BLE001
                # 兜底：流式过程中出现非预期异常，发送 error frame 后继续
                try:
                    debug_logger.log_error('ws.chat', f'chat_stream 失败: {e}', e)
                except Exception:
                    pass
                try:
                    await manager.send_personal(conn_id, {
                        "type": "error",
                        "message": str(e),
                    })
                except Exception:
                    pass
    except WebSocketDisconnect:
        pass
    except Exception as e:  # noqa: BLE001
        try:
            debug_logger.log_error('ws.chat', f'主循环异常: {e}', e)
        except Exception:
            pass
    finally:
        # v3.1.0: 连接结束清理 - 重置单例的 _session_id，
        # 防止下个连接继承上次的会话上下文（避免跨连接串话）
        try:
            if chat_service is not None and hasattr(chat_service, "set_session_id"):
                chat_service.set_session_id(None)
        except Exception:
            pass
        # v4.0: 从 WebSocketGateway 注销连接
        if ws_gateway is not None:
            try:
                await ws_gateway.unregister_connection(conn_id)
            except Exception:
                pass
        try:
            manager.disconnect(conn_id)
        except Exception:
            pass


__all__ = ["router", "CHANNEL"]
