"""测试通过 Unix socket 调用 RPC"""
import asyncio
import json
from pathlib import Path
import aiohttp
from aiohttp import UnixConnector

async def test():
    socket_path = Path.home() / ".neo_agent" / "agent.sock"
    
    connector = UnixConnector(path=str(socket_path))
    
    async with aiohttp.ClientSession(connector=connector) as session:
        # 构造 JSON-RPC 请求
        payload = {
            "jsonrpc": "2.0",
            "method": "session.send_message",
            "params": {"text": "你好"},
            "id": 1
        }
        
        print("发送 RPC 请求...")
        try:
            async with session.post("http://localhost/rpc", json=payload, timeout=aiohttp.ClientTimeout(total=60)) as resp:
                result = await resp.json()
                print(f"状态码: {resp.status}")
                print(f"响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        except asyncio.TimeoutError:
            print("✗ 超时")
        except Exception as e:
            print(f"✗ 错误: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test())
