"""
Live2D助手功能测试脚本
测试番茄时钟、日程、笔记、计划管理等核心功能
"""

import time
from datetime import datetime, timedelta

from pomodoro_timer import PomodoroTimer, PomodoroState
from schedule_manager import ScheduleManager, Schedule, SchedulePriority, ScheduleStatus
from note_manager import NoteManager, Note
from plan_manager import PlanManager, Plan, Task, PlanStatus, TaskStatus


def test_pomodoro_timer():
    """测试番茄时钟"""
    print("=== 测试番茄时钟 ===")

    timer = PomodoroTimer(work_duration=1, short_break=1, long_break=1)  # 1分钟用于测试

    # 测试状态
    status = timer.get_status()
    print(f"初始状态: {status['state']}")
    print(f"完成番茄数: {status['current_pomodoro']}")

    # 测试格式化时间
    formatted_time = timer.format_time(125)
    print(f"格式化时间 (125秒): {formatted_time}")
    assert formatted_time == "02:05", "时间格式化错误"

    print("✓ 番茄时钟测试通过\n")


def test_schedule_manager():
    """测试日程管理"""
    print("=== 测试日程管理 ===")

    manager = ScheduleManager()

    # 创建测试日程
    schedule = Schedule(
        title="测试日程",
        description="这是一个测试日程",
        start_time=datetime.now() + timedelta(hours=1),
        end_time=datetime.now() + timedelta(hours=2),
        priority=SchedulePriority.HIGH
    )

    # 添加日程
    result = manager.add_schedule(schedule)
    print(f"添加日程: {'成功' if result else '失败'}")
    assert result, "添加日程失败"

    # 获取日程
    retrieved = manager.get_schedule(schedule.schedule_id)
    print(f"获取日程: {retrieved.title if retrieved else '失败'}")
    assert retrieved is not None, "获取日程失败"
    assert retrieved.title == "测试日程", "日程标题不匹配"

    # 获取统计
    stats = manager.get_statistics()
    print(f"日程统计: 总计 {stats['total']} 个，待办 {stats['pending']} 个")

    # 清理测试数据
    manager.delete_schedule(schedule.schedule_id)

    print("✓ 日程管理测试通过\n")


def test_note_manager():
    """测试笔记管理"""
    print("=== 测试笔记管理 ===")

    manager = NoteManager()

    # 创建测试笔记
    note = Note(
        title="测试笔记",
        content="这是一条测试笔记的内容",
        tags=["测试", "开发"],
        category="技术"
    )

    # 添加笔记
    result = manager.add_note(note)
    print(f"添加笔记: {'成功' if result else '失败'}")
    assert result, "添加笔记失败"

    # 获取笔记
    retrieved = manager.get_note(note.note_id)
    print(f"获取笔记: {retrieved.title if retrieved else '失败'}")
    assert retrieved is not None, "获取笔记失败"
    assert retrieved.title == "测试笔记", "笔记标题不匹配"

    # 搜索笔记
    search_results = manager.search_notes("测试")
    print(f"搜索结果: 找到 {len(search_results)} 条笔记")
    assert len(search_results) > 0, "搜索笔记失败"

    # 获取统计
    stats = manager.get_statistics()
    print(f"笔记统计: 总计 {stats['total']} 条")

    # 清理测试数据
    manager.delete_note(note.note_id)

    print("✓ 笔记管理测试通过\n")


def test_plan_manager():
    """测试计划管理"""
    print("=== 测试计划管理 ===")

    manager = PlanManager()

    # 创建测试计划
    plan = Plan(
        title="学习Python",
        description="系统学习Python编程",
        goal="掌握Python基础和进阶知识",
        status=PlanStatus.IN_PROGRESS
    )

    # 添加任务
    task1 = Task(title="学习基础语法", description="变量、函数、类等")
    task2 = Task(title="学习高级特性", description="装饰器、生成器等")
    plan.add_task(task1)
    plan.add_task(task2)

    # 添加计划
    result = manager.add_plan(plan)
    print(f"添加计划: {'成功' if result else '失败'}")
    assert result, "添加计划失败"

    # 获取计划
    retrieved = manager.get_plan(plan.plan_id)
    print(f"获取计划: {retrieved.title if retrieved else '失败'}")
    assert retrieved is not None, "获取计划失败"
    assert retrieved.title == "学习Python", "计划标题不匹配"
    print(f"任务数量: {len(retrieved.tasks)}")
    assert len(retrieved.tasks) == 2, "任务数量不匹配"

    # 更新任务状态
    task1.mark_completed()
    plan.update_progress()
    print(f"完成第一个任务，进度: {int(plan.progress * 100)}%")
    assert plan.progress == 0.5, "进度计算错误"

    # 更新计划
    manager.update_plan(plan)

    # 获取统计
    stats = manager.get_statistics()
    print(f"计划统计: 总计 {stats['total']} 个，进行中 {stats['in_progress']} 个")
    print(f"总任务: {stats['total_tasks']}, 已完成: {stats['completed_tasks']}")

    # 清理测试数据
    manager.delete_plan(plan.plan_id)

    print("✓ 计划管理测试通过\n")


def main():
    """运行所有测试"""
    print("=" * 50)
    print("Live2D助手功能测试")
    print("=" * 50)
    print()

    try:
        test_pomodoro_timer()
        test_schedule_manager()
        test_note_manager()
        test_plan_manager()

        print("=" * 50)
        print("✓ 所有测试通过！")
        print("=" * 50)

    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        return 1

    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
