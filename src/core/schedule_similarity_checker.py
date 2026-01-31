"""
日程相似度检查工具
用于检查同一天内的相似日程，并使用LLM判断应保留哪一个
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv 不可用时跳过
    pass

import requests
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class ScheduleSimilarityChecker:
    """
    日程相似度检查工具
    使用LLM判断两个日程是否相似，以及应该保留哪一个
    """

    def __init__(self):
        """初始化日程相似度检查工具"""
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        self.temperature = 0.3  # 使用较低的温度以获得更确定的输出
        self.max_tokens = 800

        debug_logger.log_module('ScheduleSimilarityChecker', '日程相似度检查工具初始化完成')

    def check_similar_schedules(
        self,
        new_schedule: Dict[str, Any],
        existing_schedules: List[Dict[str, Any]]
    ) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
        """
        检查新日程是否与当天已有日程相似
        
        Args:
            new_schedule: 新日程信息字典
            existing_schedules: 当天已有的日程列表
            
        Returns:
            (是否有相似日程, 应保留的日程ID, LLM判断结果)
        """
        if not existing_schedules:
            debug_logger.log_info('ScheduleSimilarityChecker', '当天没有其他日程，无需检查相似度')
            return False, None, None
        
        debug_logger.log_module('ScheduleSimilarityChecker', '开始检查日程相似度', {
            'new_schedule': new_schedule.get('title'),
            'existing_count': len(existing_schedules)
        })
        
        # 逐一检查每个已有日程
        for existing in existing_schedules:
            result = self._compare_two_schedules(new_schedule, existing)
            
            if result and result.get('is_similar'):
                # 发现相似日程
                schedule_to_keep = result.get('keep_schedule')
                
                if schedule_to_keep == 'new':
                    # 保留新日程，删除旧日程
                    debug_logger.log_info('ScheduleSimilarityChecker', 
                        f"发现相似日程，LLM建议保留新日程「{new_schedule.get('title')}」")
                    return True, existing['schedule_id'], result
                elif schedule_to_keep == 'existing':
                    # 保留旧日程，不创建新日程
                    debug_logger.log_info('ScheduleSimilarityChecker', 
                        f"发现相似日程，LLM建议保留已有日程「{existing.get('title')}」")
                    return True, None, result
        
        # 没有发现相似日程
        debug_logger.log_info('ScheduleSimilarityChecker', '未发现相似日程')
        return False, None, None

    def _compare_two_schedules(
        self,
        schedule1: Dict[str, Any],
        schedule2: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        使用LLM比较两个日程是否相似
        
        Args:
            schedule1: 第一个日程（新日程）
            schedule2: 第二个日程（已有日程）
            
        Returns:
            LLM判断结果字典，包含is_similar和keep_schedule字段
        """
        system_prompt = """你是一个日程管理专家。你需要判断两个日程是否相似，以及应该保留哪一个。

判断标准：
1. 如果两个日程的主题、活动内容基本一致，视为相似日程
2. 即使时间、地点略有差异，但如果核心活动相同，也视为相似
3. 如果一个日程明确说明是与另一个日程不同的活动，则不相似
4. 如果两个日程的标题或描述明确表明是不同的事情，则不相似

如果两个日程相似，应该保留信息更详细、更完整的那一个：
- 比较标题和描述的详细程度
- 比较时间信息的明确程度
- 比较其他元数据的丰富程度

请返回JSON格式的判断结果：
{
    "is_similar": true/false,  // 是否相似
    "reason": "判断理由",  // 详细说明判断的理由
    "keep_schedule": "new"/"existing"/"none"  // 应保留哪个（new=新日程, existing=已有日程, none=不相似无需选择）
}"""

        # 格式化日程信息
        schedule1_info = self._format_schedule_for_llm(schedule1, "新日程")
        schedule2_info = self._format_schedule_for_llm(schedule2, "已有日程")

        user_prompt = f"""请判断以下两个日程是否相似，如果相似，应该保留哪一个：

{schedule1_info}

{schedule2_info}

请分析这两个日程，并返回JSON格式的判断结果。"""

        try:
            # 调用LLM进行相似度判断
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

            debug_logger.log_request('ScheduleSimilarityChecker', self.api_url, payload, headers)

            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            elapsed_time = time.time() - start_time

            debug_logger.log_response('ScheduleSimilarityChecker', response.status_code, response.text, elapsed_time)

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                
                # 尝试解析JSON结果
                try:
                    # 提取JSON部分（可能被包裹在markdown代码块中）
                    import re
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
                    if json_match:
                        content = json_match.group(1)
                    
                    parsed_result = json.loads(content)
                    
                    # 验证结果格式
                    if 'is_similar' in parsed_result and 'keep_schedule' in parsed_result:
                        debug_logger.log_info('ScheduleSimilarityChecker', 
                            f"LLM判断结果：相似={parsed_result['is_similar']}, 保留={parsed_result.get('keep_schedule')}")
                        return parsed_result
                    else:
                        debug_logger.log_error('ScheduleSimilarityChecker', 'LLM返回结果格式不正确')
                        return None
                        
                except json.JSONDecodeError as e:
                    debug_logger.log_error('ScheduleSimilarityChecker', f'解析LLM响应JSON失败: {str(e)}')
                    debug_logger.log_info('ScheduleSimilarityChecker', f'原始响应: {content}')
                    return None
            else:
                debug_logger.log_error('ScheduleSimilarityChecker', f'LLM API请求失败: {response.status_code}')
                return None
                
        except requests.exceptions.Timeout:
            debug_logger.log_error('ScheduleSimilarityChecker', 'LLM API请求超时')
            return None
        except Exception as e:
            debug_logger.log_error('ScheduleSimilarityChecker', f'相似度检查失败: {str(e)}', e)
            return None

    def _format_schedule_for_llm(self, schedule: Dict[str, Any], label: str) -> str:
        """
        格式化日程信息供LLM分析
        
        Args:
            schedule: 日程信息字典
            label: 标签（如"新日程"或"已有日程"）
            
        Returns:
            格式化的日程信息字符串
        """
        lines = [f"【{label}】"]
        lines.append(f"标题：{schedule.get('title', '无')}")
        lines.append(f"描述：{schedule.get('description', '无')}")
        lines.append(f"开始时间：{schedule.get('start_time', '无')}")
        lines.append(f"结束时间：{schedule.get('end_time', '无')}")
        lines.append(f"类型：{schedule.get('schedule_type', '无')}")
        
        # 添加元数据信息（如果有）
        metadata = schedule.get('metadata', {})
        if metadata:
            lines.append(f"附加信息：{json.dumps(metadata, ensure_ascii=False)}")
        
        return '\n'.join(lines)


def get_schedules_on_same_day(
    schedule_manager,
    target_date: str,
    exclude_schedule_id: str = None
) -> List[Dict[str, Any]]:
    """
    获取指定日期当天的所有日程
    
    Args:
        schedule_manager: 日程管理器实例
        target_date: 目标日期（ISO格式，如"2024-01-15T10:00:00"）
        exclude_schedule_id: 要排除的日程ID（可选）
        
    Returns:
        当天的日程列表
    """
    try:
        # 解析目标日期
        dt = datetime.fromisoformat(target_date.replace('Z', '+00:00'))
        day_start = dt.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = dt.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # 查询当天的日程
        schedules = schedule_manager.get_schedules_by_time_range(
            start_time=day_start.isoformat(),
            end_time=day_end.isoformat(),
            include_inactive=False
        )
        
        # 排除指定的日程ID
        if exclude_schedule_id:
            schedules = [s for s in schedules if s.schedule_id != exclude_schedule_id]
        
        # 转换为字典列表
        return [s.to_dict() for s in schedules]
        
    except Exception as e:
        debug_logger.log_error('ScheduleSimilarityChecker', f'获取当天日程失败: {str(e)}', e)
        return []
