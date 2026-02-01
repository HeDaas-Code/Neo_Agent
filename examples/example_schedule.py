"""
日程管理功能示例脚本
演示如何使用日程管理系统
"""

from datetime import datetime, timedelta
from src.core.schedule_manager import (
    ScheduleManager, ScheduleType, SchedulePriority
)
from src.core.database_manager import DatabaseManager


def print_separator():
    """打印分隔线"""
    print("=" * 60)


def example_create_schedules():
    """示例：创建不同类型的日程"""
    print_separator()
    print("示例 1: 创建不同类型的日程")
    print_separator()
    
    # 初始化数据库和日程管理器
    db = DatabaseManager("example_schedule.db")
    manager = ScheduleManager(db)
    
    # 获取今天和明天的日期
    today = datetime.now().date()
    tomorrow = today + timedelta(days=1)
    
    # 1. 创建周期日程（如课程表）
    print("\n1. 创建周期日程：英语课")
    start_time = datetime.combine(today, datetime.min.time()).replace(hour=9, minute=0)
    end_time = start_time.replace(hour=11, minute=0)
    
    success, schedule, message = manager.create_schedule(
        title="英语课",
        description="每周一的英语课",
        schedule_type=ScheduleType.RECURRING,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        weekday=0,  # 周一
        recurrence_pattern="每周一"
    )
    
    print(f"   结果: {message}")
    if success:
        print(f"   日程ID: {schedule.schedule_id}")
        print(f"   优先级: {schedule.priority.name}")
    
    # 2. 创建预约日程
    print("\n2. 创建预约日程：团队会议")
    start_time = datetime.combine(tomorrow, datetime.min.time()).replace(hour=14, minute=0)
    end_time = start_time + timedelta(hours=2)
    
    success, schedule, message = manager.create_schedule(
        title="团队会议",
        description="讨论项目进展",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        priority=SchedulePriority.HIGH
    )
    
    print(f"   结果: {message}")
    if success:
        print(f"   日程ID: {schedule.schedule_id}")
    
    # 3. 创建临时日程
    print("\n3. 创建临时日程：阅读时光")
    start_time = datetime.combine(today, datetime.min.time()).replace(hour=15, minute=0)
    end_time = start_time + timedelta(hours=1, minutes=30)
    
    success, schedule, message = manager.create_schedule(
        title="阅读时光",
        description="读一本喜欢的书",
        schedule_type=ScheduleType.TEMPORARY,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        generated_reason="空闲时间自动生成"
    )
    
    print(f"   结果: {message}")
    if success:
        print(f"   日程ID: {schedule.schedule_id}")
        print(f"   优先级: {schedule.priority.name}")


def example_conflict_detection():
    """示例：日程冲突检测"""
    print_separator()
    print("示例 2: 日程冲突检测")
    print_separator()
    
    db = DatabaseManager("example_schedule.db")
    manager = ScheduleManager(db)
    
    today = datetime.now().date()
    
    # 尝试创建一个与已有日程冲突的预约
    print("\n尝试创建冲突的日程（与英语课时间重叠）")
    start_time = datetime.combine(today, datetime.min.time()).replace(hour=10, minute=0)
    end_time = start_time + timedelta(hours=1)
    
    success, schedule, message = manager.create_schedule(
        title="咖啡约会",
        description="和朋友喝咖啡",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        priority=SchedulePriority.MEDIUM,
        check_conflict=True  # 启用冲突检查
    )
    
    print(f"   结果: {message}")
    print(f"   成功: {success}")
    
    # 演示高优先级可以覆盖低优先级
    print("\n尝试创建高优先级日程（可以覆盖临时日程）")
    start_time = datetime.combine(today, datetime.min.time()).replace(hour=15, minute=30)
    end_time = start_time + timedelta(hours=1)
    
    success, schedule, message = manager.create_schedule(
        title="重要电话会议",
        description="与客户的紧急会议",
        schedule_type=ScheduleType.APPOINTMENT,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        priority=SchedulePriority.HIGH,
        check_conflict=False  # 不检查冲突，允许覆盖
    )
    
    print(f"   结果: {message}")
    print(f"   成功: {success}")


