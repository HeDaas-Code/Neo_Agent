"""模拟守护进程用于测试 TUI"""
import asyncio
import json
from pathlib import Path
from datetime import datetime


class MockDaemon:
    """模拟服务端，用于测试 TUI 功能"""
    
    def __init__(self):
        self.socket_path = Path.home() / ".neo_agent" / "agent.sock"
        self.character = {
            "id": "char_001",
            "name": "林依",
            "gender": "女",
            "age": 18,
            "personality": ["温柔", "善良", "活泼"],
            "backstory": "一个喜欢阅读和旅行的高中生"
        }
        self.current_scene = {
            "location": "家-客厅",
            "description": "温馨的客厅，有柔软的沙发和书架",
            "areas": ["沙发区", "书架", "茶几"],
            "objects": ["书籍", "茶杯", "抱枕"]
        }
        self.emotion = {
            "state": "平静",
            "intensity": 0.6,
            "timestamp": datetime.now().isoformat()
        }
        self.history = [
            {
                "role": "user",
                "content": "你好，林依！",
                "timestamp": "14:20"
            },
            {
                "role": "assistant",
                "content": "你好呀！很高兴见到你~",
                "timestamp": "14:20"
            }
        ]
        self.itinerary = [
            {
                "time": "08:00-09:00",
                "activity": "早餐",
                "location": "家-厨房",
                "owner": "agent",
                "scene_id": "scene_001"
            },
            {
                "time": "09:00-12:00",
                "activity": "阅读",
                "location": "家-书房",
                "owner": "agent",
                "scene_id": "scene_002"
            },
            {
                "time": "14:00-16:00",
                "activity": "陪伴用户",
                "location": "家-客厅",
                "owner": "shared",
                "scene_id": "scene_003"
            }
        ]
        self.scenes = [
            {
                "location": "家-客厅",
                "visit_count": 15,
                "last_visit": "2026-10-05 14:00"
            },
            {
                "location": "家-书房",
                "visit_count": 8,
                "last_visit": "2026-10-05 09:00"
            },
            {
                "location": "家-厨房",
                "visit_count": 12,
                "last_visit": "2026-10-05 08:00"
            }
        ]
        self.audit_logs = [
            {
                "timestamp": "2026-10-05 14:15:23",
                "action": "场景切换",
                "risk_level": "low",
                "result": "从书房切换到客厅"
            },
            {
                "timestamp": "2026-10-05 14:10:05",
                "action": "创建日程",
                "risk_level": "medium",
                "result": "自动生成今日行程"
            }
        ]
    
    async def handle_rpc(self, method: str, params: dict = None) -> dict:
        """处理 RPC 调用"""
        params = params or {}
        
        handlers = {
            "character.get_profile": lambda: {"result": self.character},
            "scene.get_current": lambda: {"result": self.current_scene},
            "emotion.get_current": lambda: {"result": self.emotion},
            "session.get_history": lambda: {"result": self.history},
            "schedule.get_today_itinerary": lambda: {"result": self.itinerary},
            "scene.list_pool": lambda: {"result": self.scenes},
            "audit.get_logs": lambda: {"result": self.audit_logs},
            "memory.search": lambda: {"result": [
                {
                    "content": "用户喜欢看科幻小说",
                    "relevance": 0.95,
                    "timestamp": "2026-10-04"
                },
                {
                    "content": "林依喜欢安静的环境",
                    "relevance": 0.88,
                    "timestamp": "2026-10-03"
                }
            ]},
            "relationship.get_status": lambda: {"result": {
                "entity": "用户",
                "score": 85,
                "history": []
            }},
        }
        
        handler = handlers.get(method)
        if handler:
            return handler()
        else:
            return {"error": {"code": -32601, "message": f"Method not found: {method}"}}
    
    async def start(self):
        """启动模拟服务"""
        self.socket_path.parent.mkdir(parents=True, exist_ok=True)
        
        if self.socket_path.exists():
            self.socket_path.unlink()
        
        server = await asyncio.start_unix_server(
            self.handle_client,
            path=str(self.socket_path)
        )
        
        print(f"✓ 模拟服务已启动: {self.socket_path}")
        
        async with server:
            await server.serve_forever()
    
    async def handle_client(self, reader, writer):
        """处理客户端连接"""
        try:
            while True:
                data = await reader.readline()
                if not data:
                    break
                
                try:
                    request = json.loads(data.decode())
                    method = request.get("method")
                    params = request.get("params", {})
                    request_id = request.get("id")
                    
                    result = await self.handle_rpc(method, params)
                    
                    response = {
                        "jsonrpc": "2.0",
                        "id": request_id,
                        **result
                    }
                    
                    writer.write(json.dumps(response).encode() + b'\n')
                    await writer.drain()
                    
                except json.JSONDecodeError:
                    pass
        except Exception as e:
            print(f"客户端处理错误: {e}")
        finally:
            writer.close()
            await writer.wait_closed()


async def main():
    """启动模拟服务"""
    daemon = MockDaemon()
    await daemon.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✓ 模拟服务已停止")
