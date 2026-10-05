"""
测试关系信号捕获
"""
import asyncio
import sys
sys.path.insert(0, '/home/hedass/桌面/Lien_os')

from neo_agent.ui.v2.client import AgentClient

async def test_relationship():
    client = AgentClient()
    await client.connect()
    
    if not client.connected:
        print("❌ 无法连接服务")
        return
    
    print("✅ 已连接服务")
    print("━" * 60)
    
    # 发送一条明显带有情感的消息
    test_message = "你今天真棒！帮了我大忙，我很感激你。"
    print(f"📤 用户: {test_message}")
    
    result = await client.call("session.send_message", {"text": test_message})
    reply = result.get("reply", "")
    print(f"📥 林依: {reply}")
    print("━" * 60)
    
    # 等待一下让关系更新
    await asyncio.sleep(2)
    
    # 查询关系状态
    print("\n检查关系状态...")
    rel_result = await client.call("relationship.list_all", {})
    relationships = rel_result.get("relationships", [])
    
    if relationships:
        print(f"✅ 找到 {len(relationships)} 个关系:")
        for rel in relationships:
            print(f"  - {rel.get('entity')}: 分数 {rel.get('score')}")
    else:
        print("⚠️  没有找到关系记录")
    
    # 查询关系历史
    print("\n检查关系历史...")
    history_result = await client.call("relationship.get_history", {
        "entity": "user",
        "limit": 10
    })
    history = history_result.get("history", [])
    
    if history:
        print(f"✅ 找到 {len(history)} 条历史记录:")
        for h in history:
            print(f"  - {h.get('timestamp')}: {h.get('signal')} (delta: {h.get('score_delta')}, confidence: {h.get('confidence')})")
            print(f"    原因: {h.get('reason')}")
    else:
        print("⚠️  没有找到历史记录")
    
    await client.close()

if __name__ == "__main__":
    asyncio.run(test_relationship())
