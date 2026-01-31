"""
临时日程生成工具
用于在空闲时间段自动生成临时日程
"""

import os
import re
import json
import time
from typing import List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from src.core.schedule_manager import ScheduleManager, ScheduleType, SchedulePriority
from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class TemporaryScheduleGenerator:
    """
    临时日程生成器
    在用户询问日程时，如果没有临时日程，则生成1-3个合理的临时日程
    """

    def __init__(self, schedule_manager: ScheduleManager = None):
        """
        初始化临时日程生成器

        Args:
            schedule_manager: 日程管理器实例
        """
        self.schedule_manager = schedule_manager or ScheduleManager()
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        self.temperature = 0.8
        self.max_tokens = 1000

        debug_logger.log_module('TemporaryScheduleGenerator', '临时日程生成器初始化完成')

    def generate_temporary_schedules(
        self,
        date: str,
        character_name: str = "智能体",
        character_info: Dict[str, str] = None,
        context: str = ""
    ) -> List[Dict[str, Any]]:
        """
        为指定日期生成临时日程

        Args:
            date: 日期（ISO格式，如 "2024-01-15"）
            character_name: 智能体名称
            character_info: 智能体信息
            context: 对话上下文

        Returns:
            生成的日程列表
        """
        debug_logger.log_module('TemporaryScheduleGenerator', '开始生成临时日程', {
            'date': date
        })

        # 获取空闲时间段
        free_slots = self.schedule_manager.get_free_time_slots(date, slot_duration_minutes=60)
        
        if not free_slots:
            debug_logger.log_info('TemporaryScheduleGenerator', '没有可用的空闲时间段')
            return []

        # 使用LLM生成临时日程建议
        character_info = character_info or {}
        hobby = character_info.get('hobby', '阅读、学习')
        personality = character_info.get('personality', '活泼开朗')
        
        system_prompt = f"""你是一个日程规划助手，帮助智能体{character_name}规划临时日程。

{character_name}的信息：
- 性格：{personality}
- 爱好：{hobby}

任务：根据提供的空闲时间段，生成1-3个合理的临时日程建议。

要求：
1. 日程内容应该符合{character_name}的性格和爱好
2. 日程应该多样化，包括学习、娱乐、休息等
3. 考虑时间段的特点（如早上适合学习，晚上适合放松）
4. 部分日程可以涉及用户参与（如"一起看电影"），这类日程需要标注involves_user=true

请以JSON格式输出日程建议列表：
[
    {{
        "title": "日程标题",
        "description": "详细描述",
        "time_slot_index": 0,
        "duration_hours": 1.5,
        "involves_user": false,
        "reason": "选择这个活动的原因"
    }},
    ...
]

注意：time_slot_index是指使用第几个空闲时间段（从0开始）"""

        # 格式化空闲时间段信息
        slots_info = []
        for i, (start, end) in enumerate(free_slots):
            start_dt = datetime.fromisoformat(start)
            end_dt = datetime.fromisoformat(end)
            duration = (end_dt - start_dt).total_seconds() / 3600
            time_period = self._get_time_period(start_dt.hour)
            slots_info.append(f"时间段{i}: {start_dt.strftime('%H:%M')}-{end_dt.strftime('%H:%M')} ({time_period}, {duration:.1f}小时)")
        
        user_prompt = f"""可用的空闲时间段：
{chr(10).join(slots_info)}

{f"对话上下文：{context}" if context else ""}

请为{character_name}生成1-3个临时日程建议。"""

        try:
            # 调用LLM生成日程
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': messages,
                'temperature': self.temperature,
                'max_tokens': self.max_tokens,
                'stream': False
            }

            debug_logger.log_request('TemporaryScheduleGenerator', self.api_url, payload, headers)

            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            elapsed_time = time.time() - start_time

            debug_logger.log_response('TemporaryScheduleGenerator', response.status_code, response.text, elapsed_time)

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # 尝试解析JSON结果
                try:
                    # 提取JSON部分
                    json_match = re.search(r'```(?:json)?\s*(\[.*?\])\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                    
                    suggestions = json.loads(content)
                    
                    # 创建临时日程
                    created_schedules = []
                    for suggestion in suggestions[:3]:  # 最多3个
                        slot_index = suggestion.get('time_slot_index', 0)
                        if slot_index >= len(free_slots):
                            continue
                        
                        start, end = free_slots[slot_index]
                        duration_hours = suggestion.get('duration_hours', 1.0)
                        
                        # 计算实际的结束时间
                        start_dt = datetime.fromisoformat(start)
                        actual_end = start_dt + timedelta(hours=duration_hours)
                        slot_end_dt = datetime.fromisoformat(end)
                        
                        # 确保不超过时间段
                        if actual_end > slot_end_dt:
                            actual_end = slot_end_dt
                        
                        involves_user = suggestion.get('involves_user', False)
                        
                        # 创建临时日程
                        success, schedule, message = self.schedule_manager.create_schedule(
                            title=suggestion.get('title', '临时活动'),
                            description=suggestion.get('description', ''),
                            schedule_type=ScheduleType.TEMPORARY,
                            start_time=start_dt.isoformat(),
                            end_time=actual_end.isoformat(),
                            priority=SchedulePriority.LOW,
                            generated_reason=suggestion.get('reason', ''),
                            involves_user=involves_user
                        )
                        
                        if success:
                            created_schedules.append(schedule.to_dict())
                            debug_logger.log_info('TemporaryScheduleGenerator', f'临时日程创建成功: {schedule.title}')
                    
                    return created_schedules
                    
                except json.JSONDecodeError as e:
                    debug_logger.log_error('TemporaryScheduleGenerator', f'解析JSON失败: {content}', e)
                    return self._create_fallback_schedules(free_slots[:1], character_name)
            else:
                debug_logger.log_error('TemporaryScheduleGenerator', f'API调用失败: {response.status_code}')
                return self._create_fallback_schedules(free_slots[:1], character_name)

        except Exception as e:
            debug_logger.log_error('TemporaryScheduleGenerator', f'生成临时日程异常: {str(e)}', e)
            return self._create_fallback_schedules(free_slots[:1], character_name)

    def _get_time_period(self, hour: int) -> str:
        """
        根据小时数获取时间段描述

        Args:
            hour: 小时数（0-23）

        Returns:
            时间段描述
        """
        if 5 <= hour < 9:
            return "早晨"
        elif 9 <= hour < 12:
            return "上午"
        elif 12 <= hour < 14:
            return "中午"
        elif 14 <= hour < 18:
            return "下午"
        elif 18 <= hour < 22:
            return "晚上"
        else:
            return "深夜"

    def _create_fallback_schedules(
        self,
        free_slots: List[Tuple[str, str]],
        character_name: str
    ) -> List[Dict[str, Any]]:
        """
        创建降级的临时日程（当LLM不可用时）

        Args:
            free_slots: 空闲时间段列表
            character_name: 智能体名称

        Returns:
            创建的日程列表
        """
        if not free_slots:
            return []
        
        created_schedules = []
        
        # 使用第一个空闲时间段
        start, end = free_slots[0]
        start_dt = datetime.fromisoformat(start)
        end_dt = start_dt + timedelta(hours=1.5)
        
        # 根据时间段选择活动
        hour = start_dt.hour
        if 9 <= hour < 12:
            title = "阅读时光"
            description = "安静地阅读一本喜欢的书"
        elif 14 <= hour < 18:
            title = "学习充电"
            description = "学习新知识，充实自己"
        else:
            title = "休闲放松"
            description = "放松心情，做些喜欢的事"
        
        success, schedule, _ = self.schedule_manager.create_schedule(
            title=title,
            description=description,
            schedule_type=ScheduleType.TEMPORARY,
            start_time=start_dt.isoformat(),
            end_time=end_dt.isoformat(),
            priority=SchedulePriority.LOW,
            generated_reason="自动生成的临时日程"
        )
        
        if success:
            created_schedules.append(schedule.to_dict())
        
        return created_schedules

    def has_temporary_schedules_today(self) -> bool:
        """
        检查今天是否已有临时日程

        Returns:
            是否已有临时日程
        """
        today = datetime.now().date().isoformat()
        start_of_day = f"{today}T00:00:00"
        end_of_day = f"{today}T23:59:59"
        
        schedules = self.schedule_manager.get_schedules_by_time_range(start_of_day, end_of_day)
        
        # 检查是否有临时日程
        return any(s.schedule_type == ScheduleType.TEMPORARY for s in schedules)
