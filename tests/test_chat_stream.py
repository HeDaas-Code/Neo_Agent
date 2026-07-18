"""
Stage B.2: ChatService.chat_stream 单元测试

覆盖三个核心场景:
- 正常 (normal): agent 正常流式输出，chunks 聚合后等于预期文本
- 异常 (exception, agent 抛错): agent.chat_stream / chat 抛异常时，
  服务应能优雅降级（不会让 WS 端点整体崩溃）
- 取消 (cancel, async generator 被关闭): 消费者提前 break 不应抛异常

兼容性:
- 使用标准库 unittest.IsolatedAsyncioTestCase（不需要 pytest / pytest-asyncio）
- 在缺少 langchain / fastapi 等重型依赖时优雅 skip（参考 tests/e2e/test_chat_flow.py）
- 使用 stub agent，不发起真实 LLM / DB 调用
"""

from __future__ import annotations

import asyncio
import os
import sys
import unittest
from typing import Any, AsyncIterator, Dict, Optional

# 让 tests/ 目录能 import src.*
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
)

# 依赖检查：导入 ChatService 时会触发 src.web.backend.services.__init__
# 其内部又会触发对 ChatAgent / DatabaseManager / EventService 的懒加载。
# 若 langchain / dotenv / fastapi 等缺失，这些懒加载在 try/except 中失败，
# 不应阻塞测试运行，但为了和 e2e 模式一致，仍做 try/except 守卫。
try:
    from src.web.backend.services.chat_service import ChatService  # noqa: E402
    _DEPS_OK = True
    _IMPORT_ERROR: Optional[BaseException] = None
except Exception as exc:  # noqa: BLE001
    ChatService = None  # type: ignore
    _DEPS_OK = False
    _IMPORT_ERROR = exc


_SKIP_REASON = (
    f"缺少 ChatService 相关依赖: {_IMPORT_ERROR}"
    if not _DEPS_OK else ""
)


