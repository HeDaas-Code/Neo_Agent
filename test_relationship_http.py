"""通过 HTTP over Unix socket 测试关系服务"""
import asyncio
import json
import aiohttp
import os

SOCKET_PATH = os.path.expanduser("~/.neo_agent/agent.sock")

async def send_request(method: str, params: dict = None) -> dict:
    """发送 JSON-RPC 请求"""
    connector = aiohttp.UnixConnector(path=SOCKET_PATH)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": 1
        }
        
        async with session.post("http://localhost/rpc", json=request) as response:
            return await response.json()

async def test_relationship():
    """测试关系功能"""
    
    print("=" * 60)
    print("关系服务集成测试")
    print("=" * 60)
    
    # 1. 发送对话消息
    print("\n【1/4】发送对话消息...")
    
    messages = [
        "你好林依，今天天气真好",
        "谢谢你一直陪伴我",
        "和你聊天很开心",
    ]
    
    for i, msg in enumerate(messages, 1):
        print(f"  消息 {i}: {msg}")
        response = await send_request("session.send_message", {"text": msg})
        
        if "result" in response:
            reply = response["result"].get("reply", "")
            print(f"  回复: {reply[:50]}...")
        else:
            error = response.get("error", {})
            print(f"  错误: {error.get('message', 'Unknown')}")
        
        await asyncio.sleep(0.5)
    
    # 2. 查询关系状态
    print("\n【2/4】查询关系状态...")
    response = await send_request("relationship.get_status", {"entity": "user"})
    
    if "result" in response:
        status = response["result"]
        print(f"  当前分数: {status.get('score', 0)}")
        print(f"  阶段: {status.get('stage', 'unknown')}")
        print(f"  印象: {status.get('impression', 'N/A')}")
    else:
        error = response.get("error", {})
        print(f"  错误: {error.get('message', 'Unknown')}")
    
    # 3. 查询关系历史
    print("\n【3/4】查询关系历史...")
    response = await send_request("relationship.get_history", {
        "entity": "user",
        "limit": 10
    })
    
    if "result" in response:
        history = response["result"]
        print(f"  历史记录数: {len(history)}")
        
        for i, record in enumerate(history[-3:], 1):
            print(f"  [{i}] 信号: {record.get('signal_type')}, "
                  f"分数变化: {record.get('score_delta'):+d}, "
                  f"置信度: {record.get('confidence'):.2f}")
    else:
        error = response.get("error", {})
        print(f"  错误: {error.get('message', 'Unknown')}")
    
    # 4. 列出所有关系
    print("\n【4/4】列出所有关系...")
    response = await send_request("relationship.list_all", {})
    
    if "result" in response:
        all_rels = response["result"]
        print(f"  关系总数: {len(all_rels.get('relationships', []))}")
    else:
        error = response.get("error", {})
        print(f"  错误: {error.get('message', 'Unknown')}")
    
    print("\n" + "=" * 60)
    print("✓ 关系服务集成测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_relationship())
