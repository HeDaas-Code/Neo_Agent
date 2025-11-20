"""
多智能体协作模块
实现任务型事件的多智能体协作处理
"""

import os
import time
import json
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
import requests
from event_manager import TaskEvent
from interrupt_question_tool import InterruptQuestionTool
from debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class SubAgent:
    """
    子智能体类
    代表参与协作的单个智能体
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        description: str,
        api_key: str,
        api_url: str,
        model_name: str
    ):
        """
        初始化子智能体

        Args:
            agent_id: 智能体ID
            role: 智能体角色
            description: 角色描述
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        self.agent_id = agent_id
        self.role = role
        self.description = description
        self.api_key = api_key
        self.api_url = api_url
        self.model_name = model_name

    def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any],
        tools: List[Dict[str, Any]] = None
    ) -> str:
        """
        执行任务

        Args:
            task_description: 任务描述
            context: 上下文信息
            tools: 可用工具列表

        Returns:
            执行结果
        """
        debug_logger.log_module('SubAgent', f'智能体[{self.role}]开始执行任务', {
            'agent_id': self.agent_id,
            'task_length': len(task_description)
        })

        # 构建系统提示词
        system_prompt = f"""你是一个{self.role}。

你的职责：{self.description}

当前任务：{task_description}

上下文信息：
{json.dumps(context, ensure_ascii=False, indent=2)}
"""

        # 如果有可用工具，添加工具说明
        if tools:
            tools_description = "\n\n可用工具：\n"
            for tool in tools:
                tools_description += f"- {tool['name']}: {tool['description']}\n"
            system_prompt += tools_description

        system_prompt += """

请按照任务要求完成你的工作，如有需要可以使用可用的工具。
输出格式：直接输出你的工作结果，简洁明了。"""

        # 调用API
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': f'请完成任务：{task_description}'}
                ],
                'temperature': 0.7,
                'max_tokens': 2000,
                'stream': False
            }

            debug_logger.log_request('SubAgent', self.api_url, payload, headers)

            start_time = time.time()
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            elapsed_time = time.time() - start_time

            response.raise_for_status()
            result = response.json()

            debug_logger.log_response('SubAgent', result, response.status_code, elapsed_time)

            if 'choices' in result and len(result['choices']) > 0:
                output = result['choices'][0]['message']['content']
                debug_logger.log_info('SubAgent', f'智能体[{self.role}]任务完成', {
                    'output_length': len(output),
                    'elapsed_time': elapsed_time
                })
                return output
            else:
                return "【执行失败】未收到有效响应"

        except Exception as e:
            debug_logger.log_error('SubAgent', f'智能体[{self.role}]执行失败: {str(e)}', e)
            return f"【执行失败】{str(e)}"


