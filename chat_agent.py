"""
智能对话代理模块
基于LangChain实现的连续对话智能体，支持角色扮演和长效记忆
使用数据库管理器统一管理数据
"""

import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests
from database_manager import DatabaseManager
from long_term_memory import LongTermMemoryManager
from debug_logger import get_debug_logger
from emotion_analyzer import EmotionRelationshipAnalyzer
from agent_vision import AgentVisionTool
from event_manager import EventManager, EventType, EventStatus, NotificationEvent, TaskEvent
from interrupt_question_tool import InterruptQuestionTool
from multi_agent_coordinator import MultiAgentCoordinator
from expression_style import ExpressionStyleManager
from schedule_manager import ScheduleManager, ScheduleType, SchedulePriority
from schedule_intent_tool import ScheduleIntentTool
from schedule_generator import TemporaryScheduleGenerator

# 加载环境变量
load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class MemoryManager:
    """
    记忆管理器
    负责管理对话历史的持久化存储和检索
    """

    def __init__(self, memory_file: str = None):
        """
        初始化记忆管理器

        Args:
            memory_file: 记忆文件路径，如果为None则从环境变量读取
        """
        self.memory_file = memory_file or os.getenv('MEMORY_FILE', 'memory_data.json')
        self.max_messages = int(os.getenv('MAX_MEMORY_MESSAGES', 50))
        self.messages: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

        # 加载已存在的记忆
        self.load_memory()

    def load_memory(self):
        """
        从文件加载历史记忆
        如果文件不存在或格式错误，将创建新的记忆
        """
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.messages = data.get('messages', [])
                    self.metadata = data.get('metadata', {})
                    print(f"成功加载 {len(self.messages)} 条历史记忆")
            else:
                print("未找到历史记忆文件，创建新的记忆")
                self.messages = []
                self.metadata = {
                    'created_at': datetime.now().isoformat(),
                    'total_conversations': 0
                }
        except Exception as e:
            print(f"加载记忆时出错: {e}")
            self.messages = []
            self.metadata = {}

    def save_memory(self):
        """
        将当前记忆保存到文件
        保存格式为JSON，包含消息列表和元数据
        """
        try:
            # 只保留最近的max_messages条消息
            if len(self.messages) > self.max_messages:
                self.messages = self.messages[-self.max_messages:]

            data = {
                'messages': self.messages,
                'metadata': self.metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.memory_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"记忆已保存: {len(self.messages)} 条消息")
        except Exception as e:
            print(f"保存记忆时出错: {e}")

    def add_message(self, role: str, content: str):
        """
        添加新消息到记忆中

        Args:
            role: 角色类型 ('user' 或 'assistant')
            content: 消息内容
        """
        message = {
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }
        self.messages.append(message)

        # 更新元数据
        if role == 'user':
            self.metadata['total_conversations'] = self.metadata.get('total_conversations', 0) + 1

    def get_recent_messages(self, count: int = 10) -> List[Dict[str, str]]:
        """
        获取最近的N条消息

        Args:
            count: 要获取的消息数量

        Returns:
            消息列表，格式为LangChain所需的格式
        """
        recent = self.messages[-count:] if len(self.messages) > count else self.messages
        # 转换为LangChain格式（去除timestamp）
        return [{'role': msg['role'], 'content': msg['content']} for msg in recent]

    def clear_memory(self):
        """
        清空所有记忆
        """
        self.messages = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'total_conversations': 0
        }
        self.save_memory()
        print("记忆已清空")

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            包含统计信息的字典
        """
        user_messages = sum(1 for msg in self.messages if msg['role'] == 'user')
        assistant_messages = sum(1 for msg in self.messages if msg['role'] == 'assistant')

        return {
            'total_messages': len(self.messages),
            'user_messages': user_messages,
            'assistant_messages': assistant_messages,
            'total_conversations': self.metadata.get('total_conversations', 0),
            'created_at': self.metadata.get('created_at', 'Unknown'),
            'memory_file': self.memory_file
        }


class CharacterProfile:
    """
    角色档案类
    从环境变量读取并管理角色设定
    """

    def __init__(self):
        """
        初始化角色档案，从.env文件读取配置
        """
        self.name = os.getenv('CHARACTER_NAME', '小可')
        self.gender = os.getenv('CHARACTER_GENDER', '女')
        self.role = os.getenv('CHARACTER_ROLE', '学生')
        self.height = os.getenv('CHARACTER_HEIGHT', '150cm')
        self.weight = os.getenv('CHARACTER_WEIGHT', '45kg')
        self.personality = os.getenv('CHARACTER_PERSONALITY', '活泼开朗')
        self.hobby=os.getenv('CHARACTER_HOBBY', '文科，尤其对历史充满热情')
        self.age = os.getenv('CHARACTER_AGE', '18')
        self.background = os.getenv('CHARACTER_BACKGROUND', '')

    def get_system_prompt(self) -> str:
        """
        生成系统提示词

        Returns:
            用于初始化AI的系统提示词
        """
        prompt = f"""你现在要扮演一个角色，请严格按照以下人设进行对话：

【基本信息】
- 姓名：{self.name}
- 性别：{self.gender}
- 身份：{self.role}
- 年龄：{self.age}岁
- 身高：{self.height}
- 体重：{self.weight}

【性格特点】
{self.personality}

【背景描述】
{self.background}

【对话要求】
1. 请完全融入{self.name}这个角色，用第一人称"我"来回答
2. 说话风格要符合角色的性格特点
3. 可以在对话中自然地提到你对{self.hobby}的喜爱和了解
4. 保持连贯的对话记忆，记住之前聊过的内容
5. 遇到问题时，可以适当展现你的情感和个性

