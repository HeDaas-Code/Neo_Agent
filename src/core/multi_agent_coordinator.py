"""
多智能体协作模块
实现任务型事件的多智能体协作处理
"""

import os
import time
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dotenv import load_dotenv
import requests
from src.core.event_manager import TaskEvent
from src.tools.interrupt_question_tool import InterruptQuestionTool
from src.tools.debug_logger import get_debug_logger
from src.core.deepagents_wrapper import DeepSubAgentWrapper

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()

# 标志：是否使用deepagents增强的子智能体
USE_DEEP_AGENTS = os.getenv('USE_DEEP_AGENTS', 'true').lower() == 'true'


class SubAgent:
    """
    子智能体类
    代表参与协作的单个智能体
    """

    def __init__(
        self,
        agent_id: str,
        role: str,
        description: str
    ):
        """
        初始化子智能体（使用LangChain）

        Args:
            agent_id: 智能体ID
            role: 智能体角色
            description: 角色描述
        """
        self.agent_id = agent_id
        self.role = role
        self.description = description

    def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any],
        tools: List[Dict[str, Any]] = None
    ) -> str:
        """
        执行任务（使用提示词模板）

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

        try:
            # 尝试使用提示词模板
            from src.core.prompt_manager import get_prompt_manager
            prompt_manager = get_prompt_manager()
            
            # 构建工具描述
            tools_description = ""
            if tools:
                tools_description = "\n可用工具：\n"
                for tool in tools:
                    tools_description += f"- {tool['name']}: {tool['description']}\n"
            
            # 准备变量
            variables = {
                'agent_role': self.role,
                'agent_description': self.description,
                'task_description': task_description,
                'context': json.dumps(context, ensure_ascii=False, indent=2),
                'tools_description': tools_description or "无可用工具"
            }
            
            # 加载并渲染任务提示词
            system_prompt = prompt_manager.get_task_prompt('sub_agent_task', variables)
            
        except Exception as e:
            # 如果模板加载失败，使用后备的硬编码提示词
            debug_logger.log_error('SubAgent', f'加载提示词模板失败，使用后备提示词: {str(e)}', e)
            system_prompt = self._build_fallback_prompt(task_description, context, tools)

        # 使用LangChain LLM执行任务
        try:
            from src.core.langchain_llm import LangChainLLM, ModelType
            
            # 子智能体使用工具模型（小模型）
            llm = LangChainLLM(ModelType.TOOL)
            
            messages = [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': f'请完成任务：{task_description}'}
            ]
            
            debug_logger.log_module('SubAgent', f'使用工具模型执行任务', {
                'model_name': llm.model_name
            })
            
            output = llm.chat(messages)
            
            debug_logger.log_info('SubAgent', f'智能体[{self.role}]任务完成', {
                'output_length': len(output)
            })
            return output

        except Exception as e:
            debug_logger.log_error('SubAgent', f'智能体[{self.role}]执行失败: {str(e)}', e)
            return f"【执行失败】{str(e)}"

    def _build_fallback_prompt(
        self,
        task_description: str,
        context: Dict[str, Any],
        tools: List[Dict[str, Any]] = None
    ) -> str:
        """
        构建后备提示词（兼容性）

        Args:
            task_description: 任务描述
            context: 上下文信息
            tools: 可用工具列表

        Returns:
            提示词
        """
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

        return system_prompt


def create_sub_agent(
    agent_id: str,
    role: str,
    description: str,
    use_deep_agents: bool = USE_DEEP_AGENTS
) -> 'SubAgent':
    """
    工厂函数：创建子智能体
    根据配置选择使用传统SubAgent或DeepAgents增强版本

    Args:
        agent_id: 智能体ID
        role: 角色名称
        description: 角色描述
        use_deep_agents: 是否使用deepagents（默认从环境变量读取）

    Returns:
        SubAgent或DeepSubAgentWrapper实例
    """
    if use_deep_agents:
        try:
            debug_logger.log_info('SubAgentFactory', f'创建DeepAgents增强子智能体: {role}')
            return DeepSubAgentWrapper(
                agent_id=agent_id,
                role=role,
                description=description
            )
        except Exception as e:
            debug_logger.log_error('SubAgentFactory', 
                f'创建DeepAgents子智能体失败，降级到传统模式: {str(e)}', e)
            # 降级到传统SubAgent
            return SubAgent(agent_id, role, description)
    else:
        debug_logger.log_info('SubAgentFactory', f'创建传统子智能体: {role}')
        return SubAgent(agent_id, role, description)


class MultiAgentCoordinator:
    """
    多智能体协调器
    负责协调多个智能体完成复杂任务
    支持传统的固定流程和新的动态流程
    """

    def __init__(
        self,
        question_tool: InterruptQuestionTool,
        progress_callback: Optional[Callable[[str], None]] = None,
        use_dynamic_graph: bool = True
    ):
        """
        初始化多智能体协调器（使用LangChain架构）

        Args:
            question_tool: 中断性提问工具
            progress_callback: 进度回调函数
            use_dynamic_graph: 是否使用动态协作图（默认True）
        """
        self.question_tool = question_tool
        self.progress_callback = progress_callback
        self.use_dynamic_graph = use_dynamic_graph
        
        # 协作日志记录
        self.collaboration_logs = []
        
        # 初始化动态协作图
        if use_dynamic_graph:
            try:
                from src.core.dynamic_multi_agent_graph import DynamicMultiAgentGraph
                self.dynamic_graph = DynamicMultiAgentGraph(
                    question_tool=question_tool,
                    progress_callback=progress_callback
                )
                debug_logger.log_module('MultiAgentCoordinator', 
                    '多智能体协调器初始化完成（使用动态LangGraph协作）')
            except Exception as e:
                debug_logger.log_error('MultiAgentCoordinator', 
                    f'动态协作图初始化失败，降级到传统模式: {str(e)}', e)
                self.use_dynamic_graph = False
                self.dynamic_graph = None
                debug_logger.log_module('MultiAgentCoordinator', 
                    '多智能体协调器初始化完成（使用传统固定流程）')
        else:
            self.dynamic_graph = None
            debug_logger.log_module('MultiAgentCoordinator', 
                '多智能体协调器初始化完成（使用传统固定流程）')

    def add_collaboration_log(self, agent_role: str, action: str, content: str):
        """
        添加协作日志
        
        Args:
            agent_role: 智能体角色
            action: 动作类型
            content: 日志内容
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'agent_role': agent_role,
            'action': action,
            'content': content
        }
        self.collaboration_logs.append(log_entry)
        debug_logger.log_info('MultiAgentCoordinator', '协作日志', log_entry)

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
        
        # 记录到协作日志
        self.add_collaboration_log('系统', '进度通知', message)
        
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
        根据配置选择动态协作图或传统固定流程

        Args:
            task_event: 任务事件
            character_context: 角色上下文信息

        Returns:
            处理结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '开始处理任务型事件', {
            'event_id': task_event.event_id,
            'title': task_event.title,
            'mode': 'dynamic' if self.use_dynamic_graph else 'traditional'
        })

        # 使用动态协作图
        if self.use_dynamic_graph and self.dynamic_graph:
            try:
                result = self.dynamic_graph.process_task_event(task_event, character_context)
                # 合并协作日志
                self.collaboration_logs = result.get('collaboration_logs', [])
                return result
            except Exception as e:
                debug_logger.log_error('MultiAgentCoordinator', 
                    f'动态协作图执行失败，降级到传统模式: {str(e)}', e)
                # 降级到传统模式
                return self._process_task_event_traditional(task_event, character_context)
        
        # 使用传统固定流程
        return self._process_task_event_traditional(task_event, character_context)

    def _process_task_event_traditional(
        self,
        task_event: TaskEvent,
        character_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        使用传统固定流程处理任务型事件（后备方案）

        Args:
            task_event: 任务事件
            character_context: 角色上下文信息

        Returns:
            处理结果
        """
        debug_logger.log_module('MultiAgentCoordinator', '使用传统固定流程处理任务')

        # 清空之前的协作日志
        self.collaboration_logs = []

        self.emit_progress(f"智能体开始分析任务「{task_event.title}」...")

        # 第一步：理解任务
        task_understanding = self._understand_task(task_event, character_context)
        
        if not task_understanding.get('success'):
            return {
                'success': False,
                'error': task_understanding.get('error', '任务理解失败'),
                'collaboration_logs': self.collaboration_logs
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
                    'execution_results': execution_results,
                    'collaboration_logs': self.collaboration_logs
                }

            self.emit_progress(f"步骤 {i} 完成")

        # 所有步骤已完成，返回结果给用户
        self.emit_progress("✅ 所有步骤已完成，任务结果已提交给用户")
        
        return {
            'success': True,
            'message': '任务执行完成，请查看执行结果',
            'execution_results': execution_results,
            'task_understanding': task_understanding,
            'execution_plan': execution_plan,
            'collaboration_logs': self.collaboration_logs
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

        # 创建理解智能体（使用工厂函数）
        understanding_agent = create_sub_agent(
            agent_id='understanding_agent',
            role='任务分析专家',
            description='负责理解和分析任务需求'
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

        # 记录协作日志：任务理解开始
        self.add_collaboration_log('任务分析专家', '开始分析', f'开始分析任务：{task_event.title}')

        result = understanding_agent.execute_task(
            '请分析这个任务，总结任务的核心目标、关键要求和预期成果。用简洁的语言概括。',
            context
        )

        # 记录协作日志：任务理解结果
        self.add_collaboration_log('任务分析专家', '分析结果', result)

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

        # 创建规划智能体（使用工厂函数）
        planning_agent = create_sub_agent(
            agent_id='planning_agent',
            role='任务规划专家',
            description='负责将复杂任务分解为可执行的步骤'
        )

        context = {
            'task_understanding': task_understanding['summary'],
            'task_requirements': task_event.metadata.get('task_requirements', ''),
            'completion_criteria': task_event.metadata.get('completion_criteria', '')
        }

        # 记录协作日志：开始规划
        self.add_collaboration_log('任务规划专家', '开始规划', '基于任务分析结果制定执行计划')

        plan_text = planning_agent.execute_task(
            '请将这个任务分解为3-5个具体可执行的步骤。每个步骤用一行描述，格式为：步骤N：具体要做的事情',
            context
        )

        # 记录协作日志：规划结果
        self.add_collaboration_log('任务规划专家', '规划结果', plan_text)

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

        # 创建执行智能体（使用工厂函数）
        execution_agent = create_sub_agent(
            agent_id=f'execution_agent_{len(previous_results)}',
            role='任务执行专家',
            description='负责执行具体的任务步骤'
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

        # 记录协作日志：开始执行步骤
        self.add_collaboration_log('任务执行专家', '开始执行', f'步骤：{step["description"]}')

        result_text = execution_agent.execute_task(
            step['description'],
            context,
            tools
        )

        # 记录协作日志：执行结果
        self.add_collaboration_log('任务执行专家', '执行结果', result_text)

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

        # 创建验证智能体（使用工厂函数）
        verification_agent = create_sub_agent(
            agent_id='verification_agent',
            role='任务验证专家',
            description='负责验证任务是否达到完成标准'
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