class MultiAgentCoordinator:
    """
    多智能体协调器
    负责协调多个智能体完成复杂任务
    """

    def __init__(
        self,
        question_tool: InterruptQuestionTool,
        progress_callback: Optional[Callable[[str], None]] = None
    ):
        """
        初始化多智能体协调器

        Args:
            question_tool: 中断性提问工具
            progress_callback: 进度回调函数
        """
        self.question_tool = question_tool
        self.progress_callback = progress_callback
        
        # 从环境变量获取API配置
        self.api_key = os.getenv('SILICONFLOW_API_KEY')
        self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        
        debug_logger.log_module('MultiAgentCoordinator', '多智能体协调器初始化完成')

    def emit_progress(self, message: str):
        """
        输出进度提示（旁白式）

        Args:
            message: 进度消息
        """
        # 格式化为旁白式输出
        narration = f"📢 {message}"
        
        print(narration)
        
        if self.progress_callback:
            self.progress_callback(narration)
        
        debug_logger.log_info('MultiAgentCoordinator', '进度更新', {
            'message': message
        })

    def process_task_event(
        self,
        task_event: TaskEvent,
        character_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理任务型事件

        Args:
            task_event: 任务事件
            character_context: 角色上下文信息

        Returns:
            处理结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '开始处理任务型事件', {
            'event_id': task_event.event_id,
            'title': task_event.title
        })

        self.emit_progress(f"智能体开始分析任务「{task_event.title}」...")

        # 第一步：理解任务
        task_understanding = self._understand_task(task_event, character_context)
        
        if not task_understanding.get('success'):
            return {
                'success': False,
                'error': task_understanding.get('error', '任务理解失败')
            }

        self.emit_progress(f"任务已理解：{task_understanding['summary']}")

        # 第二步：制定计划
        self.emit_progress("智能体正在制定执行计划...")
        execution_plan = self._create_execution_plan(task_event, task_understanding)
        
        self.emit_progress(f"执行计划已制定，共{len(execution_plan['steps'])}个步骤")

        # 第三步：执行计划
        execution_results = []
        for i, step in enumerate(execution_plan['steps'], 1):
            self.emit_progress(f"正在执行步骤 {i}/{len(execution_plan['steps'])}: {step['description']}")
            
            result = self._execute_step(step, task_event, character_context, execution_results)
            execution_results.append(result)
            
            if result.get('needs_user_input'):
                # 需要用户输入
                answer = self.question_tool.ask_user(
                    result['question'],
                    result.get('context', '')
                )
                result['user_answer'] = answer
                self.emit_progress(f"用户已回答问题，继续执行...")

            if not result.get('success'):
                self.emit_progress(f"步骤执行失败：{result.get('error', '未知错误')}")
                return {
                    'success': False,
                    'error': f'执行失败于步骤{i}',
                    'execution_results': execution_results
                }

            self.emit_progress(f"步骤 {i} 完成")

        # 第四步：验证任务完成
        self.emit_progress("所有步骤已完成，正在验证任务结果...")
        
        verification_result = self._verify_task_completion(
            task_event,
            execution_results
        )

        if verification_result['is_completed']:
            self.emit_progress(f"✅ 任务验证通过！{verification_result['message']}")
            return {
                'success': True,
                'message': '任务已成功完成',
                'execution_results': execution_results,
                'verification': verification_result
            }
        else:
            self.emit_progress(f"⚠️ 任务验证未通过：{verification_result['message']}")
            return {
                'success': False,
                'error': '任务未达到完成标准',
                'execution_results': execution_results,
                'verification': verification_result
            }

    def _understand_task(
        self,
        task_event: TaskEvent,
        character_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        理解任务要求

        Args:
            task_event: 任务事件
            character_context: 角色上下文

        Returns:
            理解结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '开始理解任务')

        # 创建理解智能体
        understanding_agent = SubAgent(
            agent_id='understanding_agent',
            role='任务分析专家',
            description='负责理解和分析任务需求',
            api_key=self.api_key,
            api_url=self.api_url,
            model_name=self.model_name
        )

        task_description = f"""
任务标题：{task_event.title}
任务描述：{task_event.description}
任务要求：{task_event.metadata.get('task_requirements', '')}
完成标准：{task_event.metadata.get('completion_criteria', '')}
"""

        context = {
            'character': character_context,
            'task_id': task_event.event_id
        }

        result = understanding_agent.execute_task(
            '请分析这个任务，总结任务的核心目标、关键要求和预期成果。用简洁的语言概括。',
            context
        )

        return {
            'success': True,
            'summary': result,
            'raw_task': task_description
        }

    def _create_execution_plan(
        self,
        task_event: TaskEvent,
        task_understanding: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        制定执行计划

        Args:
            task_event: 任务事件
            task_understanding: 任务理解结果

        Returns:
            执行计划
        """
        debug_logger.log_module('MultiAgentCoordinator', '开始制定执行计划')

        # 创建规划智能体
        planning_agent = SubAgent(
            agent_id='planning_agent',
            role='任务规划专家',
            description='负责将复杂任务分解为可执行的步骤',
            api_key=self.api_key,
            api_url=self.api_url,
            model_name=self.model_name
        )

        context = {
            'task_understanding': task_understanding['summary'],
            'task_requirements': task_event.metadata.get('task_requirements', ''),
            'completion_criteria': task_event.metadata.get('completion_criteria', '')
        }

        plan_text = planning_agent.execute_task(
            '请将这个任务分解为3-5个具体可执行的步骤。每个步骤用一行描述，格式为：步骤N：具体要做的事情',
            context
        )

        # 解析计划文本为步骤列表
        steps = []
        lines = plan_text.strip().split('\n')
        for line in lines:
            line = line.strip()
            if line and ('步骤' in line or line[0].isdigit()):
                # 去除步骤编号，只保留描述
                if '：' in line:
                    description = line.split('：', 1)[1].strip()
                elif ':' in line:
                    description = line.split(':', 1)[1].strip()
                else:
                    description = line
                
                if description:  # 确保描述不为空
                    steps.append({
                        'description': description,
                        'status': 'pending'
                    })

        # 验证至少有一个步骤
        if not steps:
            debug_logger.log_module('MultiAgentCoordinator', '警告：未能从计划中解析出有效步骤', {
                'plan_text': plan_text
            })
            # 创建一个默认步骤
            steps.append({
                'description': '完成任务要求',
                'status': 'pending'
            })

        return {
            'steps': steps,
            'plan_text': plan_text
        }

    def _execute_step(
        self,
        step: Dict[str, Any],
        task_event: TaskEvent,
        character_context: Dict[str, Any],
        previous_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        执行单个步骤

        Args:
            step: 步骤信息
            task_event: 任务事件
            character_context: 角色上下文
            previous_results: 之前步骤的结果

        Returns:
            执行结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '执行步骤', {
            'step': step['description']
        })

        # 创建执行智能体
        execution_agent = SubAgent(
            agent_id=f'execution_agent_{len(previous_results)}',
            role='任务执行专家',
            description='负责执行具体的任务步骤',
            api_key=self.api_key,
            api_url=self.api_url,
            model_name=self.model_name
        )

        # 准备工具列表（包含中断性提问工具）
        tools = [self.question_tool.create_tool_description()]

        context = {
            'character': character_context,
            'task': {
                'title': task_event.title,
                'description': task_event.description
            },
            'previous_results': [r.get('output', '') for r in previous_results]
        }

        result_text = execution_agent.execute_task(
            step['description'],
            context,
            tools
        )

        # 检查是否需要用户输入
        # 改进的检测逻辑：检查问号是否在句尾，以及更具体的关键词
        needs_input = False
        if isinstance(result_text, str):
            # 检查句尾问号
            if result_text.strip().endswith('？') or result_text.strip().endswith('?'):
                needs_input = True
            # 检查特定的提问模式
            elif any(keyword in result_text for keyword in ['需要确认', '请问', '请提供', '请输入', '是否需要']):
                needs_input = True

        return {
            'success': True,
            'step': step['description'],
            'output': result_text,
            'needs_user_input': needs_input,
            'question': result_text if needs_input else None,
            'context': step['description'] if needs_input else None
        }

    def _verify_task_completion(
        self,
        task_event: TaskEvent,
        execution_results: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        验证任务是否完成

        Args:
            task_event: 任务事件
            execution_results: 执行结果列表

        Returns:
            验证结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '开始验证任务完成情况')

        # 创建验证智能体
        verification_agent = SubAgent(
            agent_id='verification_agent',
            role='任务验证专家',
            description='负责验证任务是否达到完成标准',
            api_key=self.api_key,
            api_url=self.api_url,
            model_name=self.model_name
        )

        # 整理执行结果
        results_summary = '\n'.join([
            f"步骤{i+1}：{r['step']}\n结果：{r['output']}"
            for i, r in enumerate(execution_results)
        ])

        context = {
            'task_title': task_event.title,
            'task_description': task_event.description,
            'completion_criteria': task_event.metadata.get('completion_criteria', ''),
            'execution_results': results_summary
        }

        verification_text = verification_agent.execute_task(
            '请根据任务的完成标准，判断执行结果是否达标。请以如下JSON格式回答：{"is_completed": true/false, "reason": "原因说明"}。如果无法判断，请合理说明。',
            context
        )

        # 尝试解析JSON格式的回复
        is_completed = False
        reason = verification_text
        try:
            # 尝试提取JSON部分（可能包含在其他文本中）
            import re
            json_match = re.search(r'\{[^}]*"is_completed"[^}]*\}', verification_text)
            if json_match:
                verification_json = json.loads(json_match.group(0))
                if isinstance(verification_json, dict) and 'is_completed' in verification_json:
                    is_completed = bool(verification_json['is_completed'])
                    reason = verification_json.get('reason', verification_text)
                else:
                    debug_logger.log_module('MultiAgentCoordinator', f'验证智能体回复格式不正确: {verification_text}')
            else:
                # JSON解析失败，回退到关键词匹配
                debug_logger.log_module('MultiAgentCoordinator', f'未找到JSON格式，使用关键词匹配: {verification_text}')
                if '【是】' in verification_text or '达标' in verification_text or '已完成' in verification_text or '成功完成' in verification_text:
                    is_completed = True
        except Exception as e:
            debug_logger.log_module('MultiAgentCoordinator', f'验证智能体回复解析失败: {e}, 回复内容: {verification_text}')
            # 回退到原有的关键词匹配逻辑
            if '【是】' in verification_text or '达标' in verification_text or '已完成' in verification_text or '成功完成' in verification_text:
                is_completed = True

        return {
            'is_completed': is_completed,
            'message': reason,
            'execution_summary': results_summary
        }
