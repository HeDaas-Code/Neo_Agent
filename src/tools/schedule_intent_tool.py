"""
日程意图识别工具
用于识别用户输入中的日程相关意图和邀约信息
"""

import os
import re
import json
import time
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv
import requests
from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()

# 星期映射常量
WEEKDAY_MAP = {
    '一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6,
    '1': 0, '2': 1, '3': 2, '4': 3, '5': 4, '6': 5, '7': 6
}


class ScheduleIntentTool:
    """
    日程意图识别工具
    使用LLM识别用户输入中的日程邀约和时间信息
    """

    def __init__(self):
        """初始化日程意图识别工具"""
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        self.temperature = 0.3  # 使用较低的温度以获得更确定的输出
        self.max_tokens = 500

        debug_logger.log_module('ScheduleIntentTool', '日程意图识别工具初始化完成')

    def recognize_intent(
        self,
        user_input: str,
        character_name: str = "智能体",
        context: str = ""
    ) -> Dict[str, Any]:
        """
        识别用户输入中的日程意图

        Args:
            user_input: 用户输入
            character_name: 智能体名称
            context: 对话上下文

        Returns:
            识别结果字典，包含：
            - has_schedule_intent: 是否包含日程意图
            - schedule_type: 日程类型（appointment/query）
            - title: 日程标题
            - description: 日程描述
            - start_time: 开始时间（ISO格式）
            - end_time: 结束时间（ISO格式）
            - involves_agent: 是否涉及智能体
            - involves_user: 是否涉及用户
            - confidence: 置信度（0-1）
        """
        debug_logger.log_module('ScheduleIntentTool', '开始识别日程意图', {
            'input_length': len(user_input)
        })

        # 构建识别提示词
        system_prompt = f"""你是一个日程意图识别专家。请分析用户输入，识别其中是否包含日程相关的意图。

智能体名称：{character_name}

分析要点：
1. 判断是否包含邀约、约定、计划等日程相关内容
2. 提取时间信息（具体时间或相对时间如"明天"、"下周三"）
3. 判断是创建日程还是查询日程
4. 识别主语（当用户没有明确主语时，根据语境判断）
5. 判断是否涉及智能体和/或用户

请以JSON格式输出分析结果：
{{
    "has_schedule_intent": true/false,
    "schedule_type": "appointment"/"query"/"none",
    "title": "日程标题",
    "description": "详细描述",
    "time_expression": "提取的时间表达",
    "start_time": "ISO格式时间或null",
    "end_time": "ISO格式时间或null",
    "involves_agent": true/false,
    "involves_user": true/false,
    "confidence": 0.0-1.0,
    "reasoning": "分析理由"
}}"""

        user_prompt = f"""用户输入："{user_input}"

{f"对话上下文：{context}" if context else ""}

请分析这段输入，识别日程意图。"""

        try:
            # 调用LLM进行意图识别
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

            debug_logger.log_request('ScheduleIntentTool', self.api_url, payload, headers)

            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            elapsed_time = time.time() - start_time

            debug_logger.log_response('ScheduleIntentTool', response.status_code, response.text, elapsed_time)

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # 尝试解析JSON结果
                try:
                    # 提取JSON部分（可能被包裹在markdown代码块中）
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                    
                    intent_result = json.loads(content)
                    
                    # 补充处理相对时间表达
                    if intent_result.get('has_schedule_intent') and not intent_result.get('start_time'):
                        time_expr = intent_result.get('time_expression', '')
                        if time_expr:
                            start_time, end_time = self._parse_time_expression(time_expr)
                            if start_time:
                                intent_result['start_time'] = start_time
                                intent_result['end_time'] = end_time
                    
                    debug_logger.log_info('ScheduleIntentTool', '意图识别成功', intent_result)
                    return intent_result
                    
                except json.JSONDecodeError as e:
                    debug_logger.log_error('ScheduleIntentTool', f'解析JSON失败: {content}', e)
                    return self._get_fallback_result()
            else:
                debug_logger.log_error('ScheduleIntentTool', f'API调用失败: {response.status_code}')
                return self._get_fallback_result()

        except Exception as e:
            debug_logger.log_error('ScheduleIntentTool', f'意图识别异常: {str(e)}', e)
            return self._get_fallback_result()

    def _parse_time_expression(self, time_expr: str) -> Tuple[Optional[str], Optional[str]]:
        """
        解析时间表达式为ISO格式时间

        Args:
            time_expr: 时间表达式（如"明天下午3点"、"周三上午"）

        Returns:
            (开始时间, 结束时间) ISO格式或 (None, None)
        """
        now = datetime.now()
        
        # 相对日期关键词
        if "明天" in time_expr or "明日" in time_expr:
            target_date = now + timedelta(days=1)
        elif "后天" in time_expr:
            target_date = now + timedelta(days=2)
        elif "大后天" in time_expr:
            target_date = now + timedelta(days=3)
        elif "下周" in time_expr:
            # 找到下周的对应星期
            weekday_match = re.search(r'[周星期]([一二三四五六日天1-7])', time_expr)
            if weekday_match:
                target_weekday = WEEKDAY_MAP.get(weekday_match.group(1), 0)
                days_ahead = target_weekday - now.weekday() + 7
                if days_ahead <= 7:
                    days_ahead += 7
                target_date = now + timedelta(days=days_ahead)
            else:
                target_date = now + timedelta(days=7)
        elif "今天" in time_expr or "今日" in time_expr:
            target_date = now
        else:
            # 尝试匹配本周的星期
            weekday_match = re.search(r'[周星期]([一二三四五六日天1-7])', time_expr)
            if weekday_match:
                target_weekday = WEEKDAY_MAP.get(weekday_match.group(1), 0)
                days_ahead = target_weekday - now.weekday()
                if days_ahead < 0:
                    days_ahead += 7
                target_date = now + timedelta(days=days_ahead)
            else:
                return None, None

        # 提取时间
        hour = 14  # 默认下午2点
        minute = 0
        
        # 匹配具体时间
        time_match = re.search(r'(\d{1,2})[点时:：](\d{1,2})?', time_expr)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
        else:
            # 根据时段关键词设置时间
            if "早上" in time_expr or "上午" in time_expr or "早晨" in time_expr:
                hour = 9
            elif "中午" in time_expr:
                hour = 12
            elif "下午" in time_expr:
                hour = 14
            elif "晚上" in time_expr or "傍晚" in time_expr:
                hour = 18
            elif "夜里" in time_expr or "深夜" in time_expr:
                hour = 22

        # 构建ISO格式时间
        start_datetime = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
        end_datetime = start_datetime + timedelta(hours=2)  # 默认持续2小时
        
        return start_datetime.isoformat(), end_datetime.isoformat()

    def _get_fallback_result(self) -> Dict[str, Any]:
        """
        获取降级结果（当LLM不可用时）

        Returns:
            默认的意图识别结果
        """
        return {
            'has_schedule_intent': False,
            'schedule_type': 'none',
            'title': '',
            'description': '',
            'time_expression': '',
            'start_time': None,
            'end_time': None,
            'involves_agent': False,
            'involves_user': False,
            'confidence': 0.0,
            'reasoning': '意图识别服务不可用'
        }

    def is_query_schedule(self, user_input: str) -> bool:
        """
        快速判断是否为查询日程的意图

        Args:
            user_input: 用户输入

        Returns:
            是否为查询日程意图
        """
        query_keywords = [
            '日程', '安排', '计划', '行程',
            '什么时候', '有什么事', '忙不忙',
            '空闲', '有空', '在干什么', '在做什么'
        ]
        
        user_input_lower = user_input.lower()
        return any(keyword in user_input_lower for keyword in query_keywords)
