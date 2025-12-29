"""
个性化表达风格模块
负责管理智能体的个性化表达和学习用户的表达习惯
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests
from database_manager import DatabaseManager
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class ExpressionStyleManager:
    """
    个性化表达风格管理器
    负责：
    1. 管理智能体的个性化表达（如 'wc' => '表示对突发事情的感叹'）
    2. 学习和总结用户的表达习惯
    """

    # 类级别的常量配置
    LEARNING_INTERVAL = 10  # 用户表达习惯学习间隔（每N轮）
    MIN_MESSAGES_FOR_LEARNING = 3  # 学习所需的最小用户消息数量
    CONFIDENCE_INCREMENT = 0.1  # 每次确认习惯时的置信度增加值

    def __init__(self,
                 db_manager: DatabaseManager = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化个性化表达风格管理器

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 使用共享的数据库管理器
        self.db = db_manager or DatabaseManager()

        # API配置（用于学习用户表达习惯）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 用户表达习惯学习间隔（保留实例属性以保持兼容性）
        self.learning_interval = self.LEARNING_INTERVAL

        debug_logger.log_module('ExpressionStyleManager', '个性化表达风格管理器初始化完成')
        print(f"✓ 个性化表达风格管理器已初始化")

    # ==================== 智能体表达管理 ====================

    def add_agent_expression(self, expression: str, meaning: str, category: str = "通用") -> str:
        """
        添加智能体个性化表达

        Args:
            expression: 表达方式（如 'wc'、'hhh'、'orz'）
            meaning: 含义（如 '表示对突发事情的感叹'）
            category: 分类（如 '感叹词'、'网络用语'、'表情替代'）

        Returns:
            表达UUID
        """
        debug_logger.log_info('ExpressionStyleManager', '添加智能体表达', {
            'expression': expression,
            'meaning': meaning,
            'category': category
        })

        expr_uuid = self.db.add_agent_expression(expression, meaning, category)
        print(f"✓ 已添加智能体表达: '{expression}' => '{meaning}'")
        return expr_uuid

    def get_agent_expressions(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        获取所有智能体个性化表达

        Args:
            active_only: 是否只获取激活的表达

        Returns:
            表达列表
        """
        return self.db.get_all_agent_expressions(active_only)

    def update_agent_expression(self, expr_uuid: str, **kwargs) -> bool:
        """
        更新智能体表达

        Args:
            expr_uuid: 表达UUID
            **kwargs: 要更新的字段

        Returns:
            是否更新成功
        """
        return self.db.update_agent_expression(expr_uuid, **kwargs)

    def delete_agent_expression(self, expr_uuid: str) -> bool:
        """
        删除智能体表达

        Args:
            expr_uuid: 表达UUID

        Returns:
            是否删除成功
        """
        return self.db.delete_agent_expression(expr_uuid)

    def generate_agent_expression_prompt(self) -> str:
        """
        生成智能体个性化表达提示词

        Returns:
            提示词文本
        """
        expressions = self.get_agent_expressions(active_only=True)

        if not expressions:
            return ""

        prompt_parts = ["【个性化表达风格】", "在合适的语境下，你可以使用以下个性化表达方式："]

        for expr in expressions:
            prompt_parts.append(f"  • '{expr['expression']}' => {expr['meaning']}")

        prompt_parts.append("")
        prompt_parts.append("请在回复中自然地融入这些表达，使对话更加生动有趣。")

        return "\n".join(prompt_parts)

    # ==================== 用户表达习惯学习 ====================

    def learn_user_expressions(self, messages: List[Dict[str, Any]], 
                               current_round: int = 0) -> List[Dict[str, Any]]:
        """
        从对话中学习用户的表达习惯

        Args:
            messages: 最近的对话消息列表（只分析用户消息）
            current_round: 当前对话轮次（用于记录学习来源）

        Returns:
            学习到的表达习惯列表
        """
        debug_logger.log_module('ExpressionStyleManager', '开始学习用户表达习惯', {
            'message_count': len(messages),
            'current_round': current_round
        })

        # 只提取用户消息
        user_messages = [msg for msg in messages if msg.get('role') == 'user']

        if len(user_messages) < self.MIN_MESSAGES_FOR_LEARNING:
            debug_logger.log_info('ExpressionStyleManager', '用户消息太少，跳过学习')
            return []

        # 构建用户消息文本
        user_text = "\n".join([msg['content'] for msg in user_messages])

        # 使用LLM分析用户表达习惯
        learned_habits = self._analyze_user_expressions(user_text, current_round)

        if learned_habits:
            debug_logger.log_info('ExpressionStyleManager', '学习到用户表达习惯', {
                'count': len(learned_habits)
            })

            # 保存学习到的习惯
            for habit in learned_habits:
                existing = self.db.find_user_expression_habit(habit['expression_pattern'])
                if existing:
                    # 更新现有习惯的频率和置信度
                    new_confidence = min(1.0, existing['confidence'] + self.CONFIDENCE_INCREMENT)
                    self.db.increment_habit_frequency(existing['uuid'])
                    self.db.update_user_expression_habit(
                        existing['uuid'],
                        confidence=new_confidence,
                        meaning=habit['meaning']  # 可能有更新的理解
                    )
                    print(f"  ✓ 更新用户习惯: '{habit['expression_pattern']}' (频率+1, 置信度={new_confidence:.2f})")
                else:
                    # 添加新习惯
                    self.db.add_user_expression_habit(
                        expression_pattern=habit['expression_pattern'],
                        meaning=habit['meaning'],
                        confidence=habit.get('confidence', 0.7),
                        learned_from_rounds=str(current_round)
                    )
                    print(f"  ✓ 新增用户习惯: '{habit['expression_pattern']}' => '{habit['meaning']}'")

        return learned_habits

    def _analyze_user_expressions(self, user_text: str, current_round: int) -> List[Dict[str, Any]]:
        """
        使用LLM分析用户的表达习惯

        Args:
            user_text: 用户消息文本
            current_round: 当前对话轮次

        Returns:
            分析出的表达习惯列表
        """
        try:
            analysis_prompt = f"""请分析以下用户消息中的表达习惯和特殊用语。

用户消息：
{user_text}

请识别用户使用的：
1. 网络用语/缩写（如 'hhh'、'2333'、'xswl' 等）
2. 口头禅或常用表达
3. 特殊的表达方式或语气词
4. 个人化的表达习惯

对于每个识别到的表达，请分析其含义和使用场景。

返回JSON格式（只返回JSON数组，不要其他文字）：
[
  {{
    "expression_pattern": "表达内容",
    "meaning": "含义和使用场景",
    "confidence": 0.8
  }}
]

如果没有识别到特殊表达习惯，返回空数组 []"""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的语言分析助手，擅长识别用户的表达习惯和特殊用语。你只返回JSON格式的数据。'},
                    {'role': 'user', 'content': analysis_prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 1000,
                'stream': False
            }

            debug_logger.log_request('ExpressionStyleManager', self.api_url, payload, headers)

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            debug_logger.log_response('ExpressionStyleManager', result, response.status_code, 0)

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                # 使用更健壮的JSON提取逻辑
                json_content = self._extract_json_from_response(content)

                try:
                    habits = json.loads(json_content)
                    if isinstance(habits, list):
                        return habits
                    else:
                        debug_logger.log_error('ExpressionStyleManager', '返回的不是列表格式')
                        return []
                except json.JSONDecodeError as e:
                    debug_logger.log_error('ExpressionStyleManager', f'JSON解析失败: {e}')
                    return []
            else:
                debug_logger.log_error('ExpressionStyleManager', '未能获取有效的分析结果')
                return []

        except Exception as e:
            debug_logger.log_error('ExpressionStyleManager', f'分析用户表达习惯时出错: {e}', e)
            print(f"✗ 分析用户表达习惯时出错: {e}")
            return []

    def _extract_json_from_response(self, content: str) -> str:
        """
        从LLM响应中提取JSON内容

        Args:
            content: LLM响应内容

        Returns:
            提取的JSON字符串
        """
        import re

        # 尝试方法1：直接解析（如果内容本身就是有效JSON）
        try:
            json.loads(content)
            return content
        except json.JSONDecodeError:
            pass

        # 尝试方法2：使用正则表达式提取JSON数组
        json_array_pattern = r'\[[\s\S]*?\]'
        matches = re.findall(json_array_pattern, content)
        for match in matches:
            try:
                json.loads(match)
                return match
            except json.JSONDecodeError:
                continue

        # 尝试方法3：处理markdown代码块
        if '```' in content:
            # 提取所有代码块
            code_blocks = re.findall(r'```(?:json)?\s*([\s\S]*?)```', content)
            for block in code_blocks:
                block = block.strip()
                try:
                    json.loads(block)
                    return block
                except json.JSONDecodeError:
                    continue

        # 如果都失败了，返回空数组字符串
        return '[]'

    def get_user_expression_habits(self, min_confidence: float = 0.5) -> List[Dict[str, Any]]:
        """
        获取用户表达习惯

        Args:
            min_confidence: 最低置信度

        Returns:
            习惯列表
        """
        return self.db.get_all_user_expression_habits(min_confidence)

    def generate_user_expression_context(self) -> str:
        """
        生成用户表达习惯上下文提示词

        Returns:
            提示词文本
        """
        habits = self.get_user_expression_habits(min_confidence=0.6)

        if not habits:
            return ""

        prompt_parts = ["【用户表达习惯参考】", "根据历史对话，用户有以下表达习惯："]

        for habit in habits[:10]:  # 最多显示10个习惯
            confidence_label = "高" if habit['confidence'] >= 0.8 else "中"
            prompt_parts.append(f"  • '{habit['expression_pattern']}' => {habit['meaning']} [置信度: {confidence_label}]")

        prompt_parts.append("")
        prompt_parts.append("理解用户的这些表达习惯可以帮助你更好地理解用户的意图。")

        return "\n".join(prompt_parts)

    def clear_user_expression_habits(self) -> bool:
        """
        清空所有用户表达习惯

        Returns:
            是否清空成功
        """
        return self.db.clear_user_expression_habits()

    # ==================== 统计方法 ====================

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取表达风格统计信息

        Returns:
            统计信息字典
        """
        agent_expressions = self.db.get_all_agent_expressions(active_only=False)
        user_habits = self.db.get_all_user_expression_habits()

        return {
            'agent_expressions': {
                'total': len(agent_expressions),
                'active': sum(1 for e in agent_expressions if e.get('is_active', 1)),
                'total_usage': sum(e.get('usage_count', 0) for e in agent_expressions)
            },
            'user_habits': {
                'total': len(user_habits),
                'high_confidence': sum(1 for h in user_habits if h.get('confidence', 0) >= 0.8),
                'medium_confidence': sum(1 for h in user_habits if 0.5 <= h.get('confidence', 0) < 0.8)
            }
        }


if __name__ == '__main__':
    print("=" * 60)
    print("个性化表达风格管理器测试")
    print("=" * 60)

    manager = ExpressionStyleManager()

    # 测试添加智能体表达
    print("\n测试添加智能体表达:")
    manager.add_agent_expression("wc", "表示对突发事情的感叹", "感叹词")
    manager.add_agent_expression("hhh", "表示开心、高兴的笑声", "笑声表达")
    manager.add_agent_expression("orz", "表示跪拜、佩服或无奈", "表情替代")

    # 显示所有智能体表达
    print("\n当前智能体表达:")
    expressions = manager.get_agent_expressions()
    for expr in expressions:
        print(f"  • '{expr['expression']}' => {expr['meaning']} (使用次数: {expr['usage_count']})")

    # 生成提示词
    print("\n生成的智能体表达提示词:")
    prompt = manager.generate_agent_expression_prompt()
    print(prompt)

    # 显示统计
    print("\n统计信息:")
    stats = manager.get_statistics()
    print(f"  智能体表达总数: {stats['agent_expressions']['total']}")
    print(f"  用户习惯总数: {stats['user_habits']['total']}")

    print("\n✓ 测试完成")