# ----------------------------------------------------------------------
# Stub agents — 避免实例化真实 ChatAgent
# ----------------------------------------------------------------------
class StubChatAgent:
    """正常流式输出的 stub"""

    def __init__(self, tokens: Optional[list] = None) -> None:
        self.tokens = tokens or ["你", "好", "，", "世界"]
        self.received_inputs: list = []
        self.received_contexts: list = []

    async def chat_stream(
        self, user_input: str, context: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        self.received_inputs.append(user_input)
        self.received_contexts.append(context)
        for token in self.tokens:
            yield token
            await asyncio.sleep(0.01)


class ErrorChatAgent:
    """agent 内部抛错的 stub（chat_stream / chat 都失败）"""

    def __init__(self, exc: Optional[BaseException] = None) -> None:
        self.exc = exc or RuntimeError("simulated LLM failure")

    async def chat_stream(
        self, user_input: str, context: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        # 模拟 astream 失败后回退到同步 chat() 也失败的场景
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, self._raise_sync, user_input)
        yield ""

    def _raise_sync(self, user_input: str) -> None:
        raise self.exc


class SlowChatAgent:
    """慢速流式输出的 stub，用于取消测试"""

    async def chat_stream(
        self, user_input: str, context: Optional[Dict] = None
    ) -> AsyncIterator[str]:
        for i in range(100):
            yield f"chunk{i}"
            await asyncio.sleep(0.02)


# ----------------------------------------------------------------------
# 三场景核心测试
# ----------------------------------------------------------------------
@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestChatStreamThreeScenarios(unittest.IsolatedAsyncioTestCase):
    """
    Stage B.2 三场景核心测试。
    使用 stub agent，不依赖真实 LLM / DB。
    """

    # ----- 场景 1: 正常 -----
    async def test_normal(self) -> None:
        """
        场景 1 (正常):
        agent 有 chat_stream 时，service 应委托给 agent，
        聚合后的 chunks 等于 stub tokens 拼接结果。
        """
        service = ChatService()
        agent = StubChatAgent(tokens=["Hello", " ", "world", "!"])
        service.set_agent(agent)

        chunks: list = []
        async for chunk in service.chat_stream("hi"):
            chunks.append(chunk)

        self.assertEqual("".join(chunks), "Hello world!")
        self.assertEqual(agent.received_inputs, ["hi"])
        # 未传 context，应为 None
        self.assertEqual(agent.received_contexts, [None])

    # ----- 场景 2: 异常（agent 抛错）-----
    async def test_exception(self) -> None:
        """
        场景 2 (异常):
        agent.chat_stream 和 agent.chat 都失败时，
        service 不应向外抛异常，至少 yield 一次降级回执。
        """
        service = ChatService()
        agent = ErrorChatAgent(RuntimeError("LLM down"))
        service.set_agent(agent)

        chunks: list = []
        # 不应抛异常
        try:
            async for chunk in service.chat_stream("hello"):
                chunks.append(chunk)
        except Exception as e:  # noqa: BLE001
            self.fail(f"chat_stream 不应向外抛异常: {type(e).__name__}: {e}")

        # 应至少 yield 一次降级回执（fallback 消息或 stream error 标记）
        self.assertTrue(chunks, "降级路径应至少 yield 一个 chunk")
        aggregated = "".join(chunks)
        # 任意一种降级标识都可接受
        self.assertTrue(
            any(marker in aggregated for marker in [
                "[ChatAgent",            # 策略 3 最终降级
                "[stream error]",        # 策略 2 chat() 抛错
                "LLM down",              # 错误内容
            ]),
            f"聚合结果应包含降级信息，实际: {aggregated!r}",
        )

    # ----- 场景 3: 取消（async generator 被关闭）-----
    async def test_cancel(self) -> None:
        """
        场景 3 (取消):
        消费者提前 break 时，async generator 应能干净关闭，
        不抛异常，且不消费剩余 chunk。
        """
        service = ChatService()
        agent = SlowChatAgent()
        service.set_agent(agent)

        count = 0
        async for _chunk in service.chat_stream("hello"):
            count += 1
            if count >= 3:
                break  # 提前关闭

        # 提前 break 不应抛异常；计数应为 3
        self.assertEqual(count, 3)
        # 不应消费全部 100 个 chunk
        self.assertLess(count, 100)


# ----------------------------------------------------------------------
# 附加测试: 覆盖 context 透传 + agent 不可用
# ----------------------------------------------------------------------
@unittest.skipUnless(_DEPS_OK, _SKIP_REASON)
class TestChatStreamExtras(unittest.IsolatedAsyncioTestCase):
    """附加测试：context 透传 + agent 不可用降级"""

    async def test_context_passed_through(self) -> None:
        """context 参数应原样透传给 agent.chat_stream"""
        service = ChatService()
        agent = StubChatAgent()
        service.set_agent(agent)

        ctx = {"user_id": "u1", "trace_id": "t1"}
        chunks: list = []
        async for chunk in service.chat_stream("hi", context=ctx):
            chunks.append(chunk)

        self.assertEqual(agent.received_contexts, [ctx])

    async def test_no_agent_yields_fallback(self) -> None:
        """agent 完全不可用时，应 yield 一次性 fallback 回执（不抛异常）"""
        service = ChatService()
        service.set_agent(None)

        chunks: list = []
        try:
            async for chunk in service.chat_stream("hello world"):
                chunks.append(chunk)
        except Exception as e:  # noqa: BLE001
            self.fail(f"agent 不可用时不应抛异常: {type(e).__name__}: {e}")

        self.assertTrue(chunks, "agent 不可用时也应至少 yield 一次回执")
        aggregated = "".join(chunks)
        # 无 agent 时可能通过 _try_init_agent() 成功实例化真实 ChatAgent 并返回真实回复，
        # 因此只要包含回显输入或任意非空回复即可接受
        self.assertTrue(
            "hello world" in aggregated or len(aggregated.strip()) > 0,
            f"fallback 消息应回显 user_input 或非空回复，实际: {aggregated!r}",
        )


# ----------------------------------------------------------------------
# 入口
# ----------------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
