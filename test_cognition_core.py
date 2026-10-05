"""测试认知门控核心功能（不依赖完整 Agent 运行时）。"""
import json
from unittest.mock import Mock
from neo_agent.runtime.cognition import (
    CognitionDecision,
    ActionResult,
    safe_result_summary,
    risk_for_tool,
    CognitionService,
    GroupReplyGate,
    IncomingMessage
)


def test_cognition_decision_parsing():
    """测试认知决策的结构化解析。"""
    raw = {
        "intent": "query_knowledge",
        "action_needed": True,
        "reply_strategy": "reply",
        "confidence": 0.85,
        "relationship_signal": "positive",
        "affective_state": "友好"
    }
    
    decision = CognitionDecision.from_mapping(raw)
    
    assert decision.intent == "query_knowledge"
    assert decision.action_needed is True
    assert decision.reply_strategy == "reply"
    assert decision.confidence == 0.85
    assert decision.relationship_signal == "positive"
    assert decision.affective_state == "友好"
    
    print("✅ 认知决策解析测试通过")


def test_action_result_public_dict():
    """测试操作结果的公开视图（传给表达阶段）。"""
    # 成功操作
    success_result = ActionResult(
        tool_name="internal_vector_search_v2",
        capability="search.memory",
        status="succeeded",
        risk="low",
        summary="找到 3 条相关记忆"
    )
    
    public = success_result.public_dict()
    
    # 验证：公开视图只包含状态和摘要，不包含工具名和能力
    assert "status" in public
    assert "summary" in public
    assert "tool_name" not in public
    assert "capability" not in public
    assert "risk" not in public
    
    assert public["status"] == "succeeded"
    assert public["summary"] == "找到 3 条相关记忆"
    
    print("✅ 操作结果公开视图测试通过：工具名和能力被隐藏")


def test_safe_result_summary_filters_secrets():
    """测试结果摘要过滤敏感信息。"""
    # 测试1：字符串类型的敏感信息被完全屏蔽
    raw1 = "连接成功，使用 api_key=sk-abc123xyz"
    summary1 = safe_result_summary(raw1)
    # 字符串类型的非结构化输出不安全，应该返回通用消息
    assert "sk-abc123xyz" not in summary1
    assert summary1 == "操作已完成。"  # 默认安全消息
    
    # 测试2：字符串类型的路径信息被屏蔽
    raw2 = "操作完成，文件保存至 /home/user/.ssh/id_rsa"
    summary2 = safe_result_summary(raw2)
    assert "/home/user" not in summary2
    assert "id_rsa" not in summary2
    assert summary2 == "操作已完成。"
    
    # 测试3：结构化结果中的 summary 字段可以传递
    raw3 = {"status": "success", "summary": "找到了 3 个匹配项"}
    summary3 = safe_result_summary(raw3)
    assert "找到了 3 个匹配项" in summary3
    
    # 测试4：失败操作
    summary4 = safe_result_summary(None, failed=True)
    assert summary4 == "操作未能完成。"
    
    # 测试5：错误状态
    raw5 = {"status": "failed", "error": "连接超时"}
    summary5 = safe_result_summary(raw5)
    assert summary5 == "操作未能完成。"
    
    # 测试6：message 字段
    raw6 = {"status": "ok", "message": "数据已保存"}
    summary6 = safe_result_summary(raw6)
    assert "数据已保存" in summary6
    
    print("✅ 安全摘要过滤测试通过：敏感信息已脱敏")


def test_risk_classification():
    """测试工具风险分类。"""
    # 高风险：文件系统写入
    assert risk_for_tool("file_manager", ["sandbox.fs.write"]) == "high"
    
    # 高风险：包含删除关键字
    assert risk_for_tool("delete_memory", ["memory.delete"]) == "high"
    
    # 高风险：NPS 创建
    assert risk_for_tool("create_nps", ["nps.create"]) == "high"
    
    # 高风险：插件安装
    assert risk_for_tool("install_plugin", ["plugin.install"]) == "high"
    
    # 低风险：只读操作
    assert risk_for_tool("search_memory", ["search.memory"]) == "low"
    
    # 低风险：查询操作
    assert risk_for_tool("get_schedule", ["schedule.query"]) == "low"
    
    print("✅ 风险分类测试通过：高风险操作正确标记")


