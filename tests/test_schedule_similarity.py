"""
测试日程相似度检查功能
"""

import sys
import os
import unittest
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.schedule_manager import ScheduleManager, ScheduleType, SchedulePriority
from src.core.schedule_similarity_checker import ScheduleSimilarityChecker, get_schedules_on_same_day
from src.core.database_manager import DatabaseManager


class TestScheduleSimilarity(unittest.TestCase):
    """测试日程相似度检查功能"""

    def setUp(self):
        """设置测试环境"""
        # 使用内存数据库进行测试
        self.db = DatabaseManager(':memory:')
        self.manager = ScheduleManager(self.db)
        self.checker = ScheduleSimilarityChecker()

    def test_create_schedule_with_similarity_check(self):
        """测试创建日程时的相似度检查"""
        # 创建第一个日程
        success1, schedule1, msg1 = self.manager.create_schedule(
            title="团队会议",
            description="讨论项目进度",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time="2024-01-15T10:00:00",
            end_time="2024-01-15T11:00:00",
            check_similarity=False  # 第一个不检查相似度
        )
        
        self.assertTrue(success1, "第一个日程应该创建成功")
        
        # 尝试创建一个相似但时间稍有不同的日程
        # 注意：这个测试依赖于LLM的判断，实际运行时可能会因API不可用而跳过
        success2, schedule2, msg2 = self.manager.create_schedule(
            title="项目讨论会",
            description="关于项目进度的会议",
            schedule_type=ScheduleType.APPOINTMENT,
            start_time="2024-01-15T14:00:00",
            end_time="2024-01-15T15:00:00",
            check_similarity=True
        )
        
        # 因为LLM可能不可用，我们只测试函数能正常执行，不强制要求特定结果
        print(f"第二个日程创建结果: {success2}, 消息: {msg2}")

    def test_get_schedules_on_same_day(self):
        """测试获取同一天的日程"""
        # 创建多个日程，有些在同一天，有些不在
        schedules_data = [
            ("日程1", "2024-01-15T09:00:00", "2024-01-15T10:00:00"),
            ("日程2", "2024-01-15T14:00:00", "2024-01-15T15:00:00"),
            ("日程3", "2024-01-16T09:00:00", "2024-01-16T10:00:00"),
        ]
        
        for title, start, end in schedules_data:
            self.manager.create_schedule(
                title=title,
                description="测试日程",
                schedule_type=ScheduleType.APPOINTMENT,
                start_time=start,
                end_time=end,
                check_similarity=False
            )
        
        # 获取1月15日的日程
        same_day = get_schedules_on_same_day(self.manager, "2024-01-15T12:00:00")
        
        self.assertEqual(len(same_day), 2, "应该找到2个同一天的日程")
        
        # 验证返回的是字典列表
        self.assertTrue(all(isinstance(s, dict) for s in same_day))
        
        # 验证标题
        titles = [s['title'] for s in same_day]
        self.assertIn("日程1", titles)
        self.assertIn("日程2", titles)
        self.assertNotIn("日程3", titles)

    def test_no_similarity_check_when_disabled(self):
        """测试禁用相似度检查时的行为"""
        # 创建两个明显相似的日程，但禁用相似度检查
        success1, schedule1, msg1 = self.manager.create_schedule(
            title="晨跑",
            description="早上跑步锻炼",
            schedule_type=ScheduleType.TEMPORARY,
            start_time="2024-01-15T06:00:00",
            end_time="2024-01-15T07:00:00",
            check_similarity=False
        )
        
        success2, schedule2, msg2 = self.manager.create_schedule(
            title="晨跑",
            description="早上跑步锻炼，保持健康",
            schedule_type=ScheduleType.TEMPORARY,
            start_time="2024-01-15T08:00:00",
            end_time="2024-01-15T09:00:00",
            check_similarity=False
        )
        
        self.assertTrue(success1, "第一个日程应该创建成功")
        self.assertTrue(success2, "禁用相似度检查时，第二个日程也应该创建成功")

    def test_schedule_similarity_checker_format(self):
        """测试日程相似度检查器的格式化方法"""
        schedule_dict = {
            'title': '测试日程',
            'description': '这是一个测试',
            'start_time': '2024-01-15T10:00:00',
            'end_time': '2024-01-15T11:00:00',
            'schedule_type': 'appointment',
            'metadata': {'location': '会议室A'}
        }
        
        formatted = self.checker._format_schedule_for_llm(schedule_dict, "测试标签")
        
        # 验证格式化结果包含关键信息
        self.assertIn("测试标签", formatted)
        self.assertIn("测试日程", formatted)
        self.assertIn("这是一个测试", formatted)
        self.assertIn("2024-01-15T10:00:00", formatted)


if __name__ == '__main__':
    print("=" * 60)
    print("测试日程相似度检查功能")
    print("=" * 60)
    print("\n注意：部分测试依赖LLM API，如果API不可用，某些测试可能会跳过或失败。\n")
    
    unittest.main(verbosity=2)
