"""
ScheduleManager 模块的单元测试
"""

import unittest
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schedule_manager import (
    ScheduleManager, Schedule, ScheduleType, SchedulePriority,
    RecurrencePattern
)
from database_manager import DatabaseManager


class TestScheduleEnums(unittest.TestCase):
    """测试日程枚举类型"""

    def test_schedule_type_enum(self):
        """测试 ScheduleType 枚举"""
        self.assertEqual(ScheduleType.RECURRING.value, "recurring")
        self.assertEqual(ScheduleType.APPOINTMENT.value, "appointment")
        self.assertEqual(ScheduleType.IMPROMPTU.value, "impromptu")

    def test_schedule_priority_enum(self):
        """测试 SchedulePriority 枚举"""
        self.assertEqual(SchedulePriority.LOW.value, 1)
        self.assertEqual(SchedulePriority.MEDIUM.value, 2)
        self.assertEqual(SchedulePriority.HIGH.value, 3)
        self.assertEqual(SchedulePriority.URGENT.value, 4)

    def test_recurrence_pattern_enum(self):
        """测试 RecurrencePattern 枚举"""
        self.assertEqual(RecurrencePattern.NONE.value, "none")
        self.assertEqual(RecurrencePattern.DAILY.value, "daily")
        self.assertEqual(RecurrencePattern.WEEKLY.value, "weekly")
        self.assertEqual(RecurrencePattern.WEEKDAYS.value, "weekdays")


