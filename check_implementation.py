"""检查日程场景系统的实现状态"""
import os

print("📋 检查日程场景系统实现状态\n")

files_to_check = [
    ("neo_agent/runtime/itinerary.py", "完整日程场景系统"),
    ("neo_agent/runtime/daily_itinerary.py", "每日行程生成"),
    ("neo_agent/runtime/scene_scheduler.py", "场景调度器"),
    ("neo_agent/runtime/scene_generation.py", "场景生成"),
    ("neo_agent/runtime/scene.py", "场景服务"),
    ("neo_agent/runtime/schedule.py", "日程服务"),
]

print("✅ 已实现的模块：")
for filepath, desc in files_to_check:
    if os.path.exists(filepath):
        size = os.path.getsize(filepath)
        lines = len(open(filepath).readlines())
        print(f"  ✓ {desc:20} ({filepath}) - {lines} 行, {size} 字节")
    else:
        print(f"  ✗ {desc:20} ({filepath}) - 不存在")

print("\n📊 RPC API 端点：")
import re
rpc_file = "neo_agent/service/rpc_handlers.py"
if os.path.exists(rpc_file):
    content = open(rpc_file).read()
    methods = re.findall(r'async def (\w+)\(self', content)
    
    schedule_methods = [m for m in methods if 'schedule' in m.lower()]
    scene_methods = [m for m in methods if 'scene' in m.lower()]
    
    print(f"  日程相关: {', '.join(schedule_methods)}")
    print(f"  场景相关: {', '.join(scene_methods)}")

print("\n🔧 服务守护进程集成：")
daemon_file = "neo_agent/service/agent_daemon.py"
if os.path.exists(daemon_file):
    content = open(daemon_file).read()
    
    if 'SceneScheduler' in content:
        print("  ✓ SceneScheduler 已集成")
    else:
        print("  ✗ SceneScheduler 未集成到守护进程")
    
    if 'DailyItineraryService' in content:
        print("  ✓ DailyItineraryService 已集成")
    else:
        print("  ✗ DailyItineraryService 未集成到守护进程")
    
    if 'schedule' in content:
        print("  ✓ ScheduleService 已在服务字典中")
    if 'scene' in content:
        print("  ✓ SceneService 已在服务字典中")

print("\n💡 结论：")
print("  代码已编写，但调度器(SceneScheduler, DailyItineraryService)")
print("  尚未集成到守护进程的后台 worker 中")
