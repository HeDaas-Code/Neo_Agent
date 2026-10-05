"""启动 TUI 进行手动测试"""
import asyncio
from neo_agent.ui.v2.app import NeoAgentApp

async def main():
    app = NeoAgentApp()
    await app.run_async()

if __name__ == "__main__":
    asyncio.run(main())