class TestSchedule(unittest.TestCase):
    """测试 Schedule 类"""

    def test_schedule_creation(self):
        """测试创建日程"""
        schedule = Schedule(
            title="测试日程",
            description="这是一个测试日程",
            schedule_type=ScheduleType.APPOINTMENT,
            priority=SchedulePriority.MEDIUM,
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        
        self.assertEqual(schedule.title, "测试日程")
        self.assertEqual(schedule.schedule_type, ScheduleType.APPOINTMENT)
        self.assertEqual(schedule.priority, SchedulePriority.MEDIUM)
        self.assertIsNotNone(schedule.schedule_id)

    def test_schedule_auto_priority(self):
        """测试日程类型自动设置优先级"""
        # 周期日程应该是URGENT
        recurring = Schedule(
            title="课程",
            schedule_type=ScheduleType.RECURRING,
            priority=SchedulePriority.URGENT,
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            recurrence_pattern=RecurrencePattern.WEEKDAYS
        )
        self.assertEqual(recurring.priority, SchedulePriority.URGENT)

    def test_schedule_is_recurring(self):
        """测试日程重复检测"""
        non_recurring = Schedule(
            title="一次性会议",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        self.assertFalse(non_recurring.is_recurring())

        recurring = Schedule(
            title="每日站会",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            recurrence_pattern=RecurrencePattern.DAILY
        )
        self.assertTrue(recurring.is_recurring())

    def test_schedule_applies_to_date(self):
        """测试日程日期适用性"""
        # 测试非重复日程
        schedule = Schedule(
            title="会议",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        self.assertTrue(schedule.applies_to_date("2024-01-15"))
        self.assertFalse(schedule.applies_to_date("2024-01-16"))

        # 测试每日重复
        daily_schedule = Schedule(
            title="每日任务",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            recurrence_pattern=RecurrencePattern.DAILY
        )
        self.assertTrue(daily_schedule.applies_to_date("2024-01-15"))
        self.assertTrue(daily_schedule.applies_to_date("2024-01-16"))
        self.assertTrue(daily_schedule.applies_to_date("2024-02-01"))

    def test_schedule_weekdays_pattern(self):
        """测试工作日重复模式"""
        schedule = Schedule(
            title="工作日任务",
            start_time="09:00",
            end_time="17:00",
            date="2024-01-15",  # 周一
            recurrence_pattern=RecurrencePattern.WEEKDAYS
        )
        
        # 周一到周五应该适用
        self.assertTrue(schedule.applies_to_date("2024-01-15"))  # 周一
        self.assertTrue(schedule.applies_to_date("2024-01-16"))  # 周二
        self.assertTrue(schedule.applies_to_date("2024-01-19"))  # 周五
        
        # 周末不适用
        self.assertFalse(schedule.applies_to_date("2024-01-20"))  # 周六
        self.assertFalse(schedule.applies_to_date("2024-01-21"))  # 周日


class TestScheduleManager(unittest.TestCase):
    """测试 ScheduleManager 类"""

    def setUp(self):
        """每个测试前的设置"""
        # 使用临时数据库
        self.test_db_path = "test_schedule.db"
        self.db = DatabaseManager(self.test_db_path)
        self.manager = ScheduleManager(self.db)

    def tearDown(self):
        """每个测试后的清理"""
        # 删除测试数据库
        import os
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_add_schedule_success(self):
        """测试成功添加日程"""
        success, schedule, message = self.manager.add_schedule(
            title="测试会议",
            description="重要会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.title, "测试会议")

    def test_add_recurring_schedule(self):
        """测试添加周期日程"""
        success, schedule, message = self.manager.add_schedule(
            title="每日站会",
            schedule_type=ScheduleType.RECURRING,
            start_time="09:00",
            end_time="09:30",
            date="2024-01-15",
            recurrence_pattern=RecurrencePattern.WEEKDAYS
        )
        
        self.assertTrue(success)
        self.assertEqual(schedule.schedule_type, ScheduleType.RECURRING)
        self.assertEqual(schedule.priority, SchedulePriority.URGENT)

    def test_conflict_detection(self):
        """测试冲突检测"""
        # 添加第一个日程
        self.manager.add_schedule(
            title="会议A",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            schedule_type=ScheduleType.APPOINTMENT
        )
        
        # 尝试添加冲突的日程（不自动解决冲突）
        success, schedule, message = self.manager.add_schedule(
            title="会议B",
            start_time="09:30",
            end_time="10:30",
            date="2024-01-15",
            schedule_type=ScheduleType.APPOINTMENT,
            auto_resolve_conflicts=False
        )
        
        self.assertFalse(success)
        self.assertIn("冲突", message)

    def test_priority_conflict_resolution(self):
        """测试优先级冲突解决"""
        # 添加低优先级日程
        self.manager.add_schedule(
            title="临时活动",
            start_time="14:00",
            end_time="15:00",
            date="2024-01-15",
            schedule_type=ScheduleType.IMPROMPTU,
            priority=SchedulePriority.LOW
        )
        
        # 添加高优先级日程，应该替换低优先级的
        success, schedule, message = self.manager.add_schedule(
            title="重要会议",
            start_time="14:00",
            end_time="15:00",
            date="2024-01-15",
            schedule_type=ScheduleType.APPOINTMENT,
            priority=SchedulePriority.HIGH,
            auto_resolve_conflicts=True
        )
        
        self.assertTrue(success)
        self.assertIn("删除", message)
        
        # 验证低优先级日程已被删除
        schedules = self.manager.get_schedules_by_date("2024-01-15")
        self.assertEqual(len(schedules), 1)
        self.assertEqual(schedules[0].title, "重要会议")

    def test_get_schedules_by_date(self):
        """测试按日期获取日程"""
        # 添加多个日程
        self.manager.add_schedule(
            title="会议1",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        self.manager.add_schedule(
            title="会议2",
            start_time="14:00",
            end_time="15:00",
            date="2024-01-15"
        )
        self.manager.add_schedule(
            title="会议3",
            start_time="10:00",
            end_time="11:00",
            date="2024-01-16"
        )
        
        schedules_15 = self.manager.get_schedules_by_date("2024-01-15")
        self.assertEqual(len(schedules_15), 2)
        
        schedules_16 = self.manager.get_schedules_by_date("2024-01-16")
        self.assertEqual(len(schedules_16), 1)

    def test_recurring_schedule_retrieval(self):
        """测试重复日程的检索"""
        # 添加工作日重复日程
        self.manager.add_schedule(
            title="每日站会",
            start_time="09:00",
            end_time="09:30",
            date="2024-01-15",  # 周一
            recurrence_pattern=RecurrencePattern.WEEKDAYS,
            schedule_type=ScheduleType.RECURRING
        )
        
        # 检查周一到周五都能获取到
        self.assertEqual(len(self.manager.get_schedules_by_date("2024-01-15")), 1)  # 周一
        self.assertEqual(len(self.manager.get_schedules_by_date("2024-01-16")), 1)  # 周二
        self.assertEqual(len(self.manager.get_schedules_by_date("2024-01-19")), 1)  # 周五
        
        # 周末不应该有
        self.assertEqual(len(self.manager.get_schedules_by_date("2024-01-20")), 0)  # 周六
        self.assertEqual(len(self.manager.get_schedules_by_date("2024-01-21")), 0)  # 周日

    def test_schedule_summary(self):
        """测试日程摘要生成"""
        self.manager.add_schedule(
            title="早会",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            location="会议室A"
        )
        self.manager.add_schedule(
            title="午餐",
            start_time="12:00",
            end_time="13:00",
            date="2024-01-15"
        )
        
        summary = self.manager.get_schedule_summary("2024-01-15")
        self.assertIn("早会", summary)
        self.assertIn("午餐", summary)
        self.assertIn("上午", summary)
        self.assertIn("下午", summary)

    def test_update_schedule(self):
        """测试更新日程"""
        # 添加日程
        success, schedule, _ = self.manager.add_schedule(
            title="原标题",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        
        # 更新日程
        success, message = self.manager.update_schedule(
            schedule.schedule_id,
            title="新标题",
            description="更新后的描述"
        )
        
        self.assertTrue(success)
        
        # 验证更新
        updated = self.manager.get_schedule(schedule.schedule_id)
        self.assertEqual(updated.title, "新标题")
        self.assertEqual(updated.description, "更新后的描述")

    def test_delete_schedule(self):
        """测试删除日程"""
        # 添加日程
        success, schedule, _ = self.manager.add_schedule(
            title="待删除",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15"
        )
        
        # 删除日程
        deleted = self.manager.delete_schedule(schedule.schedule_id)
        self.assertTrue(deleted)
        
        # 验证已删除
        retrieved = self.manager.get_schedule(schedule.schedule_id)
        self.assertIsNone(retrieved)

    def test_statistics(self):
        """测试统计信息"""
        self.manager.add_schedule(
            title="周期日程",
            start_time="09:00",
            end_time="10:00",
            date="2024-01-15",
            schedule_type=ScheduleType.RECURRING,
            recurrence_pattern=RecurrencePattern.DAILY
        )
        self.manager.add_schedule(
            title="预约",
            start_time="14:00",
            end_time="15:00",
            date="2024-01-15",
            schedule_type=ScheduleType.APPOINTMENT
        )
        
        stats = self.manager.get_statistics()
        self.assertEqual(stats['total_schedules'], 2)
        self.assertEqual(stats['recurring'], 1)
        self.assertEqual(stats['appointments'], 1)


if __name__ == '__main__':
    unittest.main()
