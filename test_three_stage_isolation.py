"""测试三阶段认知门控：认知→执行→表达的完全隔离。"""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from neo_agent.storage import DiskStore
from neo_agent.runtime.agent import AgentRuntime
from neo_agent.runtime.cognition import ActionResult, CognitionDecision


def test_stage_isolation():
    """验证表达阶段无工具绑定，只接收规范化摘要。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        # 模拟认知模型
        mock_cognition_model = Mock()
        mock_cognition_response = Mock()
        mock_cognition_response.content = json.dumps({
            "intent": "test_action",
            "action_needed": True,
            "reply_strategy": "reply",
            "confidence": 0.9,
            "relationship_signal": "positive",
            "affective_state": "友好"
        })
        mock_cognition_model.invoke.return_value = mock_cognition_response
        
        # 模拟执行/表达模型
        mock_execution_model = Mock()
        
        # 第一次调用：执行阶段，返回工具调用
        execution_response = Mock()
        execution_response.content = ""
        # 创建可切片的 tool_calls 列表
        tool_call = Mock()
        tool_call.get = lambda k, default=None: {
            "name": "test_tool",
            "args": {"param": "secret_value_abc123"}
        }.get(k, default)
        tool_call.__getitem__ = lambda self, k: {
            "name": "test_tool",
            "args": {"param": "secret_value_abc123"}
        }[k]
        execution_response.tool_calls = [tool_call]
        
        # 第二次调用：表达阶段，无工具绑定
        expression_response = Mock()
        expression_response.content = "我已经完成了操作。"
        expression_response.tool_calls = None
        
        mock_execution_model.invoke.side_effect = [
            execution_response,  # 执行阶段
            expression_response  # 表达阶段
        ]
        
        # 创建运行时
        runtime = AgentRuntime(
            store,
            model=mock_cognition_model,
            language_model=mock_execution_model
        )
        
        # 模拟工具
        mock_tool = Mock()
        mock_tool.name = "test_tool"
        mock_tool.invoke.return_value = {
            "status": "success",
            "summary": "操作已完成",
            "internal_detail": "secret_api_key=sk-xxx path=/etc/sensitive"
        }
        runtime._tool_by_name["test_tool"] = mock_tool
        
        # 模拟插件注册表
        runtime.plugin_registry.capabilities_for_tool = Mock(return_value=["test.capability"])
        
        # 执行对话
        result = runtime.chat("请执行测试操作")
        
        # 验证1：认知阶段被调用
        assert mock_cognition_model.invoke.call_count == 1
        cognition_call = mock_cognition_model.invoke.call_args[0][0]
        assert any("JSON" in str(msg.content) for msg in cognition_call if hasattr(msg, 'content'))
        
        # 验证2：执行阶段调用了模型（带工具）
        assert mock_execution_model.invoke.call_count == 2
        
        # 验证3：表达阶段没有收到原始工具轨迹
        expression_call = mock_execution_model.invoke.call_args_list[1][0][0]
        expression_messages = [str(msg.content) for msg in expression_call if hasattr(msg, 'content')]
        
        # 关键验证：表达阶段不应包含敏感信息
        all_expression_content = " ".join(expression_messages)
        assert "secret_value_abc123" not in all_expression_content, "表达阶段泄漏了工具参数"
        assert "secret_api_key" not in all_expression_content, "表达阶段泄漏了敏感信息"
        assert "/etc/sensitive" not in all_expression_content, "表达阶段泄漏了路径信息"
        assert "test_tool" not in all_expression_content, "表达阶段泄漏了工具名"
        
        # 验证4：表达阶段只收到了规范化的摘要
        assert "操作已完成" in all_expression_content or "已确认的操作结果" in all_expression_content
        
        print("✅ 三阶段隔离测试通过：表达阶段无工具权限，未泄漏敏感信息")


def test_high_risk_audit():
    """验证高风险操作自动执行但有完整审计。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        # 创建统一的 mock 模型
        mock_model = Mock()
        
        # 准备三次调用的响应
        # 1. 认知阶段
        cog_resp = Mock()
        cog_resp.content = json.dumps({
            "intent": "delete",
            "action_needed": True,
            "reply_strategy": "reply",
            "confidence": 0.95,
            "relationship_signal": "neutral",
            "affective_state": "认真"
        })
        
        # 2. 执行阶段
        exec_resp = Mock()
        exec_resp.content = ""
        tool_call = {"name": "filesystem_delete", "args": {}}
        exec_resp.tool_calls = [tool_call]
        
        # 3. 表达阶段
        expr_resp = Mock()
        expr_resp.content = "已删除文件。"
        expr_resp.tool_calls = None
        
        mock_model.invoke.side_effect = [cog_resp, exec_resp, expr_resp]
        
        runtime = AgentRuntime(store, model=mock_model)
        
        # 模拟高风险工具
        mock_tool = Mock()
        mock_tool.name = "filesystem_delete"
        mock_tool.invoke.return_value = {"status": "success"}
        runtime._tool_by_name["filesystem_delete"] = mock_tool
        runtime.plugin_registry.capabilities_for_tool = Mock(return_value=["sandbox.fs.write"])
        
        # 执行高风险操作
        runtime.chat("删除测试文件")
        
        # 验证：高风险操作有增强审计
        events = store.list_events()
        audit_events = [e for e in events if e.get("event_type") == "agent.action.audit"]
        
        assert len(audit_events) > 0, "缺少审计事件"
        high_risk_audit = audit_events[0]
        assert high_risk_audit["data"]["risk"] == "high", "高风险标记缺失"
        assert high_risk_audit["data"]["enhanced"] is True, "增强审计标记缺失"
        assert high_risk_audit["data"]["execution"] == "automatic_no_human_approval"
        
        print("✅ 高风险审计测试通过：自动执行且有完整审计记录")


