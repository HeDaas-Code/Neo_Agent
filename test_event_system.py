#!/usr/bin/env python
"""
事件系统测试脚本
演示通知型和任务型事件的创建和管理
"""

from chat_agent import ChatAgent
from event_manager import EventType, EventPriority
import sys

def test_notification_event(agent):
    """测试通知型事件"""
    print("\n" + "="*60)
    print("测试 1: 通知型事件")
    print("="*60)
    
    # 创建通知事件
    event = agent.event_manager.create_event(
        title="系统更新通知",
        description="Neo Agent v2.0 已发布！新增事件驱动功能、多智能体协作和中断性提问工具。",
        event_type=EventType.NOTIFICATION,
        priority=EventPriority.HIGH
    )
    
    print(f"✓ 通知事件已创建")
    print(f"  - ID: {event.event_id[:8]}...")
    print(f"  - 标题: {event.title}")
    print(f"  - 优先级: {event.priority.name}")
    print(f"  - 状态: {event.status.name}")
    
    return event

def test_task_event(agent):
    """测试任务型事件"""
    print("\n" + "="*60)
    print("测试 2: 任务型事件")
    print("="*60)
    
    # 创建任务事件
    event = agent.event_manager.create_event(
        title="生成系统功能报告",
        description="根据当前系统功能生成一份完整的功能报告文档",
        event_type=EventType.TASK,
        priority=EventPriority.MEDIUM,
        task_requirements="""
        1. 列出所有主要功能模块
        2. 描述每个模块的核心功能
        3. 说明模块之间的协作关系
        """,
        completion_criteria="""
        报告应包含：
        - 系统架构概述
        - 功能模块列表
        - 模块功能说明
        - 协作流程图（文字描述）
        """
    )
    
    print(f"✓ 任务事件已创建")
    print(f"  - ID: {event.event_id[:8]}...")
    print(f"  - 标题: {event.title}")
    print(f"  - 优先级: {event.priority.name}")
    print(f"  - 状态: {event.status.name}")
    print(f"  - 任务要求: {event.metadata.get('task_requirements', '')[:50]}...")
    
    return event

def test_event_management(agent):
    """测试事件管理功能"""
    print("\n" + "="*60)
    print("测试 3: 事件管理功能")
    print("="*60)
    
    # 获取统计信息
    stats = agent.get_event_statistics()
    print(f"\n📊 事件统计:")
    print(f"  - 总事件数: {stats['total_events']}")
    print(f"  - 待处理: {stats['pending']}")
    print(f"  - 处理中: {stats['processing']}")
    print(f"  - 已完成: {stats['completed']}")
    print(f"  - 通知型: {stats['notifications']}")
    print(f"  - 任务型: {stats['tasks']}")
    
    # 获取待处理事件列表
    pending = agent.get_pending_events()
    print(f"\n📋 待处理事件列表 (共{len(pending)}个):")
    for i, event_dict in enumerate(pending, 1):
        print(f"  {i}. [{event_dict['event_type']}] {event_dict['title']}")
        print(f"     优先级: {event_dict['priority']}, 状态: {event_dict['status']}")

def main():
    print("="*60)
    print("Neo Agent 事件系统测试")
    print("="*60)
    
    # 初始化代理
    print("\n正在初始化 ChatAgent...")
    agent = ChatAgent()
    
    try:
        # 测试通知型事件
        test_notification_event(agent)
        
        # 测试任务型事件
        test_task_event(agent)
        
        # 测试事件管理
        test_event_management(agent)
        
        print("\n" + "="*60)
        print("✅ 所有测试完成!")
        print("="*60)
        
        print("\n💡 提示:")
        print("  1. 启动 GUI: python gui_enhanced.py")
        print("  2. 打开「事件管理」标签页")
        print("  3. 选择事件并点击「🚀 触发事件」")
        print("  4. 查看智能体的处理结果")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
