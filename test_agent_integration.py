"""测试 Agent 集成"""
import asyncio
import aiohttp
import json
from pathlib import Path

async def test_agent_chat():
    """测试 Agent 对话功能"""
    socket_path = Path.home() / ".neo_agent" / "agent.sock"
    
    if not socket_path.exists():
        print("❌ 服务未运行")
        return
    
    # 创建 Unix socket 连接
    connector = aiohttp.UnixConnector(path=str(socket_path))
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 1. 获取角色信息
        print("📋 测试 1: 获取角色信息")
        resp = await session.post(
            "http://unix/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "character.get_profile",
                "params": {},
                "id": 1
            }
        )
        result = await resp.json()
        character = result.get("result", {})
        print(f"✓ 角色: {character.get('name')} ({character.get('age')}岁)")
        print(f"  性格: {', '.join(character.get('personality', []))}")
        print()
        
        # 2. 发送消息给 Agent
        print("💬 测试 2: 发送消息给 Agent")
        test_message = "你好，你在做什么？"
        print(f"用户: {test_message}")
        
        resp = await session.post(
            "http://unix/rpc",
            json={
                "jsonrpc": "2.0",
                "method": "session.send_message",
                "params": {"text": test_message},
                "id": 2
            }
        )
        result = await resp.json()
        
        if "result" in result:
            reply_data = result["result"]
            reply = reply_data.get("reply", "")
            emotion = reply_data.get("emotion", {})
            
            print(f"林依: {reply}")
            print(f"情绪: {emotion.get('state', 'unknown')} (强度: {emotion.get('intensity', 0)})")
            
            # 判断是否使用了真实 Agent
            if "Mock" in reply or "收到消息" in reply:
                print("\n⚠ 当前使用 Mock 响应（未配置 LLM API Key）")
            else:
                print("\n✓ Agent 运行时已成功集成！")
        else:
            print(f"❌ 错误: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(test_agent_chat())
