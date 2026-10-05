"""简单测试 RPC handler"""
import asyncio
import sys
from pathlib import Path

# 加载环境变量
env_file = Path(__file__).parent / ".env"
if env_file.exists():
    import os
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())

from neo_agent.storage import DiskStore
from neo_agent.service.rpc_handlers import RPCHandlers
from neo_agent.service.events import EventBroadcaster

async def test():
    # 初始化存储
    vdisk_path = Path.home() / ".neo_agent" / "data.vdisk"
    store = DiskStore.open(str(vdisk_path))
    
    # 初始化广播器
    broadcaster = EventBroadcaster()
    await broadcaster.start()
    
    # 初始化 RPC 处理器
    handlers = RPCHandlers(store, broadcaster)
    
    print("测试 session.send_message...")
    try:
        result = await handlers.session_send_message({"text": "你好"})
        print(f"✓ 成功: {result.get('reply', '')[:50]}")
    except Exception as e:
        print(f"✗ 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await broadcaster.stop()
        store.close()

if __name__ == "__main__":
    asyncio.run(test())