def test_group_reply_gate():
    """测试群聊回复门控逻辑。"""
    gate = GroupReplyGate()
    
    # 测试1：直接 @ 提及，必须回复
    msg1 = IncomingMessage(
        message_id="m1",
        group_id="g1",
        speaker_id="user1",
        text="@林依 你好",
        addressed_to_agent=True,
        confidence=0.9
    )
    candidate1 = gate.evaluate(msg1)
    assert candidate1.decision == "reply"
    assert candidate1.reason == "direct_address"
    
    # 测试2：相关性低，保持沉默
    msg2 = IncomingMessage(
        message_id="m2",
        group_id="g1",
        speaker_id="user2",
        text="今天天气不错",
        addressed_to_agent=False,
        relevance=0.2,
        confidence=0.8
    )
    candidate2 = gate.evaluate(msg2)
    assert candidate2.decision == "silence"
    assert "low_relevance" in candidate2.reason
    
    # 测试3：冷却期内，非直接提及时沉默
    msg3 = IncomingMessage(
        message_id="m3",
        group_id="g1",
        speaker_id="user3",
        text="有人知道这个吗？",
        addressed_to_agent=False,
        relevance=0.7,
        confidence=0.8,
        cooldown=True
    )
    candidate3 = gate.evaluate(msg3)
    assert candidate3.decision == "silence"
    assert "cooldown" in candidate3.reason
    
    # 测试4：置信度不足，延迟回复
    msg4 = IncomingMessage(
        message_id="m4",
        group_id="g1",
        speaker_id="user4",
        text="这个怎么办？",
        addressed_to_agent=False,
        relevance=0.7,
        confidence=0.5
    )
    candidate4 = gate.evaluate(msg4)
    assert candidate4.decision == "delay"
    assert "uncertain" in candidate4.reason
    
    # 测试5：群聊活跃度高，延迟回复
    msg5 = IncomingMessage(
        message_id="m5",
        group_id="g1",
        speaker_id="user5",
        text="关于这个话题",
        addressed_to_agent=False,
        relevance=0.6,
        confidence=0.7,
        activity=0.95
    )
    candidate5 = gate.evaluate(msg5)
    assert candidate5.decision == "delay"
    assert "busy" in candidate5.reason
    
    # 测试6：正常相关消息，回复
    msg6 = IncomingMessage(
        message_id="m6",
        group_id="g1",
        speaker_id="user6",
        text="有什么推荐吗？",
        addressed_to_agent=False,
        relevance=0.8,
        confidence=0.75,
        activity=0.3
    )
    candidate6 = gate.evaluate(msg6)
    assert candidate6.decision == "reply"
    assert "relevant" in candidate6.reason
    
    print("✅ 群聊回复门控测试通过：沉默/延迟/回复策略正确")


def test_cognition_service_with_mock_model():
    """测试认知服务的模型调用。"""
    mock_model = Mock()
    mock_response = Mock()
    mock_response.content = json.dumps({
        "intent": "information_query",
        "action_needed": False,
        "reply_strategy": "reply",
        "confidence": 0.9,
        "relationship_signal": "neutral",
        "affective_state": "好奇"
    })
    mock_model.invoke.return_value = mock_response
    
    service = CognitionService(mock_model)
    
    decision = service.assess(
        message="什么是 Python？",
        context="这是一次技术讨论",
        personality="热心助人的程序员",
        direct_chat=True
    )
    
    assert decision.intent == "information_query"
    assert decision.action_needed is False
    assert decision.reply_strategy == "reply"
    assert decision.confidence == 0.9
    
    # 验证模型被调用
    assert mock_model.invoke.call_count == 1
    
    print("✅ 认知服务模型调用测试通过")


def test_direct_chat_forces_reply_or_clarify():
    """测试直聊模式强制回复或澄清，不允许沉默。"""
    mock_model = Mock()
    
    # 模型错误地返回 "silence"
    mock_response = Mock()
    mock_response.content = json.dumps({
        "intent": "unclear",
        "action_needed": False,
        "reply_strategy": "silence",  # 错误：直聊不能沉默
        "confidence": 0.3,
        "relationship_signal": "neutral",
        "affective_state": "困惑"
    })
    mock_model.invoke.return_value = mock_response
    
    service = CognitionService(mock_model)
    
    decision = service.assess(
        message="嗯",
        direct_chat=True  # 直聊模式
    )
    
    # 验证：即使模型返回 silence，直聊模式也会强制改为 reply
    assert decision.reply_strategy == "reply"
    assert decision.reply_strategy != "silence"
    
    print("✅ 直聊强制回复测试通过：沉默被改写为回复")


if __name__ == "__main__":
    print("🧪 开始认知门控核心功能测试...\n")
    
    try:
        test_cognition_decision_parsing()
        test_action_result_public_dict()
        test_safe_result_summary_filters_secrets()
        test_risk_classification()
        test_group_reply_gate()
        test_cognition_service_with_mock_model()
        test_direct_chat_forces_reply_or_clarify()
        
        print("\n" + "="*60)
        print("✅ 所有认知门控核心测试通过！")
        print("   - 认知决策结构化解析 ✓")
        print("   - 操作结果隐私边界 ✓")
        print("   - 敏感信息脱敏 ✓")
        print("   - 风险分类 ✓")
        print("   - 群聊回复门控 ✓")
        print("   - 认知服务集成 ✓")
        print("   - 直聊模式约束 ✓")
        print("="*60)
        print("\n📋 Phase 2 核心验证：")
        print("   ✓ 认知决策与执行隔离")
        print("   ✓ 表达阶段接收规范化摘要")
        print("   ✓ 敏感信息自动脱敏")
        print("   ✓ 高风险操作标记机制")
        print("   ✓ 群聊智能回复门控")
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"\n💥 测试错误: {e}")
        import traceback
        traceback.print_exc()
        raise
