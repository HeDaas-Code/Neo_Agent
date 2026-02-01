"""
SysTime - 系统时间工具
用于获取当前系统时间并提供给智能体作为上下文信息
"""

from datetime import datetime
from typing import Dict, Any


def get_system_time(context: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    获取当前系统时间

    Args:
        context: 执行上下文（可选）

    Returns:
        包含时间信息的字典
    """
    now = datetime.now()
    
    # 获取星期几
    weekday_names = ['星期一', '星期二', '星期三', '星期四', '星期五', '星期六', '星期日']
    weekday = weekday_names[now.weekday()]
    
    # 判断时段
    hour = now.hour
    if 5 <= hour < 9:
        period = '清晨'
    elif 9 <= hour < 12:
        period = '上午'
    elif 12 <= hour < 14:
        period = '中午'
    elif 14 <= hour < 18:
        period = '下午'
    elif 18 <= hour < 22:
        period = '晚上'
    else:
        period = '深夜'
    
    # 格式化时间字符串
    time_str = now.strftime('%Y年%m月%d日 %H:%M:%S')
    short_time = now.strftime('%H:%M')
    
    # 构建上下文描述
    context_desc = f"现在是{time_str}，{weekday}，{period}"
    
    return {
        'datetime': now.isoformat(),
        'date': now.strftime('%Y-%m-%d'),
        'time': now.strftime('%H:%M:%S'),
        'short_time': short_time,
        'year': now.year,
        'month': now.month,
        'day': now.day,
        'hour': now.hour,
        'minute': now.minute,
        'second': now.second,
        'weekday': weekday,
        'period': period,
        'context': context_desc
    }