def example_query_schedules():
    """示例：查询日程"""
    print_separator()
    print("示例 3: 查询日程")
    print_separator()
    
    db = DatabaseManager("example_schedule.db")
    manager = ScheduleManager(db)
    
    today = datetime.now().date()
    
    # 查询今天的所有日程
    print("\n今天的所有日程：")
    start_of_day = datetime.combine(today, datetime.min.time())
    end_of_day = datetime.combine(today, datetime.max.time())
    
    schedules = manager.get_schedules_by_time_range(
        start_of_day.isoformat(),
        end_of_day.isoformat()
    )
    
    if schedules:
        for i, schedule in enumerate(schedules, 1):
            start_dt = datetime.fromisoformat(schedule.start_time)
            end_dt = datetime.fromisoformat(schedule.end_time)
            print(f"   {i}. {schedule.title}")
            print(f"      时间: {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')}")
            print(f"      类型: {schedule.schedule_type.value}")
            print(f"      优先级: {schedule.priority.name}")
    else:
        print("   今天没有日程安排")
    
    # 查询空闲时间段
    print(f"\n今天的空闲时间段：")
    free_slots = manager.get_free_time_slots(today.isoformat(), slot_duration_minutes=60)
    
    if free_slots:
        for i, (start, end) in enumerate(free_slots, 1):
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration = (end_dt - start_dt).total_seconds() / 3600
            print(f"   {i}. {start_dt.strftime('%H:%M')} - {end_dt.strftime('%H:%M')} ({duration:.1f}小时)")
    else:
        print("   今天没有空闲时间段")


def example_collaboration_schedule():
    """示例：协作日程确认"""
    print_separator()
    print("示例 4: 协作日程确认")
    print_separator()
    
    db = DatabaseManager("example_schedule.db")
    manager = ScheduleManager(db)
    
    today = datetime.now().date()
    
    # 创建涉及用户的临时日程
    print("\n创建涉及用户的临时日程：一起看电影")
    start_time = datetime.combine(today, datetime.min.time()).replace(hour=19, minute=0)
    end_time = start_time + timedelta(hours=2)
    
    success, schedule, message = manager.create_schedule(
        title="一起看电影",
        description="和用户一起看电影",
        schedule_type=ScheduleType.TEMPORARY,
        start_time=start_time.isoformat(),
        end_time=end_time.isoformat(),
        involves_user=True  # 涉及用户参与
    )
    
    if success:
        print(f"   结果: {message}")
        print(f"   协作状态: {schedule.collaboration_status.value}")
        print(f"   可查询: {schedule.is_queryable}")
        
        # 查询待确认的协作日程
        print("\n待确认的协作日程：")
        pending = manager.get_pending_collaboration_schedules()
        for s in pending:
            print(f"   - {s.title}")
        
        # 模拟用户确认
        print("\n用户确认日程...")
        confirm_success = manager.confirm_collaboration(schedule.schedule_id, True)
        
        if confirm_success:
            # 重新获取日程查看状态
            updated_schedule = manager.get_schedule(schedule.schedule_id)
            print(f"   确认成功！")
            print(f"   新的协作状态: {updated_schedule.collaboration_status.value}")
            print(f"   现在可查询: {updated_schedule.is_queryable}")


def example_statistics():
    """示例：日程统计"""
    print_separator()
    print("示例 5: 日程统计")
    print_separator()
    
    db = DatabaseManager("example_schedule.db")
    manager = ScheduleManager(db)
    
    stats = manager.get_statistics()
    
    print("\n日程统计信息：")
    print(f"   总日程数: {stats['total_schedules']}")
    print(f"   周期日程: {stats['recurring']}")
    print(f"   预约日程: {stats['appointments']}")
    print(f"   临时日程: {stats['temporary']}")
    print(f"   激活的日程: {stats['active']}")
    print(f"   待确认的协作日程: {stats['pending_collaboration']}")


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" " * 15 + "日程管理功能示例")
    print("=" * 60)
    
    try:
        # 运行所有示例
        example_create_schedules()
        example_conflict_detection()
        example_query_schedules()
        example_collaboration_schedule()
        example_statistics()
        
        print("\n" + "=" * 60)
        print("示例运行完成！")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
