"""
Debug日志管理器
用于记录系统运行时的详细调试信息，包括提示词、请求、响应等
"""

import os
import sys
import traceback
from datetime import datetime
from typing import List, Dict, Any, Optional
import json


class DebugLogger:
    """
    Debug日志记录器
    记录模块运行、提示词变化、API请求/响应等调试信息
    """

    def __init__(self, debug_mode: bool = False, log_file: str = None):
        """
        初始化Debug日志记录器

        Args:
            debug_mode: 是否启用debug模式
            log_file: 日志文件路径（可选）
        """
        self.debug_mode = debug_mode
        self.log_file = log_file or 'debug.log'

        # 内存中的日志列表（用于GUI显示）
        self.logs: List[Dict[str, Any]] = []

        # 日志类型统计
        self.log_stats = {
            'module': 0,
            'prompt': 0,
            'request': 0,
            'response': 0,
            'error': 0,
            'info': 0
        }

        # 日志监听器（用于实时更新GUI）
        self.listeners = []

        if self.debug_mode:
            print(f"✓ Debug模式已启用 | 日志文件: {self.log_file}")
            self._init_log_file()

    def _init_log_file(self):
        """初始化日志文件"""
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write(f"Debug日志 - {datetime.now().isoformat()}\n")
                f.write("=" * 80 + "\n\n")
        except Exception as e:
            print(f"✗ 初始化日志文件失败: {e}")

    def add_listener(self, callback):
        """
        添加日志监听器（用于GUI实时更新）

        Args:
            callback: 回调函数，接收日志字典作为参数
        """
        self.listeners.append(callback)

    def remove_listener(self, callback):
        """移除日志监听器"""
        if callback in self.listeners:
            self.listeners.remove(callback)

    def _notify_listeners(self, log_entry: Dict[str, Any]):
        """通知所有监听器"""
        for listener in self.listeners:
            try:
                listener(log_entry)
            except Exception as e:
                print(f"✗ 通知监听器失败: {e}")

    def _write_to_file(self, message: str):
        """写入日志文件"""
        if not self.debug_mode:
            return

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception as e:
            print(f"✗ 写入日志文件失败: {e}")

    def log_module(self, module_name: str, action: str, details: str = ""):
        """
        记录模块运行信息

        Args:
            module_name: 模块名称
            action: 动作描述
            details: 详细信息
        """
        if not self.debug_mode:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'module',
            'module': module_name,
            'action': action,
            'details': details
        }

        self.logs.append(log_entry)
        self.log_stats['module'] += 1

        message = f"[{log_entry['timestamp']}] [MODULE] {module_name} | {action}"
        if details:
            message += f"\n  详情: {details}"

        print(message)
        self._write_to_file(message)
        self._notify_listeners(log_entry)

    def log_prompt(self, module_name: str, prompt_type: str, prompt_content: str, metadata: Dict[str, Any] = None):
        """
        记录提示词信息

        Args:
            module_name: 模块名称
            prompt_type: 提示词类型（system/user/assistant）
            prompt_content: 提示词内容
            metadata: 元数据（如温度、最大token等）
        """
        if not self.debug_mode:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'prompt',
            'module': module_name,
            'prompt_type': prompt_type,
            'content': prompt_content,
            'metadata': metadata or {}
        }

        self.logs.append(log_entry)
        self.log_stats['prompt'] += 1

        # 截断过长的内容
        display_content = prompt_content[:200] + "..." if len(prompt_content) > 200 else prompt_content

        message = f"[{log_entry['timestamp']}] [PROMPT] {module_name} | {prompt_type}\n"
        message += f"  内容: {display_content}"
        if metadata:
            message += f"\n  元数据: {json.dumps(metadata, ensure_ascii=False)}"

        print(message)
        self._write_to_file(message)
        self._write_to_file(f"  完整内容:\n{prompt_content}\n")
        self._notify_listeners(log_entry)

    def log_request(self, module_name: str, api_url: str, payload: Dict[str, Any], headers: Dict[str, str] = None):
        """
        记录API请求信息

        Args:
            module_name: 模块名称
            api_url: API地址
            payload: 请求负载
            headers: 请求头
        """
        if not self.debug_mode:
            return

        # 隐藏敏感信息
        safe_headers = {}
        if headers:
            safe_headers = {k: (v if k.lower() != 'authorization' else '***') for k, v in headers.items()}

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'request',
            'module': module_name,
            'api_url': api_url,
            'payload': payload,
            'headers': safe_headers
        }

        self.logs.append(log_entry)
        self.log_stats['request'] += 1

        message = f"[{log_entry['timestamp']}] [REQUEST] {module_name}\n"
        message += f"  API: {api_url}\n"
        message += f"  Payload: {json.dumps(payload, ensure_ascii=False, indent=2)[:500]}..."

        print(message)
        self._write_to_file(message)
        self._write_to_file(f"  完整Payload:\n{json.dumps(payload, ensure_ascii=False, indent=2)}\n")
        self._notify_listeners(log_entry)

    def log_response(self, module_name: str, response_data: Any, status_code: int = 200, elapsed_time: float = 0):
        """
        记录API响应信息

        Args:
            module_name: 模块名称
            response_data: 响应数据
            status_code: HTTP状态码
            elapsed_time: 响应时间（秒）
        """
        if not self.debug_mode:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'response',
            'module': module_name,
            'status_code': status_code,
            'elapsed_time': elapsed_time,
            'response': response_data
        }

        self.logs.append(log_entry)
        self.log_stats['response'] += 1

        response_str = json.dumps(response_data, ensure_ascii=False) if isinstance(response_data, dict) else str(response_data)
        display_response = response_str[:300] + "..." if len(response_str) > 300 else response_str

        message = f"[{log_entry['timestamp']}] [RESPONSE] {module_name}\n"
        message += f"  状态码: {status_code} | 耗时: {elapsed_time:.2f}s\n"
        message += f"  响应: {display_response}"

        print(message)
        self._write_to_file(message)
        self._write_to_file(f"  完整响应:\n{response_str}\n")
        self._notify_listeners(log_entry)

    def log_error(self, module_name: str, error_message: str, exception: Exception = None):
        """
        记录错误信息（包含文件和行号）

        Args:
            module_name: 模块名称
            error_message: 错误消息
            exception: 异常对象
        """
        if not self.debug_mode:
            return

        # 获取堆栈跟踪信息
        traceback_info = None
        file_info = None
        if exception:
            tb = sys.exc_info()[2]
            if tb:
                # 提取堆栈帧
                frames = traceback.extract_tb(tb)
                if frames:
                    # 获取最后一帧（错误发生的位置）
                    last_frame = frames[-1]
                    file_info = {
                        'filename': last_frame.filename,
                        'line': last_frame.lineno,
                        'function': last_frame.name,
                        'code': last_frame.line
                    }
                    traceback_info = ''.join(traceback.format_exception(type(exception), exception, tb))

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'error',
            'module': module_name,
            'message': error_message,
            'exception': str(exception) if exception else None,
            'file_info': file_info,
            'traceback': traceback_info
        }

        self.logs.append(log_entry)
        self.log_stats['error'] += 1

        message = f"[{log_entry['timestamp']}] [ERROR] {module_name}\n"
        message += f"  错误: {error_message}"
        if exception:
            message += f"\n  异常: {str(exception)}"
        if file_info:
            message += f"\n  位置: {file_info['filename']}:{file_info['line']} in {file_info['function']}()"
            if file_info['code']:
                message += f"\n  代码: {file_info['code']}"
        
        print(message)
        self._write_to_file(message)
        if traceback_info:
            self._write_to_file(f"  完整堆栈:\n{traceback_info}")
        self._notify_listeners(log_entry)

    def log_info(self, module_name: str, message: str, data: Any = None):
        """
        记录一般信息

        Args:
            module_name: 模块名称
            message: 信息内容
            data: 附加数据
        """
        if not self.debug_mode:
            return

        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'info',
            'module': module_name,
            'message': message,
            'data': data
        }

        self.logs.append(log_entry)
        self.log_stats['info'] += 1

        log_message = f"[{log_entry['timestamp']}] [INFO] {module_name} | {message}"
        if data:
            log_message += f"\n  数据: {json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)}"

        print(log_message)
        self._write_to_file(log_message)
        self._notify_listeners(log_entry)

    def get_logs(self, log_type: str = None, module_name: str = None, limit: int = None) -> List[Dict[str, Any]]:
        """
        获取日志列表

        Args:
            log_type: 日志类型筛选
            module_name: 模块名称筛选
            limit: 限制返回数量

        Returns:
            日志列表
        """
        filtered_logs = self.logs

        if log_type:
            filtered_logs = [log for log in filtered_logs if log['type'] == log_type]

        if module_name:
            filtered_logs = [log for log in filtered_logs if log.get('module') == module_name]

        if limit:
            filtered_logs = filtered_logs[-limit:]

        return filtered_logs

    def get_recent_logs(self, count: int = 50) -> List[Dict[str, Any]]:
        """获取最近的日志"""
        return self.logs[-count:]

    def clear_logs(self):
        """清空内存中的日志"""
        self.logs.clear()
        self.log_stats = {key: 0 for key in self.log_stats}
        print("✓ 日志已清空")

    def get_statistics(self) -> Dict[str, Any]:
        """获取日志统计信息"""
        return {
            'total_logs': len(self.logs),
            'by_type': self.log_stats.copy(),
            'debug_mode': self.debug_mode,
            'log_file': self.log_file
        }
    
    @staticmethod
    def format_exception_with_location(exception: Exception, include_traceback: bool = True) -> str:
        """
        格式化异常信息，包含文件位置信息
        
        Args:
            exception: 异常对象
            include_traceback: 是否包含完整堆栈跟踪
            
        Returns:
            格式化的异常信息
        """
        exc_type, exc_value, exc_tb = sys.exc_info()
        
        if not exc_tb:
            return str(exception)
        
        # 提取堆栈帧
        frames = traceback.extract_tb(exc_tb)
        
        if not frames:
            return str(exception)
        
        # 获取最后一帧（错误发生的位置）
        last_frame = frames[-1]
        
        # 构建简短的错误信息（带文件和行号）
        error_msg = f"{exc_type.__name__}: {exc_value}\n"
        error_msg += f"位置: {last_frame.filename}:{last_frame.lineno}\n"
        error_msg += f"函数: {last_frame.name}()"
        
        if last_frame.line:
            error_msg += f"\n代码: {last_frame.line.strip()}"
        
        # 如果需要完整堆栈跟踪
        if include_traceback and len(frames) > 1:
            error_msg += "\n\n完整堆栈跟踪:\n"
            for i, frame in enumerate(frames):
                error_msg += f"  {i+1}. {frame.filename}:{frame.lineno} in {frame.name}()\n"
                if frame.line:
                    error_msg += f"     {frame.line.strip()}\n"
        
        return error_msg

    def format_log_for_display(self, log_entry: Dict[str, Any]) -> str:
        """
        格式化日志用于显示

        Args:
            log_entry: 日志条目

        Returns:
            格式化后的字符串
        """
        timestamp = log_entry['timestamp'][11:19]  # 只取时分秒
        log_type = log_entry['type'].upper()
        module = log_entry.get('module', 'Unknown')

        if log_type == 'MODULE':
            return f"[{timestamp}] [{log_type}] {module} | {log_entry.get('action', '')}"

        elif log_type == 'PROMPT':
            content = log_entry.get('content', '')
            display = content[:80] + "..." if len(content) > 80 else content
            return f"[{timestamp}] [{log_type}] {module} | {log_entry.get('prompt_type', '')} | {display}"

        elif log_type == 'REQUEST':
            return f"[{timestamp}] [{log_type}] {module} | {log_entry.get('api_url', '')}"

        elif log_type == 'RESPONSE':
            elapsed = log_entry.get('elapsed_time', 0)
            status = log_entry.get('status_code', 0)
            return f"[{timestamp}] [{log_type}] {module} | 状态:{status} | 耗时:{elapsed:.2f}s"

        elif log_type == 'ERROR':
            msg = log_entry.get('message', '')
            file_info = log_entry.get('file_info')
            if file_info:
                location = f"{file_info.get('filename', 'unknown')}:{file_info.get('line', '?')}"
                return f"[{timestamp}] [{log_type}] {module} | {msg} @ {location}"
            return f"[{timestamp}] [{log_type}] {module} | {msg}"

        elif log_type == 'INFO':
            return f"[{timestamp}] [{log_type}] {module} | {log_entry.get('message', '')}"

        return f"[{timestamp}] [{log_type}] {module}"


# 全局debug日志记录器实例
_global_logger: Optional[DebugLogger] = None


def get_debug_logger() -> DebugLogger:
    """获取全局debug日志记录器"""
    global _global_logger
    if _global_logger is None:
        # 从环境变量读取debug模式设置
        debug_mode = os.getenv('DEBUG_MODE', 'False').lower() == 'true'
        _global_logger = DebugLogger(debug_mode=debug_mode)
    return _global_logger


def init_debug_logger(debug_mode: bool = False, log_file: str = None):
    """
    初始化全局debug日志记录器

    Args:
        debug_mode: 是否启用debug模式
        log_file: 日志文件路径
    """
    global _global_logger
    _global_logger = DebugLogger(debug_mode=debug_mode, log_file=log_file)
    return _global_logger

