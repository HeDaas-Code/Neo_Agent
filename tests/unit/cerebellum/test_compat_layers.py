"""
v4.0 兼容层单元测试（小脑）。

验证旧路径（src.tools.*）仍然可以通过导入转发访问新实现。
"""

from src.cerebellum.vision.agent_vision import AgentVisionTool as CerebellumAgentVisionTool
from src.cerebellum.intent.schedule_intent_tool import ScheduleIntentTool as CerebellumScheduleIntentTool
from src.cerebellum.interrupt.interrupt_question_tool import InterruptQuestionTool as CerebellumInterruptQuestionTool
from src.cerebellum.nps.bridge_tool import NPSBridgeTool as CerebellumNPSBridgeTool
from src.cerebellum.nps.langchain_tools import (
    NPSSystemTimeTool as CerebellumNPSSystemTimeTool,
    NPSWebSearchTool as CerebellumNPSWebSearchTool,
    create_nps_tools as cerebellum_create_nps_tools,
)
from src.cerebellum.style.expression_style import ExpressionStyleManager as CerebellumExpressionStyleManager

from src.tools.agent_vision import AgentVisionTool as ToolsAgentVisionTool
from src.tools.schedule_intent_tool import ScheduleIntentTool as ToolsScheduleIntentTool
from src.tools.interrupt_question_tool import InterruptQuestionTool as ToolsInterruptQuestionTool
from src.tools.nps_bridge_tool import NPSBridgeTool as ToolsNPSBridgeTool
from src.tools.nps_langchain_tools import (
    NPSSystemTimeTool as ToolsNPSSystemTimeTool,
    NPSWebSearchTool as ToolsNPSWebSearchTool,
    create_nps_tools as tools_create_nps_tools,
)
from src.tools.expression_style import ExpressionStyleManager as ToolsExpressionStyleManager


def test_agent_vision_compat():
    """src.tools.agent_vision 应转发到 src.cerebellum.vision.agent_vision。"""
    assert ToolsAgentVisionTool is CerebellumAgentVisionTool


def test_schedule_intent_compat():
    """src.tools.schedule_intent_tool 应转发到 src.cerebellum.intent.schedule_intent_tool。"""
    assert ToolsScheduleIntentTool is CerebellumScheduleIntentTool


def test_interrupt_question_compat():
    """src.tools.interrupt_question_tool 应转发到 src.cerebellum.interrupt.interrupt_question_tool。"""
    assert ToolsInterruptQuestionTool is CerebellumInterruptQuestionTool


def test_nps_bridge_compat():
    """src.tools.nps_bridge_tool 应转发到 src.cerebellum.nps.bridge_tool。"""
    assert ToolsNPSBridgeTool is CerebellumNPSBridgeTool


def test_nps_langchain_tools_compat():
    """src.tools.nps_langchain_tools 应转发到 src.cerebellum.nps.langchain_tools。"""
    assert ToolsNPSWebSearchTool is CerebellumNPSWebSearchTool
    assert ToolsNPSSystemTimeTool is CerebellumNPSSystemTimeTool
    assert tools_create_nps_tools is cerebellum_create_nps_tools


def test_expression_style_compat():
    """src.tools.expression_style 应转发到 src.cerebellum.style.expression_style。"""
    assert ToolsExpressionStyleManager is CerebellumExpressionStyleManager
