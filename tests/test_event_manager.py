"""
EventManager 模块的单元测试
"""

import unittest
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.event_manager import EventType, EventPriority, EventStatus, Event


class TestEventEnums(unittest.TestCase):
    """测试事件枚举类型"""

    def test_event_type_enum(self):
        """测试 EventType 枚举"""
        self.assertEqual(EventType.NOTIFICATION.value, "notification")
        self.assertEqual(EventType.TASK.value, "task")

    def test_event_priority_enum(self):
        """测试 EventPriority 枚举"""
        self.assertEqual(EventPriority.LOW.value, 1)
        self.assertEqual(EventPriority.MEDIUM.value, 2)
        self.assertEqual(EventPriority.HIGH.value, 3)
        self.assertEqual(EventPriority.URGENT.value, 4)

    def test_event_status_enum(self):
        """测试 EventStatus 枚举"""
        self.assertEqual(EventStatus.PENDING.value, "pending")
        self.assertEqual(EventStatus.PROCESSING.value, "processing")
        self.assertEqual(EventStatus.COMPLETED.value, "completed")
        self.assertEqual(EventStatus.FAILED.value, "failed")


class TestEvent(unittest.TestCase):
    """测试 Event 类"""

    def test_event_creation_with_required_fields(self):
        """测试使用必需字段创建事件"""
        event = Event(
            title="测试事件",
            description="这是一个测试事件",
            event_type=EventType.NOTIFICATION,
            priority=EventPriority.MEDIUM
        )
        
        self.assertEqual(event.title, "测试事件")
        self.assertEqual(event.description, "这是一个测试事件")
        self.assertEqual(event.event_type, EventType.NOTIFICATION)
        self.assertEqual(event.priority, EventPriority.MEDIUM)
        self.assertEqual(event.status, EventStatus.PENDING)
        self.assertIsNotNone(event.event_id)
        self.assertIsNotNone(event.created_at)

    def test_event_id_is_unique(self):
        """测试事件ID的唯一性"""
        event1 = Event(
            title="事件1",
            description="描述1",
            event_type=EventType.NOTIFICATION,
            priority=EventPriority.LOW
        )
        event2 = Event(
            title="事件2",
            description="描述2",
            event_type=EventType.NOTIFICATION,
            priority=EventPriority.LOW
        )
        
        self.assertNotEqual(event1.event_id, event2.event_id)

    def test_event_default_status(self):
        """测试事件的默认状态"""
        event = Event(
            title="测试",
            description="测试",
            event_type=EventType.TASK,
            priority=EventPriority.HIGH
        )
        
        self.assertEqual(event.status, EventStatus.PENDING)

    def test_notification_event(self):
        """测试通知型事件"""
        event = Event(
            title="系统通知",
            description="系统更新通知",
            event_type=EventType.NOTIFICATION,
            priority=EventPriority.HIGH
        )
        
        self.assertEqual(event.event_type, EventType.NOTIFICATION)
        self.assertEqual(event.priority, EventPriority.HIGH)

    def test_task_event(self):
        """测试任务型事件"""
        event = Event(
            title="执行任务",
            description="需要完成的任务",
            event_type=EventType.TASK,
            priority=EventPriority.URGENT
        )
        
        self.assertEqual(event.event_type, EventType.TASK)
        self.assertEqual(event.priority, EventPriority.URGENT)


if __name__ == '__main__':
    unittest.main()
