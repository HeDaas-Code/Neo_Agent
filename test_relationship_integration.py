"""测试关系服务的完整集成"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.service.client import AgentClient

async def test_relationship_flow():
    """测试关系信号记录到持久化的完整流程"""
    
    print("=" * 60)
    print("关系服务集成测试")
    print("=" * 60)
    
    async with AgentClient() as client:
        
        # 1. 发送多条消息，触发不同的关系信号
        print("\n【1/4】发送对话消息...")
        
        messages = [
            "你好林依，今天天气真好",
            "谢谢你一直陪伴我",
            "和你聊天很开心",
        ]
        
        for i, msg in enumerate(messages, 1):
            print(f"  消息 {i}: {msg}")
            response = await client.request("session.send_message", {"text": msg})
            print(f"  回复: {response.get('reply', '')[:50]}...")
            await asyncio.sleep(0.5)
        
        # 2. 查询关系状态
        print("\n【2/4】查询当前关系状态...")
        status = await client.request("relationship.get_status", {"entity": "user"})
        print(f"  当前分数: {status.get('score', 0)}")
        print(f"  阶段: {status.get('stage', 'unknown')}")
        print(f"  印象: {status.get('impression', 'N/A')}")
        
        # 3. 查询关系历史
        print("\n【3/4】查询关系变化历史...")
        history = await client.request("relationship.get_history", {
            "entity": "user",
            "limit": 10
        })
        
        if history:
            print(f"  历史记录数: {len(history)}")
            for i, record in enumerate(history[-3:], 1):
                print(f"  [{i}] 信号: {record.get('signal_type')}, "
                      f"分数变化: {record.get('score_delta'):+d}, "
                      f"置信度: {record.get('confidence'):.2f}")
        else:
            print("  暂无历史记录")
        
        # 4. 列出所有关系
        print("\n【4/4】列出所有关系...")
        all_rels = await client.request("relationship.list_all", {})
        print(f"  关系总数: {len(all_rels.get('relationships', []))}")
        
        print("\n" + "=" * 60)
        print("✓ 关系服务集成测试完成")
        print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_relationship_flow())
