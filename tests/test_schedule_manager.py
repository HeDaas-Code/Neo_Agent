"""
日程管理器测试
"""

import unittest
import os
from datetime import datetime, timedelta
from schedule_manager import (
    ScheduleManager, Schedule, RecurringSchedule, AppointmentSchedule, TemporarySchedule,
    ScheduleType, SchedulePriority, CollaborationStatus
)
from database_manager import DatabaseManager


class TestScheduleManager(unittest.TestCase):
    """日程管理器测试类"""

    def setUp(self):
        """测试前的设置"""
        # 使用测试数据库
        self.test_db_path = "test_schedule.db"
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
        
        self.db_manager = DatabaseManager(self.test_db_path)
        self.schedule_manager = ScheduleManager(self.db_manager)

    def tearDown(self):
        """测试后的清理"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)

    def test_create_appointment_schedule(self):
        """测试创建预约日程"""
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        success, schedule, message = self.schedule_manager.create_schedule(
            title="开会",
            description="与团队讨论项目进展",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            priority=SchedulePriority.HIGH
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.title, "开会")
        self.assertEqual(schedule.priority, SchedulePriority.HIGH)

    def test_create_recurring_schedule(self):
        """测试创建周期日程"""
        now = datetime.now()
        start_time = now.replace(hour=9, minute=0, second=0, microsecond=0)
        end_time = start_time.replace(hour=11)
        
        success, schedule, message = self.schedule_manager.create_schedule(
            title="英语课",
            description="每周一的英语课",
            schedule_type=ScheduleType.RECURRING,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            weekday=0,  # 周一
            recurrence_pattern="每周一"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.schedule_type, ScheduleType.RECURRING)
        self.assertEqual(schedule.priority, SchedulePriority.CRITICAL)

    def test_create_temporary_schedule(self):
        """测试创建临时日程"""
        now = datetime.now()
        start_time = now + timedelta(hours=2)
        end_time = start_time + timedelta(hours=1)
        
        success, schedule, message = self.schedule_manager.create_schedule(
            title="阅读时光",
            description="读一本喜欢的书",
            schedule_type=ScheduleType.TEMPORARY,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            generated_reason="空闲时间自动生成"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(schedule)
        self.assertEqual(schedule.schedule_type, ScheduleType.TEMPORARY)
        self.assertEqual(schedule.priority, SchedulePriority.LOW)

    def test_conflict_detection_same_priority(self):
        """测试相同优先级的冲突检测"""
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        # 创建第一个日程
        success1, schedule1, message1 = self.schedule_manager.create_schedule(
            title="会议A",
            description="第一个会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            priority=SchedulePriority.MEDIUM
        )
        
        self.assertTrue(success1)
        
        # 尝试创建冲突的日程（相同优先级）
        conflict_start = start_time + timedelta(minutes=30)
        conflict_end = end_time + timedelta(minutes=30)
        
        success2, schedule2, message2 = self.schedule_manager.create_schedule(
            title="会议B",
            description="第二个会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=conflict_start.isoformat(),
            end_time=conflict_end.isoformat(),
            priority=SchedulePriority.MEDIUM,
            check_conflict=True
        )
        
        self.assertFalse(success2)
        self.assertIsNone(schedule2)
        self.assertIn("冲突", message2)

    def test_priority_override(self):
        """测试高优先级覆盖低优先级"""
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        # 创建低优先级临时日程
        success1, schedule1, message1 = self.schedule_manager.create_schedule(
            title="临时活动",
            description="临时安排的活动",
            schedule_type=ScheduleType.TEMPORARY,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            priority=SchedulePriority.LOW
        )
        
        self.assertTrue(success1)
        
        # 尝试创建高优先级预约，应该成功（不检查冲突）
        success2, schedule2, message2 = self.schedule_manager.create_schedule(
            title="重要会议",
            description="高优先级会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            priority=SchedulePriority.HIGH,
            check_conflict=False  # 禁用自动冲突检查
        )
        
        self.assertTrue(success2)
        
        # 验证冲突检测逻辑：低优先级尝试创建应该被高优先级阻止
        has_conflict_low, conflict_schedule_low = self.schedule_manager.check_conflict(
            start_time.isoformat(),
            end_time.isoformat(),
            SchedulePriority.LOW
        )
        
        # 低优先级日程应该检测到与高优先级日程的冲突
        self.assertTrue(has_conflict_low)
        # 冲突可能返回任一日程，只要优先级 >= 新日程的优先级
        self.assertIn(conflict_schedule_low.title, ["临时活动", "重要会议"])
        
        # 验证：高优先级尝试创建不应该被低优先级阻止
        has_conflict_high, conflict_schedule_high = self.schedule_manager.check_conflict(
            start_time.isoformat(),
            end_time.isoformat(),
            SchedulePriority.HIGH
        )
        
        # 高优先级日程只会与同等或更高优先级的日程冲突
        if has_conflict_high:
            self.assertGreaterEqual(conflict_schedule_high.priority.value, SchedulePriority.HIGH.value)

    def test_collaboration_status(self):
        """测试协作确认状态"""
        now = datetime.now()
        start_time = now + timedelta(hours=1)
        end_time = start_time + timedelta(hours=2)
        
        # 创建涉及用户的临时日程
        success, schedule, message = self.schedule_manager.create_schedule(
            title="一起看电影",
            description="和用户一起看电影",
            schedule_type=ScheduleType.TEMPORARY,
            start_time=start_time.isoformat(),
            end_time=end_time.isoformat(),
            involves_user=True
        )
        
        self.assertTrue(success)
        self.assertEqual(schedule.collaboration_status, CollaborationStatus.PENDING)
        self.assertFalse(schedule.is_queryable)
        
        # 确认协作
        confirm_success = self.schedule_manager.confirm_collaboration(schedule.schedule_id, True)
        self.assertTrue(confirm_success)
        
        # 重新获取日程验证状态
        updated_schedule = self.schedule_manager.get_schedule(schedule.schedule_id)
        self.assertEqual(updated_schedule.collaboration_status, CollaborationStatus.CONFIRMED)
        self.assertTrue(updated_schedule.is_queryable)

    def test_get_free_time_slots(self):
        """测试获取空闲时间段"""
        # 创建一些日程
        today = datetime.now().date()
        
        # 早上9-11点有课
        morning_start = datetime.combine(today, datetime.min.time()).replace(hour=9)
        morning_end = morning_start.replace(hour=11)
        
        self.schedule_manager.create_schedule(
            title="上课",
            description="早上的课程",
            schedule_type=ScheduleType.RECURRING,
            start_time=morning_start.isoformat(),
            end_time=morning_end.isoformat()
        )
        
        # 下午2-4点开会
        afternoon_start = datetime.combine(today, datetime.min.time()).replace(hour=14)
        afternoon_end = afternoon_start.replace(hour=16)
        
        self.schedule_manager.create_schedule(
            title="会议",
            description="下午的会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=afternoon_start.isoformat(),
            end_time=afternoon_end.isoformat()
        )
        
        # 获取空闲时间段
        free_slots = self.schedule_manager.get_free_time_slots(today.isoformat())
        
        # 应该有多个空闲时间段
        self.assertGreater(len(free_slots), 0)
        
        # 验证11点到14点之间应该是空闲的
        found_free_slot = False
        for start, end in free_slots:
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            if start_dt.hour == 11 and end_dt.hour >= 14:
                found_free_slot = True
                break
        
        self.assertTrue(found_free_slot)

    def test_get_schedules_by_time_range(self):
        """测试按时间范围查询日程"""
        today = datetime.now().date()
        
        # 创建多个日程
        for i in range(3):
            start_time = datetime.combine(today, datetime.min.time()).replace(hour=9+i*2)
            end_time = start_time + timedelta(hours=1)
            
            self.schedule_manager.create_schedule(
                title=f"活动{i+1}",
                description=f"第{i+1}个活动",
                schedule_type=ScheduleType.APPOINTMENT,
                start_time=start_time.isoformat(),
                end_time=end_time.isoformat()
            )
        
        # 查询今天的所有日程
        start_of_day = datetime.combine(today, datetime.min.time())
        end_of_day = datetime.combine(today, datetime.max.time())
        
        schedules = self.schedule_manager.get_schedules_by_time_range(
            start_of_day.isoformat(),
            end_of_day.isoformat()
        )
        
        self.assertEqual(len(schedules), 3)

    def test_statistics(self):
        """测试统计信息"""
        now = datetime.now()
        
        # 创建不同类型的日程
        self.schedule_manager.create_schedule(
            title="课程",
            description="周期课程",
            schedule_type=ScheduleType.RECURRING,
            start_time=now.isoformat(),
            end_time=(now + timedelta(hours=1)).isoformat()
        )
        
        self.schedule_manager.create_schedule(
            title="会议",
            description="预约会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time=(now + timedelta(hours=2)).isoformat(),
            end_time=(now + timedelta(hours=3)).isoformat()
        )
        
        self.schedule_manager.create_schedule(
            title="休闲",
            description="临时休闲",
            schedule_type=ScheduleType.TEMPORARY,
            start_time=(now + timedelta(hours=4)).isoformat(),
            end_time=(now + timedelta(hours=5)).isoformat()
        )
        
        # 获取统计信息
        stats = self.schedule_manager.get_statistics()
        
        self.assertEqual(stats['total_schedules'], 3)
        self.assertEqual(stats['recurring'], 1)
        self.assertEqual(stats['appointments'], 1)
        self.assertEqual(stats['temporary'], 1)
        self.assertEqual(stats['active'], 3)


if __name__ == '__main__':
    unittest.main()
