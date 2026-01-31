"""
演示日程相似度检查功能

该脚本演示了新增的日程相似度检查功能：
1. 创建日程时自动检查当天是否有相似日程
2. 使用LLM判断哪个日程应该保留
3. 自动删除较不详细的日程，保留更详细的日程
"""

import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.core.schedule_manager import ScheduleManager, ScheduleType
from src.core.database_manager import DatabaseManager


def demo_similarity_check():
    """演示日程相似度检查"""
    print("=" * 70)
    print("日程相似度检查功能演示")
    print("=" * 70)
    print()
    
    # 创建管理器（使用内存数据库演示）
    db = DatabaseManager(':memory:')
    manager = ScheduleManager(db)
    
    print("📝 场景1: 创建第一个日程")
    print("-" * 70)
    
    success1, schedule1, msg1 = manager.create_schedule(
        title="团队会议",
        description="讨论项目进度",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time="2024-01-15T10:00:00",
        end_time="2024-01-15T11:00:00",
        check_similarity=False  # 第一个不检查
    )
    
    print(f"结果: {'✓ 成功' if success1 else '✗ 失败'}")
    print(f"消息: {msg1}")
    if schedule1:
        print(f"日程ID: {schedule1.schedule_id[:8]}...")
    print()
    
    print("📝 场景2: 尝试创建相似但更详细的日程（同一天）")
    print("-" * 70)
    print("说明: 系统将使用LLM判断这个新日程与已有的「团队会议」是否相似")
    print()
    
    success2, schedule2, msg2 = manager.create_schedule(
        title="项目进度讨论会议",
        description="与团队成员讨论本周项目进度，包括开发、测试、部署各个环节的情况，制定下周计划",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time="2024-01-15T14:00:00",
        end_time="2024-01-15T15:00:00",
        check_similarity=True  # 启用相似度检查
    )
    
    print(f"结果: {'✓ 成功' if success2 else '✗ 失败'}")
    print(f"消息: {msg2}")
    if schedule2:
        print(f"日程ID: {schedule2.schedule_id[:8]}...")
    print()
    
    print("📝 场景3: 创建明显不同的日程（同一天）")
    print("-" * 70)
    print("说明: 这个日程与之前的会议主题不同，应该不会被判定为相似")
    print()
    
    success3, schedule3, msg3 = manager.create_schedule(
        title="下午茶时间",
        description="和朋友一起喝下午茶，放松一下",
        schedule_type=ScheduleType.TEMPORARY,
        start_time="2024-01-15T16:00:00",
        end_time="2024-01-15T17:00:00",
        check_similarity=True
    )
    
    print(f"结果: {'✓ 成功' if success3 else '✗ 失败'}")
    print(f"消息: {msg3}")
    if schedule3:
        print(f"日程ID: {schedule3.schedule_id[:8]}...")
    print()
    
    print("📝 场景4: 创建另一天的相似日程")
    print("-" * 70)
    print("说明: 虽然主题相似，但不在同一天，不会触发相似度检查")
    print()
    
    success4, schedule4, msg4 = manager.create_schedule(
        title="团队会议",
        description="讨论项目进度",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time="2024-01-16T10:00:00",  # 第二天
        end_time="2024-01-16T11:00:00",
        check_similarity=True
    )
    
    print(f"结果: {'✓ 成功' if success4 else '✗ 失败'}")
    print(f"消息: {msg4}")
    if schedule4:
        print(f"日程ID: {schedule4.schedule_id[:8]}...")
    print()
    
    # 查询所有日程
    print("📊 当前所有日程汇总")
    print("-" * 70)
    
    from datetime import datetime, timedelta
    start = datetime(2024, 1, 15, 0, 0, 0).isoformat()
    end = datetime(2024, 1, 17, 0, 0, 0).isoformat()
    
    all_schedules = manager.get_schedules_by_time_range(
        start_time=start,
        end_time=end,
        queryable_only=False,
        active_only=True
    )
    
    print(f"共有 {len(all_schedules)} 个激活的日程：")
    print()
    
    for i, schedule in enumerate(all_schedules, 1):
        print(f"{i}. 【{schedule.title}】")
        print(f"   描述: {schedule.description}")
        print(f"   时间: {schedule.start_time} ~ {schedule.end_time}")
        print(f"   类型: {schedule.schedule_type.value}")
        print()
    
    print("=" * 70)
    print("演示完成！")
    print("=" * 70)
    print()
    print("💡 功能说明：")
    print("- 创建日程时设置 check_similarity=True 可启用相似度检查")
    print("- 系统会使用LLM分析当天已有日程，判断是否相似")
    print("- 如果相似，LLM会选择保留信息更详细的日程")
    print("- 相似度检查仅在同一天内进行，不同日期的日程互不影响")
    print()
    print("⚠️  注意：")
    print("- 该功能依赖LLM API (SiliconFlow)")
    print("- 如果API不可用或超时，会跳过相似度检查，直接创建日程")
    print("- 可以通过 check_similarity=False 禁用相似度检查")
    print()


if __name__ == '__main__':
    try:
        demo_similarity_check()
    except KeyboardInterrupt:
        print("\n\n演示已中断")
    except Exception as e:
        print(f"\n\n演示过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
