"""直接测试 RPC 连接"""
import asyncio
import aiohttp
from aiohttp import UnixConnector

async def test_rpc():
    """测试 RPC 调用"""
    socket_path = "/home/hedass/.neo_agent/agent.sock"
    
    connector = UnixConnector(path=socket_path)
    
    async with aiohttp.ClientSession(connector=connector) as session:
        request = {
            "jsonrpc": "2.0",
            "method": "character.get_profile",
            "params": {},
            "id": 1
        }
        
        try:
            async with session.post("http://localhost/rpc", json=request) as resp:
                result = await resp.json()
                print("✓ RPC 调用成功!")
                print(f"响应: {result}")
                
                if "result" in result:
                    profile = result["result"]
                    print(f"\n角色信息:")
                    print(f"  名字: {profile.get('name')}")
                    print(f"  年龄: {profile.get('age')}")
                    print(f"  性别: {profile.get('gender')}")
                    
        except Exception as e:
            print(f"❌ RPC 调用失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_rpc())
