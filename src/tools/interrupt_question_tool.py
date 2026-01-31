"""
中断性提问工具
允许智能体在任务执行过程中向用户提问
"""

from typing import Optional, Callable, Dict, Any
from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class InterruptQuestionTool:
    """
    中断性提问工具类
    智能体可以使用此工具在任务执行过程中向用户提问
    """

    def __init__(self):
        """初始化中断性提问工具"""
        self.question_callback: Optional[Callable] = None
        debug_logger.log_module('InterruptQuestionTool', '中断性提问工具初始化完成')

    def set_question_callback(self, callback: Callable[[str], str]):
        """
        设置提问回调函数

        Args:
            callback: 回调函数，接收问题字符串，返回用户回答字符串
        """
        self.question_callback = callback
        debug_logger.log_info('InterruptQuestionTool', '提问回调函数已设置')

    def ask_user(
        self,
        question: str,
        context: str = ""
    ) -> str:
        """
        向用户提问

        Args:
            question: 要提问的问题
            context: 问题背景上下文

        Returns:
            用户的回答
        """
        debug_logger.log_module('InterruptQuestionTool', '智能体发起提问', {
            'question': question,
            'has_context': bool(context)
        })

        if not self.question_callback:
            debug_logger.log_error(
                'InterruptQuestionTool',
                '提问回调函数未设置',
                None
            )
            return "【系统错误】提问功能未配置"

        # 格式化问题
        formatted_question = self._format_question(question, context)

        # 调用回调函数获取用户回答
        try:
            answer = self.question_callback(formatted_question)
            
            debug_logger.log_info('InterruptQuestionTool', '用户已回答', {
                'question_length': len(question),
                'answer_length': len(answer)
            })

            return answer

        except Exception as e:
            debug_logger.log_error(
                'InterruptQuestionTool',
                f'提问过程出错: {str(e)}',
                e
            )
            return "【系统错误】提问失败"

    def _format_question(self, question: str, context: str = "") -> str:
        """
        格式化问题

        Args:
            question: 原始问题
            context: 上下文

        Returns:
            格式化后的问题
        """
        if context:
            return f"🤔 【智能体提问】\n\n背景：{context}\n\n问题：{question}"
        else:
            return f"🤔 【智能体提问】\n\n{question}"

    def create_tool_description(self) -> Dict[str, Any]:
        """
        创建工具描述（用于智能体理解如何使用此工具）

        Returns:
            工具描述字典
        """
        return {
            'name': 'interrupt_question',
            'description': '''向用户提出问题并等待回答。
            
使用场景：
- 任务信息不明确，需要用户补充
- 需要用户确认某个决策
- 遇到多个选择，需要用户决定
- 需要用户提供具体的参数或数据

使用方法：
调用 ask_user(question, context) 函数
- question: 要问的问题（必填）
- context: 问题的背景说明（可选）

返回：用户的回答字符串

注意：
- 问题应该清晰明确
- 避免一次问太多问题
- 等待用户回答后再继续任务
''',
            'parameters': {
                'question': {
                    'type': 'string',
                    'description': '要向用户提出的问题',
                    'required': True
                },
                'context': {
                    'type': 'string',
                    'description': '问题的背景上下文说明',
                    'required': False
                }
            }
        }
