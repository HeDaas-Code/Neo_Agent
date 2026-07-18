"""
Chat schemas - Pydantic v2 models for chat endpoints.
聊天相关的 Pydantic v2 模型。

Stage A.3: 为 /api/chat 提供请求/响应/流式 chunk 的契约。
"""

from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    """
    聊天请求体。
    Attributes:
        user_input: 用户输入文本（必填，1-10000 字符）
        context: 可选上下文（不直接传给 agent，保留供未来扩展）
        stream: 是否走流式响应（Stage B.2 才真正使用）
    """
    user_input: str = Field(..., min_length=1, max_length=10000)
    context: Optional[Dict] = None
    stream: bool = False


class ChatChunk(BaseModel):
    """
    流式响应 chunk。
    Attributes:
        type: chunk 类型（chunk / done / error）；用于客户端按类型分发
        chunk: 增量文本片段
        done: 是否为最后一个 chunk
        message_id: 消息 ID（首个 chunk 必带，便于客户端关联）
    """
    type: str = Field(default="chunk", description="chunk 类型：chunk / done / error")
    chunk: str
    done: bool = False
    message_id: Optional[str] = None


class ChatResponse(BaseModel):
    """
    同步聊天响应。
    Attributes:
        content: 完整回复文本
        message_id: 消息唯一标识
        emotion: 情绪标签/分值（可选）
        timestamp: ISO 8601 时间戳
    """
    content: str
    message_id: str
    emotion: Optional[Dict] = None
    timestamp: str


__all__ = ["ChatRequest", "ChatChunk", "ChatResponse"]