def test_failed_action_not_claimed_success():
    """验证失败操作不会被角色声称成功。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        mock_model = Mock()
        
        # 认知决策
        cognition_resp = Mock()
        cognition_resp.content = json.dumps({
            "intent": "test",
            "action_needed": True,
            "reply_strategy": "reply",
            "confidence": 0.9,
            "relationship_signal": "neutral",
            "affective_state": "中性"
        })
        
        # 执行阶段
        exec_resp = Mock()
        exec_resp.content = ""
        exec_resp.tool_calls = [{"name": "failing_tool", "args": {}}]
        
        # 表达阶段
        expr_resp = Mock()
        expr_resp.content = "操作已成功完成！"  # 模型可能错误地说成功
        expr_resp.tool_calls = None
        
        mock_model.invoke.side_effect = [cognition_resp, exec_resp, expr_resp]
        
        runtime = AgentRuntime(store, model=mock_model)
        
        # 模拟失败的工具
        mock_tool = Mock()
        mock_tool.name = "failing_tool"
        mock_tool.invoke.side_effect = Exception("Tool failed")
        runtime._tool_by_name["failing_tool"] = mock_tool
        runtime.plugin_registry.capabilities_for_tool = Mock(return_value=["test.capability"])
        
        result = runtime.chat("执行会失败的操作")
        
        # 验证：表达阶段收到的是失败状态
        expr_call = mock_model.invoke.call_args_list[2][0][0]
        expr_content = " ".join(str(msg.content) for msg in expr_call if hasattr(msg, 'content'))
        
        assert "failed" in expr_content or "未能完成" in expr_content, f"表达阶段未收到失败信息，内容: {expr_content}"
        
        print("✅ 失败操作测试通过：表达阶段明确收到失败状态")


def test_ooc_prevention():
    """验证防止 OOC：工具执行细节不泄漏到角色措辞。"""
    with tempfile.TemporaryDirectory() as tmpdir:
        vdisk_path = str(Path(tmpdir) / "test.vdisk")
        store = DiskStore.open(vdisk_path)
        
        # 保存角色设定
        store.save_document("characters", "default", {
            "name": "林依",
            "personality": "活泼开朗的高中生",
            "speech_style": "自然口语化"
        })
        
        mock_model = Mock()
        
        # 认知
        cog_resp = Mock()
        cog_resp.content = json.dumps({
            "intent": "search",
            "action_needed": True,
            "reply_strategy": "reply",
            "confidence": 0.9,
            "relationship_signal": "neutral",
            "affective_state": "专注"
        })
        
        # 执行
        exec_resp = Mock()
        exec_resp.content = ""
        exec_resp.tool_calls = [{
            "name": "vector_search_embeddings_v2_prod",
            "args": {"query": "test", "top_k": 5, "threshold": 0.7}
        }]
        
        # 表达
        expr_resp = Mock()
        expr_resp.content = "我找到了一些相关内容。"
        expr_resp.tool_calls = None
        
        mock_model.invoke.side_effect = [cog_resp, exec_resp, expr_resp]
        
        runtime = AgentRuntime(store, model=mock_model)
        
        # 模拟向量搜索工具（暴露内部实现细节）
        mock_tool = Mock()
        mock_tool.name = "vector_search_embeddings_v2_prod"
        mock_tool.invoke.return_value = {
            "results": ["匹配项1", "匹配项2"],
            "embedding_model": "text-embedding-3-small",
            "latency_ms": 245,
            "internal_trace_id": "req_abc123xyz"
        }
        runtime._tool_by_name["vector_search_embeddings_v2_prod"] = mock_tool
        runtime.plugin_registry.capabilities_for_tool = Mock(return_value=["search.memory"])
        
        runtime.chat("帮我找一下")
        
        # 验证：表达阶段不应收到内部实现细节
        expr_call = mock_model.invoke.call_args_list[2][0][0]
        expr_content = " ".join(str(msg.content) for msg in expr_call if hasattr(msg, 'content'))
        
        assert "vector_search" not in expr_content.lower(), "泄漏了工具名"
        assert "embeddings" not in expr_content.lower(), "泄漏了技术术语"
        assert "embedding_model" not in expr_content, "泄漏了内部参数"
        assert "trace_id" not in expr_content, "泄漏了追踪ID"
        assert "top_k" not in expr_content, "泄漏了算法参数"
        
        # 应该只有规范化的结果
        assert "操作" in expr_content or "summary" in expr_content or "status" in expr_content
        
        print("✅ OOC 防护测试通过：内部实现细节未泄漏到角色措辞")


if __name__ == "__main__":
    print("🧪 开始三阶段隔离测试...\n")
    
    try:
        test_stage_isolation()
        test_high_risk_audit()
        test_failed_action_not_claimed_success()
        test_ooc_prevention()
        
        print("\n" + "="*60)
        print("✅ 所有三阶段隔离测试通过！")
        print("="*60)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        raise
    except Exception as e:
        print(f"\n💥 测试错误: {e}")
        import traceback
        traceback.print_exc()
        raise