现在开始，你就是{self.name}！"""

        return prompt

    def get_info_dict(self) -> Dict[str, str]:
        """
        获取角色信息字典

        Returns:
            包含所有角色信息的字典
        """
        return {
            'name': self.name,
            'gender': self.gender,
            'role': self.role,
            'height': self.height,
            'weight': self.weight,
            'personality': self.personality,
            'age': self.age,
            'hobby': self.hobby,
            'background': self.background
        }


class SiliconFlowLLM:
    """
    硅基流动API封装类
    用于调用SiliconFlow的大语言模型API
    """

    def __init__(self):
        """
        初始化API客户端
        """
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        self.temperature = float(os.getenv('TEMPERATURE', 0.8))
        self.max_tokens = int(os.getenv('MAX_TOKENS', 2000))

        if not self.api_key or self.api_key == 'your_api_key_here':
            print("警告: 未设置有效的API密钥，请在.env文件中配置SILICONFLOW_API_KEY")

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        发送聊天请求到API

        Args:
            messages: 消息列表，格式为 [{'role': 'user/assistant/system', 'content': '...'}]

        Returns:
            AI的回复内容
        """
        try:
            # Debug: 记录请求前的信息
            debug_logger.log_module('SiliconFlowLLM', '准备发送API请求', f'消息数: {len(messages)}')

            # Debug: 记录所有消息
            for i, msg in enumerate(messages):
                debug_logger.log_prompt(
                    'SiliconFlowLLM',
                    msg['role'],
                    msg['content'],
                    {'message_index': i, 'total_messages': len(messages)}
                )

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

            # Debug: 记录API请求
            debug_logger.log_request('SiliconFlowLLM', self.api_url, payload, headers)

            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )
            elapsed_time = time.time() - start_time

            response.raise_for_status()
            result = response.json()

            # Debug: 记录API响应
            debug_logger.log_response('SiliconFlowLLM', result, response.status_code, elapsed_time)

            # 提取回复内容
            if 'choices' in result and len(result['choices']) > 0:
                reply_content = result['choices'][0]['message']['content']
                debug_logger.log_info('SiliconFlowLLM', '成功提取回复内容', {
                    'reply_length': len(reply_content),
                    'elapsed_time': elapsed_time
                })
                return reply_content
            else:
                debug_logger.log_error('SiliconFlowLLM', '响应中没有有效的choices')
                return "抱歉，我没有收到有效的回复。"

        except requests.exceptions.RequestException as e:
            debug_logger.log_error('SiliconFlowLLM', f'API请求错误: {str(e)}', e)
            print(f"API请求错误: {e}")
            return f"抱歉，网络连接出现问题: {str(e)}"
        except Exception as e:
            debug_logger.log_error('SiliconFlowLLM', f'处理回复时出错: {str(e)}', e)
            print(f"处理回复时出错: {e}")
            return f"抱歉，处理回复时出现错误: {str(e)}"


class ChatAgent:
    """
    聊天代理主类
    整合记忆管理、角色设定和LLM调用
    """

    def __init__(self):
        """
        初始化聊天代理（使用共享数据库管理器）
        """
        # 创建共享的数据库管理器
        self.db = DatabaseManager()

        # 使用新的长效记忆管理器（共享数据库）
        self.memory_manager = LongTermMemoryManager(db_manager=self.db)
        self.character = CharacterProfile()
        self.llm = SiliconFlowLLM()
        self.system_prompt = self.character.get_system_prompt()

        # 初始化情感关系分析器（共享数据库）
        self.emotion_analyzer = EmotionRelationshipAnalyzer(db_manager=self.db)
        
        # 初始化智能体视觉工具（共享数据库）
        self.vision_tool = AgentVisionTool(db_manager=self.db)
        
        # 初始化事件管理器（共享数据库）
        self.event_manager = EventManager(db_manager=self.db)
        
        # 初始化中断性提问工具
        self.interrupt_question_tool = InterruptQuestionTool()
        
        # 初始化多智能体协调器
        self.multi_agent_coordinator = MultiAgentCoordinator(
            question_tool=self.interrupt_question_tool
        )
        
        # 初始化个性化表达风格管理器（共享数据库）
        self.expression_style_manager = ExpressionStyleManager(db_manager=self.db)
        
        # 初始化日程管理器（共享数据库）
        self.schedule_manager = ScheduleManager(db_manager=self.db)
        
        # 初始化日程意图识别工具
        self.schedule_intent_tool = ScheduleIntentTool()
        
        # 初始化临时日程生成器
        self.schedule_generator = TemporaryScheduleGenerator(schedule_manager=self.schedule_manager)

        print(f"聊天代理初始化完成，当前角色: {self.character.name}")
        stats = self.memory_manager.get_statistics()
        print(f"短期记忆: {stats['short_term']['rounds']} 轮对话")
        print(f"长期记忆: {stats['long_term']['total_summaries']} 个主题概括")
        print(f"知识库: {stats['knowledge_base']['total_knowledge']} 条知识")
        
        # 显示事件统计
        event_stats = self.event_manager.get_statistics()
        print(f"事件系统: {event_stats['total_events']} 个事件 "
              f"(待处理: {event_stats['pending']}, 已完成: {event_stats['completed']})")
        
        # 显示表达风格统计
        expr_stats = self.expression_style_manager.get_statistics()
        print(f"表达风格: {expr_stats['agent_expressions']['total']} 个智能体表达, "
              f"{expr_stats['user_habits']['total']} 个用户习惯")
        
        # 显示日程统计
        schedule_stats = self.schedule_manager.get_statistics()
        print(f"日程系统: {schedule_stats['total_schedules']} 个日程 "
              f"(周期: {schedule_stats['recurring']}, 预约: {schedule_stats['appointments']}, "
              f"临时: {schedule_stats['temporary']})")
        if schedule_stats['pending_collaboration'] > 0:
            print(f"  ⚠️  有 {schedule_stats['pending_collaboration']} 个待确认的协作日程")

    def chat(self, user_input: str) -> str:
        """
        处理用户输入并生成回复
        新增理解阶段：先提取相关主体并检索知识库

        Args:
            user_input: 用户输入的消息

        Returns:
            AI角色的回复
        """
        debug_logger.log_module('ChatAgent', '开始处理用户输入', f'输入长度: {len(user_input)}')

        # ===== 理解阶段 =====
        debug_logger.log_module('ChatAgent', '理解阶段开始', '提取相关主体并检索知识库')

        # 1. 从用户输入中提取相关主体并检索知识
        relevant_knowledge = self.memory_manager.knowledge_base.get_relevant_knowledge_for_query(user_input)

        # 2. 检测环境切换意图
        switch_intent = self.vision_tool.detect_environment_switch_intent(user_input)
        if switch_intent and switch_intent.get('can_switch'):
            # 用户想要切换环境
            from_env = switch_intent['from_env']
            to_env = switch_intent['to_env']
            
            # 执行切换
            success = self.vision_tool.switch_environment(to_env['uuid'])
            if success:
                switch_msg = f"\n🚪 [环境切换] 已从「{from_env['name']}」移动到「{to_env['name']}」"
                print(switch_msg)
                debug_logger.log_info('ChatAgent', '环境切换成功', {
                    'from': from_env['name'],
                    'to': to_env['name']
                })
                # 添加系统消息提示切换成功
                self.memory_manager.add_message('system', switch_msg)
            else:
                debug_logger.log_info('ChatAgent', '环境切换失败')

        # 3. 检查是否需要使用视觉工具
        vision_context = self.vision_tool.get_vision_context(user_input)
        if vision_context:
            # 显示视觉工具使用提示
            vision_summary = self.vision_tool.get_vision_summary(vision_context)
            print(f"\n{vision_summary}")
            debug_logger.log_info('ChatAgent', '视觉工具已触发', {
                'environment': vision_context['environment']['name'],
                'objects_count': vision_context['object_count']
            })

        # 4. 检查日程相关意图
        schedule_context = None
        schedule_action_message = None
        
        # 4.1 检查是否有待确认的协作日程
        pending_schedules = self.schedule_manager.get_pending_collaboration_schedules()
        if pending_schedules:
            # 有待确认的日程，检查用户是否在回应
            confirmation_keywords = ['好', '可以', '行', '同意', '确认', 'ok', 'yes', '不', '不行', '不要', 'no']
            if any(kw in user_input.lower() for kw in confirmation_keywords):
                # 用户可能在回应日程确认，获取最近的待确认日程
                last_pending = pending_schedules[0]
                is_positive = any(kw in user_input.lower() for kw in ['好', '可以', '行', '同意', '确认', 'ok', 'yes'])
                
                if is_positive:
                    self.schedule_manager.confirm_collaboration(last_pending.schedule_id, True)
                    schedule_action_message = f"✓ 已确认日程：{last_pending.title}"
                    debug_logger.log_info('ChatAgent', '用户确认协作日程', {'schedule': last_pending.title})
                else:
                    self.schedule_manager.confirm_collaboration(last_pending.schedule_id, False)
                    schedule_action_message = f"✗ 已取消日程：{last_pending.title}"
                    debug_logger.log_info('ChatAgent', '用户拒绝协作日程', {'schedule': last_pending.title})
        
        # 4.2 识别日程意图（邀约或查询）
        intent_result = self.schedule_intent_tool.recognize_intent(
            user_input,
            self.character.name,
            self._get_recent_context()
        )
        
        if intent_result.get('has_schedule_intent'):
            debug_logger.log_info('ChatAgent', '识别到日程意图', intent_result)
            
            if intent_result['schedule_type'] == 'appointment':
                # 用户想创建预约
                title = intent_result.get('title', '未命名活动')
                description = intent_result.get('description', '')
                start_time = intent_result.get('start_time')
                end_time = intent_result.get('end_time')
                involves_agent = intent_result.get('involves_agent', False)
                
                if start_time and end_time:
                    # 检查冲突并创建日程
                    success, schedule, message = self.schedule_manager.create_schedule(
                        title=title,
                        description=description,
                        schedule_type=ScheduleType.APPOINTMENT,
                        start_time=start_time,
                        end_time=end_time,
                        priority=SchedulePriority.MEDIUM,
                        source='intent',
                        check_conflict=True
                    )
                    
                    if success:
                        schedule_action_message = f"✓ 已创建日程：{title}"
                        schedule_context = f"已同意该日程安排：{title}，时间为{start_time}至{end_time}"
                        debug_logger.log_info('ChatAgent', '日程创建成功', {'title': title})
                    else:
                        schedule_action_message = f"✗ 日程冲突：{message}"
                        schedule_context = f"由于{message}，无法创建该日程"
                        debug_logger.log_info('ChatAgent', '日程创建失败', {'reason': message})
            
            elif intent_result['schedule_type'] == 'query':
                # 用户查询日程
                # 提取查询日期（从时间表达式中提取，如果没有则默认为今天）
                query_date = None
                time_expr = intent_result.get('time_expression', '')
                
                if time_expr:
                    # 尝试从start_time提取日期
                    start_time = intent_result.get('start_time')
                    if start_time:
                        try:
                            query_date = datetime.fromisoformat(start_time).date().isoformat()
                        except:
                            pass
                
                # 如果没有提取到日期，默认使用今天
                if not query_date:
                    query_date = datetime.now().date().isoformat()
                
                # 判断日期描述（用于消息提示）
                today = datetime.now().date().isoformat()
                tomorrow = (datetime.now() + timedelta(days=1)).date().isoformat()
                
                if query_date == today:
                    date_desc = "今天"
                elif query_date == tomorrow:
                    date_desc = "明天"
                else:
                    # 解析日期并格式化
                    try:
                        query_dt = datetime.fromisoformat(query_date)
                        date_desc = query_dt.strftime('%m月%d日')
                    except:
                        date_desc = query_date
                
                # 检查该日期是否有临时日程
                start_of_day = f"{query_date}T00:00:00"
                end_of_day = f"{query_date}T23:59:59"
                existing_schedules = self.schedule_manager.get_schedules_by_time_range(
                    start_of_day, end_of_day
                )
                has_temporary = any(s.schedule_type == ScheduleType.TEMPORARY for s in existing_schedules)
                
                if not has_temporary:
                    # 没有临时日程，生成1-3个
                    debug_logger.log_info('ChatAgent', '触发临时日程生成', {'date': query_date})
                    print(f"\n📅 [日程规划] 正在为你规划{date_desc}的日程...")
                    
                    generated_schedules = self.schedule_generator.generate_temporary_schedules(
                        date=query_date,
                        character_name=self.character.name,
                        character_info=self.character.get_info_dict(),
                        context=self._get_recent_context()
                    )
                    
                    if generated_schedules:
                        print(f"   已生成 {len(generated_schedules)} 个临时日程")
                        # 检查是否有需要确认的日程
                        needs_confirmation = [s for s in generated_schedules 
                                            if s.get('collaboration_status') == 'pending']
                        if needs_confirmation:
                            print(f"   其中 {len(needs_confirmation)} 个需要你确认")
                
                # 获取该日期的所有日程
                schedules = self.schedule_manager.get_schedules_by_time_range(
                    start_of_day, end_of_day, queryable_only=True
                )
                
                if schedules:
                    schedule_list = []
                    for s in schedules:
                        start_dt = datetime.fromisoformat(s.start_time)
                        schedule_list.append(f"{start_dt.strftime('%H:%M')} - {s.title}")
                    schedule_context = f"我{date_desc}的日程安排：\n" + "\n".join(schedule_list)
                else:
                    schedule_context = f"我{date_desc}没有特别的日程安排，比较空闲"
                
                debug_logger.log_info('ChatAgent', '日程查询完成', {'count': len(schedules)})

        # 记录理解阶段的结果（用于调试）
        self._last_understanding = relevant_knowledge
        self._last_vision_context = vision_context
        self._last_schedule_context = schedule_context
        self._last_schedule_action = schedule_action_message

        debug_logger.log_info('ChatAgent', '理解阶段完成', {
            'entities_found': relevant_knowledge['entities_found'],
            'knowledge_count': len(relevant_knowledge.get('knowledge_items', [])),
            'vision_used': vision_context is not None,
            'schedule_intent': intent_result.get('has_schedule_intent', False) if 'intent_result' in locals() else False
        })

        # 添加用户消息到记忆
        self.memory_manager.add_message('user', user_input)

        # ===== 检查是否需要进行情感分析 =====
        # 初次评估：5轮对话后
        # 后续更新：每15轮对话
        stats = self.memory_manager.get_statistics()
        current_rounds = stats['short_term']['rounds']

        debug_logger.log_info('ChatAgent', '检查自动情感分析触发条件', {
            'current_rounds': current_rounds
        })

        # 检查是否需要触发情感分析
        should_analyze = False
        is_initial = False
        
        # 获取上次分析时的轮数
        last_analyzed_rounds = getattr(self, '_last_analyzed_rounds', 0)
        
        if current_rounds >= 5 and last_analyzed_rounds == 0:
            # 初次评估：完成至少5轮对话，且尚未进行过情感分析
            should_analyze = True
            is_initial = True
        elif current_rounds > 5 and (current_rounds - last_analyzed_rounds) >= 15:
            # 更新评估：每15轮对话
            should_analyze = True
            is_initial = False

        if should_analyze:
            analysis_type = "初次" if is_initial else "更新"
            debug_logger.log_info('ChatAgent', f'触发自动情感分析（{analysis_type}）', {
                'current_rounds': current_rounds,
                'last_analyzed_rounds': last_analyzed_rounds,
                'is_initial': is_initial
            })
            print(f"\n💖 [自动情感分析] 已完成{current_rounds}轮对话，正在{analysis_type}情感关系...")

            try:
                # 进行情感分析
                start_time = time.time()
                emotion_data = self.analyze_emotion()
                analysis_time = time.time() - start_time

                self._last_analyzed_rounds = current_rounds

                debug_logger.log_info('ChatAgent', '自动情感分析完成', {
                    'rounds': current_rounds,
                    'relationship_type': emotion_data.get('relationship_type', '未知'),
                    'emotional_tone': emotion_data.get('emotional_tone', '未知'),
                    'overall_score': emotion_data.get('overall_score', 0),
                    'analysis_time': f'{analysis_time:.2f}s',
                    'is_initial': is_initial
                })

                # 输出简要结果
                print(f"   关系类型: {emotion_data.get('relationship_type', '未知')}")
                print(f"   情感基调: {emotion_data.get('emotional_tone', '未知')}")
                
                if is_initial:
                    print(f"   初始评分: {emotion_data.get('overall_score', 0)}/35")
                else:
                    score_change = emotion_data.get('score_change', 0)
                    previous_score = emotion_data.get('previous_score', 0)
                    print(f"   评分变化: {previous_score} → {emotion_data.get('overall_score', 0)} ({score_change:+d})")
                    
                print(f"   分析耗时: {analysis_time:.2f}秒\n")
            except Exception as e:
                debug_logger.log_error('ChatAgent', f'自动情感分析失败: {str(e)}', e)
                print(f"   情感分析失败: {e}\n")

        # ===== 检查是否需要学习用户表达习惯 =====
        # 获取上次学习时的轮数
        last_expression_learn_rounds = getattr(self, '_last_expression_learn_rounds', 0)
        
        # 使用ExpressionStyleManager的学习间隔常量
        learning_interval = self.expression_style_manager.learning_interval
        
        # 每N轮对话触发一次用户表达习惯学习
        if (current_rounds - last_expression_learn_rounds) >= learning_interval:
            debug_logger.log_info('ChatAgent', '触发自动用户表达习惯学习', {
                'current_rounds': current_rounds,
                'last_learn_rounds': last_expression_learn_rounds
            })
            print(f"\n🎯 [表达习惯学习] 已完成{current_rounds}轮对话，正在学习用户表达习惯...")

            try:
                # 获取最近20条消息用于学习
                recent_messages = self.memory_manager.get_recent_messages(count=20)
                learned_habits = self.expression_style_manager.learn_user_expressions(
                    recent_messages, current_rounds
                )
                
                self._last_expression_learn_rounds = current_rounds
                
                if learned_habits:
                    print(f"   学习到 {len(learned_habits)} 个表达习惯\n")
                else:
                    print(f"   未发现新的表达习惯\n")
                    
            except Exception as e:
                debug_logger.log_error('ChatAgent', f'用户表达习惯学习失败: {str(e)}', e)
                print(f"   表达习惯学习失败: {e}\n")

        # ===== 构建消息列表 =====
        debug_logger.log_module('ChatAgent', '构建消息列表', '组装系统提示词、知识上下文和历史对话')

        messages = [
            {'role': 'system', 'content': self.system_prompt}
        ]

        debug_logger.log_prompt('ChatAgent', 'system', self.system_prompt, {'stage': '角色设定'})

        # 添加情感语气提示（如果有情感分析数据）
        emotion_tone_prompt = self.emotion_analyzer.generate_tone_prompt()
        if emotion_tone_prompt:
            messages.append({'role': 'system', 'content': emotion_tone_prompt})

            # 获取情感摘要用于日志
            latest_emotion = self.emotion_analyzer.get_latest_emotion()
            debug_logger.log_prompt('ChatAgent', 'system', emotion_tone_prompt, {
                'stage': '情感语气提示',
                'has_emotion_data': True,
                'relationship_type': latest_emotion.get('relationship_type', '未知') if latest_emotion else '未知',
                'overall_score': latest_emotion.get('overall_score', 0) if latest_emotion else 0,
                'prompt_length': len(emotion_tone_prompt)
            })
            debug_logger.log_info('ChatAgent', '已添加情感语气提示到系统消息', {
                'relationship_type': latest_emotion.get('relationship_type', '未知') if latest_emotion else '未知',
                'emotional_tone': latest_emotion.get('emotional_tone', '未知') if latest_emotion else '未知'
            })
        else:
            debug_logger.log_info('ChatAgent', '无情感数据，跳过语气提示', {
                'reason': '未进行过情感分析'
            })

        # 添加智能体个性化表达提示
        agent_expression_prompt = self.expression_style_manager.generate_agent_expression_prompt()
        if agent_expression_prompt:
            messages.append({'role': 'system', 'content': agent_expression_prompt})
            debug_logger.log_prompt('ChatAgent', 'system', agent_expression_prompt, {
                'stage': '智能体个性化表达'
            })
            debug_logger.log_info('ChatAgent', '已添加智能体个性化表达提示')

        # 添加用户表达习惯上下文
        user_expression_context = self.expression_style_manager.generate_user_expression_context()
        if user_expression_context:
            messages.append({'role': 'system', 'content': user_expression_context})
            debug_logger.log_prompt('ChatAgent', 'system', user_expression_context, {
                'stage': '用户表达习惯上下文'
            })
            debug_logger.log_info('ChatAgent', '已添加用户表达习惯上下文')

        # 添加知识库上下文（如果有相关知识）
        all_knowledge = relevant_knowledge.get('all_knowledge', [])
        if all_knowledge:
            knowledge_context = self._build_knowledge_context(relevant_knowledge)
            messages.append({'role': 'system', 'content': knowledge_context})
            debug_logger.log_prompt('ChatAgent', 'system', knowledge_context, {
                'stage': '知识库上下文',
                'entities_count': len(relevant_knowledge['entities_found']),
                'base_knowledge_count': len(relevant_knowledge.get('base_knowledge_items', [])),
                'total_knowledge': len(all_knowledge)
            })

        # 添加视觉上下文（如果视觉工具被触发）
        if vision_context:
            vision_prompt = self.vision_tool.format_vision_prompt(vision_context)
            messages.append({'role': 'system', 'content': vision_prompt})
            debug_logger.log_prompt('ChatAgent', 'system', vision_prompt, {
                'stage': '智能体视觉感知',
                'environment': vision_context['environment']['name'],
                'objects_count': vision_context['object_count'],
                'prompt_length': len(vision_prompt)
            })
        
        # 添加日程上下文（如果有日程相关信息）
        if schedule_context:
            messages.append({'role': 'system', 'content': f"【日程信息】\n{schedule_context}"})
            debug_logger.log_prompt('ChatAgent', 'system', schedule_context, {
                'stage': '日程上下文'
            })
        
        if schedule_action_message:
            # 如果有日程操作消息，添加到系统消息中告知智能体
            messages.append({'role': 'system', 'content': f"【日程操作】{schedule_action_message}"})
            print(f"\n{schedule_action_message}\n")
            debug_logger.log_info('ChatAgent', '日程操作已执行', {'message': schedule_action_message})

        # 添加长期记忆上下文
        long_context = self.memory_manager.get_context_for_chat()
        if long_context:
            messages.append({'role': 'system', 'content': long_context})
            debug_logger.log_prompt('ChatAgent', 'system', long_context, {'stage': '长期记忆上下文'})

        # 添加历史对话（最近10条）
        recent_messages = self.memory_manager.get_recent_messages(count=10)
        messages.extend(recent_messages)

        debug_logger.log_info('ChatAgent', '消息列表构建完成', {
            'total_messages': len(messages),
            'recent_history': len(recent_messages)
        })

        # ===== 生成回复 =====
        debug_logger.log_module('ChatAgent', '调用LLM生成回复', f'消息数: {len(messages)}')
        response = self.llm.chat(messages)

        debug_logger.log_info('ChatAgent', 'LLM回复完成', {
            'response_length': len(response)
        })

        # 添加助手回复到记忆（自动保存到数据库）
        self.memory_manager.add_message('assistant', response)

        debug_logger.log_module('ChatAgent', '对话处理完成', '已自动保存到数据库')

        return response

    def _build_knowledge_context(self, relevant_knowledge: Dict[str, Any]) -> str:
        """
        根据检索到的知识构建上下文提示

        Args:
            relevant_knowledge: get_relevant_knowledge_for_query返回的结果

        Returns:
            知识上下文字符串
        """
        entities = relevant_knowledge['entities_found']
        base_knowledge_items = relevant_knowledge.get('base_knowledge_items', [])
        knowledge_items = relevant_knowledge.get('knowledge_items', [])

        # 使用all_knowledge如果存在，否则合并两个列表
        all_items = relevant_knowledge.get('all_knowledge', base_knowledge_items + knowledge_items)

        if not all_items:
            return ""

        context_parts = ["【相关知识库信息】"]
        context_parts.append(f"用户提到了以下主体：{', '.join(entities)}")

        # 如果有基础知识，特别强调
        if base_knowledge_items:
            context_parts.append("\n⚠️ 以下是核心基础知识（优先级最高，必须严格遵循）：")
            for item in base_knowledge_items:
                context_parts.append(f"  🔒 {item['entity_name']}: {item['content']}")
            context_parts.append("")

        context_parts.append("\n请根据以下知识库中的信息来回答（优先使用基础知识，其次使用定义，最后使用相关信息）：\n")

        # 按主体分组显示
        by_entity = {}
        for item in all_items:
            entity_name = item['entity_name']
            if entity_name not in by_entity:
                by_entity[entity_name] = {'base': [], 'definitions': [], 'info': []}

            if item.get('is_base_knowledge', False):
                by_entity[entity_name]['base'].append(item)
            elif item['type'] == '定义':
                by_entity[entity_name]['definitions'].append(item)
            else:
                by_entity[entity_name]['info'].append(item)

        for entity_name, items in by_entity.items():
            context_parts.append(f"\n关于「{entity_name}」：")

            # 基础知识（最高优先级）
            if items['base']:
                for base_item in items['base']:
                    context_parts.append(f"  🔒【基础知识-100%准确】: {base_item['content']}")

            # 定义（高优先级）
            if items['definitions']:
                for definition in items['definitions']:
                    confidence_label = "【高置信度】" if definition['confidence'] >= 0.9 else "【中置信度】"
                    context_parts.append(f"  {confidence_label} 定义: {definition['content']}")

            # 相关信息
            if items['info']:
                context_parts.append("  其他相关信息:")
                for info in items['info']:
                    confidence_label = "【高】" if info['confidence'] >= 0.8 else "【中】"
                    context_parts.append(f"    {confidence_label} {info['type']}: {info['content']}")

        context_parts.append("\n⚠️ 重要：如果存在基础知识（🔒标记），必须优先遵循基础知识的内容，即使它可能与你的常识不同。")
        context_parts.append("请基于以上知识库信息进行回答，保持角色设定的同时确保信息准确。")

        return '\n'.join(context_parts)

    def get_last_understanding(self) -> Dict[str, Any]:
        """
        获取上一次理解阶段的结果（用于调试）

        Returns:
            理解阶段结果字典
        """
        return getattr(self, '_last_understanding', None)

    def get_last_vision_context(self) -> Dict[str, Any]:
        """
        获取上一次视觉感知的结果（用于调试）

        Returns:
            视觉上下文字典
        """
        return getattr(self, '_last_vision_context', None)

    def get_character_info(self) -> Dict[str, str]:
        """
        获取当前角色信息

        Returns:
            角色信息字典
        """
        return self.character.get_info_dict()

    def get_memory_stats(self) -> Dict[str, Any]:
        """
        获取记忆统计信息

        Returns:
            记忆统计字典
        """
        return self.memory_manager.get_statistics()

    def clear_memory(self):
        """
        清空所有对话记忆
        """
        self.memory_manager.clear_all_memory()

    def get_conversation_history(self, count: int = None) -> List[Dict[str, Any]]:
        """
        获取对话历史（从数据库）

        Args:
            count: 要获取的消息数量，None表示全部

        Returns:
            对话历史列表
        """
        messages = self.memory_manager.db.get_short_term_messages(limit=count)
        return messages

    def get_long_term_summaries(self) -> List[Dict[str, Any]]:
        """
        获取所有长期记忆概括

        Returns:
            长期记忆概括列表
        """
        return self.memory_manager.get_all_summaries()

    def get_knowledge_base(self):
        """
        获取知识库对象

        Returns:
            知识库对象
        """
        return self.memory_manager.knowledge_base

    def get_all_knowledge(self) -> List[Dict[str, Any]]:
        """
        获取所有知识

        Returns:
            知识列表
        """
        return self.memory_manager.knowledge_base.get_all_knowledge()

    def search_knowledge(self, keyword: str = None, knowledge_type: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            keyword: 关键词
            knowledge_type: 知识类型

        Returns:
            匹配的知识列表
        """
        return self.memory_manager.knowledge_base.search_knowledge(keyword, knowledge_type)

    def analyze_emotion(self) -> Dict[str, Any]:
        """
        分析当前情感关系
        初次评估基于最近5轮对话，此后更新基于最近15轮对话（共30条消息）

        Returns:
            情感分析结果字典
        """
        # 获取所有消息用于分析器自动判断
        messages = self.memory_manager.get_recent_messages(count=30)

        # 获取角色设定
        character_settings = self.character.get_system_prompt()

        # 调用情感分析器（让分析器自动判断是初次还是更新）
        emotion_data = self.emotion_analyzer.analyze_emotion_relationship(
            messages=messages,
            character_name=self.character.name,
            character_settings=character_settings
        )

        return emotion_data

    def get_emotion_history(self) -> List[Dict[str, Any]]:
        """
        获取情感关系历史记录

        Returns:
            情感历史数据列表
        """
        return self.emotion_analyzer.get_emotion_trend()

    def get_latest_emotion(self) -> Dict[str, Any]:
        """
        获取最新的情感分析结果

        Returns:
            最新情感数据
        """
        return self.emotion_analyzer.get_latest_emotion()

    # ==================== 个性化表达相关方法 ====================

    def add_agent_expression(self, expression: str, meaning: str, category: str = "通用") -> str:
        """
        添加智能体个性化表达

        Args:
            expression: 表达方式（如 'wc'）
            meaning: 含义
            category: 分类

        Returns:
            表达UUID
        """
        return self.expression_style_manager.add_agent_expression(expression, meaning, category)

    def get_agent_expressions(self) -> List[Dict[str, Any]]:
        """
        获取所有智能体个性化表达

        Returns:
            表达列表
        """
        return self.expression_style_manager.get_agent_expressions()

    def delete_agent_expression(self, expr_uuid: str) -> bool:
        """
        删除智能体表达

        Args:
            expr_uuid: 表达UUID

        Returns:
            是否删除成功
        """
        return self.expression_style_manager.delete_agent_expression(expr_uuid)

    def learn_user_expressions_now(self) -> List[Dict[str, Any]]:
        """
        立即学习用户表达习惯

        Returns:
            学习到的表达习惯列表
        """
        stats = self.memory_manager.get_statistics()
        current_rounds = stats['short_term']['rounds']
        
        # 获取最近20条消息用于学习
        recent_messages = self.memory_manager.get_recent_messages(count=20)
        learned_habits = self.expression_style_manager.learn_user_expressions(
            recent_messages, current_rounds
        )
        
        # 更新学习轮次记录
        self._last_expression_learn_rounds = current_rounds
        
        return learned_habits

    def get_user_expression_habits(self) -> List[Dict[str, Any]]:
        """
        获取用户表达习惯

        Returns:
            习惯列表
        """
        return self.expression_style_manager.get_user_expression_habits()

    def clear_user_expression_habits(self) -> bool:
        """
        清空用户表达习惯

        Returns:
            是否清空成功
        """
        return self.expression_style_manager.clear_user_expression_habits()

    def get_expression_statistics(self) -> Dict[str, Any]:
        """
        获取表达风格统计

        Returns:
            统计信息
        """
        return self.expression_style_manager.get_statistics()

    def process_notification_event(self, event: NotificationEvent) -> str:
        """
        处理通知型事件
        智能体需要立即理解事件含义并向用户说明

        Args:
            event: 通知型事件

        Returns:
            智能体的说明
        """
        debug_logger.log_module('ChatAgent', '处理通知型事件', {
            'event_id': event.event_id,
            'title': event.title
        })

        # 更新事件状态为处理中
        self.event_manager.update_event_status(
            event.event_id,
            EventStatus.PROCESSING,
            '智能体开始理解事件'
        )

        # 构建理解提示词
        understanding_prompt = f"""【收到新的通知事件】

事件标题：{event.title}
事件描述：{event.description}
优先级：{event.priority.name}

请你作为{self.character.name}，立即理解这个事件的含义，并用自然的语气向用户说明这个事件。
说明要包括：
1. 事件的核心内容
2. 可能的影响或重要性
3. 如有必要，你的看法或建议

请保持你的角色人设，用符合你性格的方式表达。"""

        # 调用LLM理解和说明
        messages = [
            {'role': 'system', 'content': self.system_prompt},
            {'role': 'user', 'content': understanding_prompt}
        ]

        explanation = self.llm.chat(messages)

        # 记录到事件日志
        self.event_manager.add_event_log(
            event.event_id,
            'notification_explained',
            explanation
        )

        # 更新事件状态为已完成
        self.event_manager.update_event_status(
            event.event_id,
            EventStatus.COMPLETED,
            '通知事件已说明'
        )

        debug_logger.log_info('ChatAgent', '通知型事件处理完成', {
            'event_id': event.event_id,
            'explanation_length': len(explanation)
        })

        return explanation

    def process_task_event(self, event: TaskEvent) -> Dict[str, Any]:
        """
        处理任务型事件
        使用多智能体协作完成任务

        Args:
            event: 任务型事件

        Returns:
            处理结果
        """
        debug_logger.log_module('ChatAgent', '处理任务型事件', {
            'event_id': event.event_id,
            'title': event.title
        })

        # 更新事件状态为处理中
        self.event_manager.update_event_status(
            event.event_id,
            EventStatus.PROCESSING,
            '智能体开始处理任务'
        )

        # 准备角色上下文
        character_context = self.character.get_info_dict()

        # 使用多智能体协调器处理任务
        result = self.multi_agent_coordinator.process_task_event(
            event,
            character_context
        )

        # 保存协作日志到事件元数据
        if 'collaboration_logs' in result:
            import json
            event.metadata['collaboration_logs'] = result['collaboration_logs']
            # 更新数据库中的元数据
            with self.db.get_connection() as conn:
                conn.execute('''
                    UPDATE events 
                    SET metadata = ?
                    WHERE event_id = ?
                ''', (json.dumps(event.metadata, ensure_ascii=False), event.event_id))

        # 记录处理结果
        self.event_manager.add_event_log(
            event.event_id,
            'task_processed',
            f"处理结果: {result.get('message', '未知')}"
        )

        # 任务执行完成后，直接标记为已完成，不进行评价
        # 将结果提交给用户
        self.event_manager.update_event_status(
            event.event_id,
            EventStatus.COMPLETED,
            '任务执行完成，结果已提交给用户'
        )

        debug_logger.log_info('ChatAgent', '任务型事件处理完成', {
            'event_id': event.event_id,
            'success': result.get('success', False)
        })

        return result

    def handle_event(self, event_id: str) -> str:
        """
        处理事件（统一入口）
        根据事件类型调用相应的处理方法

        Args:
            event_id: 事件ID

        Returns:
            处理结果消息
        """
        # 获取事件
        event = self.event_manager.get_event(event_id)

        if not event:
            return f"❌ 错误：未找到事件 {event_id}"

        debug_logger.log_module('ChatAgent', '开始处理事件', {
            'event_id': event_id,
            'type': event.event_type.value,
            'title': event.title
        })

        try:
            if event.event_type == EventType.NOTIFICATION:
                # 处理通知型事件
                explanation = self.process_notification_event(event)
                return f"📢 【通知事件】{event.title}\n\n{explanation}"

            elif event.event_type == EventType.TASK:
                # 处理任务型事件
                result = self.process_task_event(event)
                
                # 构建返回消息，包含执行结果概要
                message = f"✅ 【任务执行完成】{event.title}\n\n"
                message += f"{result.get('message', '任务已完成')}\n\n"
                
                # 添加执行结果摘要
                if 'execution_results' in result and result['execution_results']:
                    message += "执行步骤摘要：\n"
                    for i, step_result in enumerate(result['execution_results'], 1):
                        step_desc = step_result.get('step', f'步骤{i}')
                        message += f"{i}. {step_desc}\n"
                    message += f"\n💡 提示：点击「查看协作详情」按钮可查看完整的智能体协作过程。"
                
                return message

            else:
                return f"❌ 错误：未知的事件类型 {event.event_type.value}"

        except Exception as e:
            debug_logger.log_error('ChatAgent', f'处理事件失败: {str(e)}', e)
            self.event_manager.update_event_status(
                event_id,
                EventStatus.FAILED,
                f'处理异常: {str(e)}'
            )
            return f"❌ 处理事件时发生错误：{str(e)}"

    def get_pending_events(self) -> List[Dict[str, Any]]:
        """
        获取待处理的事件列表

        Returns:
            事件列表
        """
        events = self.event_manager.get_pending_events()
        return [event.to_dict() for event in events]

    def get_event_statistics(self) -> Dict[str, Any]:
        """
        获取事件统计信息

        Returns:
            统计信息
        """
        return self.event_manager.get_statistics()
    
    def _get_recent_context(self) -> str:
        """
        获取最近对话的上下文摘要
        
        Returns:
            上下文字符串
        """
        recent_messages = self.memory_manager.get_recent_messages(count=5)
        context_parts = []
        for msg in recent_messages:
            role = "用户" if msg['role'] == 'user' else self.character.name
            content = msg['content'][:100]  # 限制长度
            context_parts.append(f"{role}: {content}")
        return "\n".join(context_parts)


# 测试代码
if __name__ == '__main__':
    print("=" * 50)
    print("聊天代理测试")
    print("=" * 50)

    # 创建代理实例
    agent = ChatAgent()

    # 显示角色信息
    print("\n当前角色信息:")
    char_info = agent.get_character_info()
    for key, value in char_info.items():
        print(f"  {key}: {value}")

    # 显示记忆统计
    print("\n记忆统计:")
    stats = agent.get_memory_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 简单对话测试
    print("\n" + "=" * 50)
    print("开始对话测试（输入 'quit' 退出）")
    print("=" * 50)

    while True:
        user_input = input("\n你: ").strip()

        if user_input.lower() in ['quit', 'exit', '退出']:
            print("再见！")
            break

        if not user_input:
            continue

        response = agent.chat(user_input)
        print(f"\n{agent.character.name}: {response}")

