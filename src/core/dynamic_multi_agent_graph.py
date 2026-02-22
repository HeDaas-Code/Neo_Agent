"""
动态多智能体协作图模块
基于LangGraph实现自主编排的多智能体协作系统
增强版：集成DeepAgents长期记忆和跨会话状态管理
"""

import os
import json
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.tools.debug_logger import get_debug_logger
from src.core.event_manager import TaskEvent

# 获取debug日志记录器
debug_logger = get_debug_logger()

# 是否启用长期记忆和跨会话状态管理
ENABLE_PERSISTENT_STATE = os.getenv('ENABLE_PERSISTENT_STATE', 'true').lower() == 'true'


class AgentState(TypedDict):
    """
    智能体状态
    单个智能体的执行状态
    """
    agent_id: str
    role: str
    description: str
    task: str
    status: str  # 'pending', 'running', 'completed', 'failed'
    result: Optional[str]
    error: Optional[str]
    dependencies: List[str]  # 依赖的其他智能体ID


class MultiAgentState(TypedDict):
    """
    多智能体协作状态
    管理整个协作流程的状态
    """
    # 任务信息
    task_event: Dict[str, Any]
    character_context: Dict[str, Any]
    
    # 编排阶段
    orchestration_plan: Optional[Dict[str, Any]]  # 主模型生成的编排计划
    
    # 智能体列表
    agents: Annotated[List[AgentState], operator.add]
    
    # 执行结果
    agent_results: Dict[str, str]  # agent_id -> result
    
    # 协作日志
    collaboration_logs: Annotated[List[Dict[str, Any]], operator.add]
    
    # 最终结果
    final_result: Optional[str]
    
    # 错误信息
    error: Optional[str]
    
    # 流程控制
    next_action: str  # 'orchestrate', 'execute_parallel', 'execute_sequential', 'synthesize', 'end'


class DynamicMultiAgentGraph:
    """
    动态多智能体协作图
    使用LangGraph实现主模型自主编排的多智能体协作
    增强版：支持长期记忆和跨会话状态管理
    """
    
    def __init__(self, question_tool=None, progress_callback=None, enable_persistent_state=ENABLE_PERSISTENT_STATE):
        """
        初始化动态多智能体协作图
        
        Args:
            question_tool: 中断性提问工具
            progress_callback: 进度回调函数
            enable_persistent_state: 是否启用持久化状态管理
        """
        self.question_tool = question_tool
        self.progress_callback = progress_callback
        self.enable_persistent_state = enable_persistent_state
        
        # 启用持久化状态管理
        if self.enable_persistent_state:
            self.checkpointer = MemorySaver()
            debug_logger.log_info('DynamicMultiAgentGraph', '已启用持久化状态管理（checkpointer）')
        else:
            self.checkpointer = None
        
        self.graph = self._build_graph()
        
        debug_logger.log_module('DynamicMultiAgentGraph', '动态多智能体协作图初始化完成', {
            'enable_persistent_state': self.enable_persistent_state
        })
    
    def _build_graph(self) -> StateGraph:
        """
        构建动态协作流程图
        
        Returns:
            StateGraph实例
        """
        workflow = StateGraph(MultiAgentState)
        
        # 添加节点
        workflow.add_node("orchestrate", self._orchestrate_node)  # 主模型编排
        workflow.add_node("execute_parallel", self._execute_parallel_node)  # 并行执行
        workflow.add_node("execute_sequential", self._execute_sequential_node)  # 顺序执行
        workflow.add_node("synthesize", self._synthesize_node)  # 结果综合
        
        # 设置入口点
        workflow.set_entry_point("orchestrate")
        
        # 添加条件边
        workflow.add_conditional_edges(
            "orchestrate",
            self._route_after_orchestration,
            {
                "execute_parallel": "execute_parallel",
                "execute_sequential": "execute_sequential",
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "execute_parallel",
            self._route_after_execution,
            {
                "synthesize": "synthesize",
                "execute_parallel": "execute_parallel",  # 继续执行剩余任务
                "end": END
            }
        )
        
        workflow.add_conditional_edges(
            "execute_sequential",
            self._route_after_execution,
            {
                "synthesize": "synthesize",
                "execute_sequential": "execute_sequential",  # 继续执行下一步
                "end": END
            }
        )
        
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _emit_progress(self, state: MultiAgentState, message: str):
        """
        输出进度信息
        
        Args:
            state: 当前状态
            message: 进度消息
        """
        narration = f"📢 {message}"
        print(narration)
        
        if self.progress_callback:
            self.progress_callback(narration)
        
        # 添加到协作日志
        state['collaboration_logs'].append({
            'timestamp': self._get_timestamp(),
            'type': 'progress',
            'message': message
        })
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def _orchestrate_node(self, state: MultiAgentState) -> MultiAgentState:
        """
        编排节点：主模型分析任务并生成执行计划
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        debug_logger.log_module('DynamicMultiAgentGraph', '开始任务编排', {})
        
        task_event = state['task_event']
        self._emit_progress(state, f"主模型开始分析任务「{task_event['title']}」...")
        
        # 使用主模型分析任务并生成编排计划
        orchestration_plan = self._generate_orchestration_plan(state)
        
        if not orchestration_plan or 'error' in orchestration_plan:
            state['error'] = orchestration_plan.get('error', '编排失败') if orchestration_plan else '编排失败'
            state['next_action'] = 'end'
            return state
        
        state['orchestration_plan'] = orchestration_plan
        
        # 根据编排计划设置下一步动作
        execution_strategy = orchestration_plan.get('execution_strategy', 'sequential')
        
        if execution_strategy == 'parallel':
            state['next_action'] = 'execute_parallel'
            self._emit_progress(state, f"计划采用并行执行策略，共{len(orchestration_plan['agents'])}个智能体")
        elif execution_strategy == 'sequential':
            state['next_action'] = 'execute_sequential'
            self._emit_progress(state, f"计划采用顺序执行策略，共{len(orchestration_plan['agents'])}个步骤")
        else:
            # 简单任务，直接结束
            state['next_action'] = 'end'
            state['final_result'] = orchestration_plan.get('direct_result', '任务过于简单，无需多智能体协作')
        
        return state
    
    def _execute_parallel_node(self, state: MultiAgentState) -> MultiAgentState:
        """
        并行执行节点：同时执行多个独立的智能体任务
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        debug_logger.log_module('DynamicMultiAgentGraph', '开始并行执行', {})
        
        plan = state['orchestration_plan']
        agents_to_execute = [a for a in plan['agents'] if a.get('status') == 'pending']
        
        if not agents_to_execute:
            state['next_action'] = 'synthesize'
            return state
        
        self._emit_progress(state, f"并行执行{len(agents_to_execute)}个智能体任务...")
        
        # 使用线程池并行执行
        with ThreadPoolExecutor(max_workers=min(len(agents_to_execute), 3)) as executor:
            futures = {}
            for agent_state in agents_to_execute:
                future = executor.submit(self._execute_agent, agent_state, state)
                futures[future] = agent_state['agent_id']
            
            # 收集结果
            for future in as_completed(futures):
                agent_id = futures[future]
                try:
                    result = future.result()
                    state['agent_results'][agent_id] = result['result']
                    
                    # 更新智能体状态
                    for a in plan['agents']:
                        if a['agent_id'] == agent_id:
                            a['status'] = 'completed' if result['success'] else 'failed'
                            a['result'] = result['result']
                            if not result['success']:
                                a['error'] = result.get('error')
                    
                    self._emit_progress(state, f"智能体 [{result['role']}] 完成任务")
                    
                except Exception as e:
                    debug_logger.log_error('DynamicMultiAgentGraph', f'智能体执行异常: {str(e)}', e)
                    state['agent_results'][agent_id] = f"执行失败: {str(e)}"
        
        # 检查是否还有待执行的智能体
        remaining = [a for a in plan['agents'] if a.get('status') == 'pending']
        if remaining:
            state['next_action'] = 'execute_parallel'
        else:
            state['next_action'] = 'synthesize'
        
        return state
    
    def _execute_sequential_node(self, state: MultiAgentState) -> MultiAgentState:
        """
        顺序执行节点：按依赖关系顺序执行智能体任务
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        debug_logger.log_module('DynamicMultiAgentGraph', '开始顺序执行', {})
        
        plan = state['orchestration_plan']
        agents_to_execute = [a for a in plan['agents'] if a.get('status') == 'pending']
        
        if not agents_to_execute:
            state['next_action'] = 'synthesize'
            return state
        
        # 找到第一个可执行的智能体（依赖已满足）
        executable = None
        for agent_state in agents_to_execute:
            dependencies = agent_state.get('dependencies', [])
            if all(state['agent_results'].get(dep_id) for dep_id in dependencies):
                executable = agent_state
                break
        
        if not executable:
            # 没有可执行的智能体，可能是依赖关系有问题
            state['error'] = '无法找到可执行的智能体，可能存在循环依赖'
            state['next_action'] = 'end'
            return state
        
        self._emit_progress(state, f"执行智能体 [{executable['role']}] 的任务...")
        
        # 执行智能体
        result = self._execute_agent(executable, state)
        state['agent_results'][executable['agent_id']] = result['result']
        
        # 更新智能体状态
        for a in plan['agents']:
            if a['agent_id'] == executable['agent_id']:
                a['status'] = 'completed' if result['success'] else 'failed'
                a['result'] = result['result']
                if not result['success']:
                    a['error'] = result.get('error')
        
        self._emit_progress(state, f"智能体 [{result['role']}] 完成任务")
        
        # 检查是否还有待执行的智能体
        remaining = [a for a in plan['agents'] if a.get('status') == 'pending']
        if remaining:
            state['next_action'] = 'execute_sequential'
        else:
            state['next_action'] = 'synthesize'
        
        return state
    
    def _synthesize_node(self, state: MultiAgentState) -> MultiAgentState:
        """
        综合节点：整合所有智能体的结果
        
        Args:
            state: 当前状态
            
        Returns:
            更新后的状态
        """
        debug_logger.log_module('DynamicMultiAgentGraph', '开始结果综合', {})
        
        self._emit_progress(state, "主模型正在整合所有智能体的结果...")
        
        # 使用主模型综合结果
        final_result = self._synthesize_results(state)
        
        state['final_result'] = final_result
        state['next_action'] = 'end'
        
        self._emit_progress(state, "✅ 任务完成，结果已生成")
        
        return state
    
    def _route_after_orchestration(self, state: MultiAgentState) -> str:
        """路由：编排后的下一步"""
        return state['next_action']
    
    def _route_after_execution(self, state: MultiAgentState) -> str:
        """路由：执行后的下一步"""
        return state['next_action']
    
    def _generate_orchestration_plan(self, state: MultiAgentState) -> Dict[str, Any]:
        """
        使用主模型生成编排计划
        
        Args:
            state: 当前状态
            
        Returns:
            编排计划
        """
        from src.core.langchain_llm import LangChainLLM, ModelType
        from src.core.prompt_manager import get_prompt_manager
        
        task_event = state['task_event']
        
        try:
            # 使用主模型进行任务编排
            llm = LangChainLLM(ModelType.MAIN)
            prompt_manager = get_prompt_manager()
            
            # 构建编排提示词
            orchestration_prompt = f"""你是一个任务编排专家，负责分析任务并决定最佳的执行策略。

任务信息：
- 标题：{task_event['title']}
- 描述：{task_event['description']}
- 要求：{task_event.get('metadata', {}).get('task_requirements', '无')}

请分析这个任务，并决定：
1. 任务复杂度（简单/中等/复杂）
2. 最佳执行策略（simple/parallel/sequential）
3. 需要的智能体列表

执行策略说明：
- simple: 任务很简单，可以直接回答，不需要多智能体
- parallel: 任务可以分解为多个独立的子任务，智能体可以并行执行
- sequential: 任务需要按步骤执行，后续步骤依赖前面的结果

请以JSON格式返回：
{{
    "complexity": "simple|medium|complex",
    "execution_strategy": "simple|parallel|sequential",
    "reasoning": "你的分析理由",
    "agents": [
        {{
            "agent_id": "唯一ID",
            "role": "角色名称（如：研究员、分析师）",
            "description": "职责描述",
            "task": "具体任务",
            "dependencies": ["依赖的agent_id列表，并行时为空"]
        }}
    ],
    "direct_result": "如果是simple策略，直接提供结果"
}}

只返回JSON，不要其他内容。"""
            
            messages = [
                {'role': 'system', 'content': '你是一个专业的任务编排专家。'},
                {'role': 'user', 'content': orchestration_prompt}
            ]
            
            response = llm.chat(messages)
            
            # 解析JSON
            response = response.strip()
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1]) if len(lines) > 2 else response
                if response.startswith('json'):
                    response = response[4:].strip()
            
            plan = json.loads(response)
            
            # 初始化智能体状态
            for agent in plan.get('agents', []):
                agent['status'] = 'pending'
                agent['result'] = None
                agent['error'] = None
                if 'dependencies' not in agent:
                    agent['dependencies'] = []
            
            debug_logger.log_info('DynamicMultiAgentGraph', '编排计划生成成功', {
                'strategy': plan.get('execution_strategy'),
                'agents_count': len(plan.get('agents', []))
            })
            
            return plan
            
        except Exception as e:
            debug_logger.log_error('DynamicMultiAgentGraph', f'生成编排计划失败: {str(e)}', e)
            return {'error': f'编排失败: {str(e)}'}
    
    def _execute_agent(self, agent_state: AgentState, state: MultiAgentState) -> Dict[str, Any]:
        """
        执行单个智能体任务
        
        Args:
            agent_state: 智能体状态
            state: 全局状态
            
        Returns:
            执行结果
        """
        from src.core.multi_agent_coordinator import create_sub_agent
        
        agent = create_sub_agent(
            agent_id=agent_state['agent_id'],
            role=agent_state['role'],
            description=agent_state['description']
        )
        
        # 构建上下文，包含依赖的智能体结果
        context = {
            'task_info': state['task_event'],
            'character': state['character_context']
        }
        
        # 添加依赖的智能体结果
        if agent_state.get('dependencies'):
            context['dependency_results'] = {
                dep_id: state['agent_results'].get(dep_id, '未执行')
                for dep_id in agent_state['dependencies']
            }
        
        try:
            result = agent.execute_task(agent_state['task'], context)
            
            state['collaboration_logs'].append({
                'timestamp': self._get_timestamp(),
                'agent_id': agent_state['agent_id'],
                'role': agent_state['role'],
                'action': '任务完成',
                'result': result[:200] + '...' if len(result) > 200 else result
            })
            
            return {
                'success': True,
                'role': agent_state['role'],
                'result': result
            }
            
        except Exception as e:
            debug_logger.log_error('DynamicMultiAgentGraph', f'智能体执行失败: {str(e)}', e)
            return {
                'success': False,
                'role': agent_state['role'],
                'result': f'执行失败: {str(e)}',
                'error': str(e)
            }
    
    def _synthesize_results(self, state: MultiAgentState) -> str:
        """
        使用主模型综合所有智能体的结果
        
        Args:
            state: 当前状态
            
        Returns:
            综合后的最终结果
        """
        from src.core.langchain_llm import LangChainLLM, ModelType
        
        try:
            llm = LangChainLLM(ModelType.MAIN)
            
            # 构建综合提示词
            agent_results_text = "\n\n".join([
                f"[{agent['role']}] 的结果：\n{state['agent_results'].get(agent['agent_id'], '未执行')}"
                for agent in state['orchestration_plan']['agents']
            ])
            
            synthesis_prompt = f"""请整合以下多个智能体的工作结果，生成一个完整、连贯的最终答案。

原始任务：{state['task_event']['title']}

各智能体的结果：
{agent_results_text}

请将这些结果整合成一个完整的答案，确保：
1. 内容连贯、逻辑清晰
2. 覆盖所有重要信息
3. 去除重复内容
4. 语言自然流畅

直接输出最终答案，不要添加额外的说明。"""
            
            messages = [
                {'role': 'system', 'content': '你是一个信息整合专家，擅长将多个来源的信息整合成连贯的答案。'},
                {'role': 'user', 'content': synthesis_prompt}
            ]
            
            final_result = llm.chat(messages)
            
            debug_logger.log_info('DynamicMultiAgentGraph', '结果综合完成', {
                'result_length': len(final_result)
            })
            
            return final_result
            
        except Exception as e:
            debug_logger.log_error('DynamicMultiAgentGraph', f'结果综合失败: {str(e)}', e)
            # 如果综合失败，返回所有结果的简单拼接
            return "\n\n".join([
                f"【{agent['role']}】\n{state['agent_results'].get(agent['agent_id'], '未执行')}"
                for agent in state['orchestration_plan']['agents']
            ])
    
    def process_task_event(
        self,
        task_event: TaskEvent,
        character_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        处理任务事件
        
        Args:
            task_event: 任务事件
            character_context: 角色上下文
            
        Returns:
            处理结果
        """
        debug_logger.log_module('DynamicMultiAgentGraph', '开始处理任务事件', {
            'event_id': task_event.event_id,
            'title': task_event.title
        })
        
        # 初始化状态
        initial_state = {
            'task_event': {
                'event_id': task_event.event_id,
                'title': task_event.title,
                'description': task_event.description,
                'metadata': task_event.metadata
            },
            'character_context': character_context,
            'orchestration_plan': None,
            'agents': [],
            'agent_results': {},
            'collaboration_logs': [],
            'final_result': None,
            'error': None,
            'next_action': 'orchestrate'
        }
        
        # 执行工作流（使用checkpointer支持跨会话状态管理）
        try:
            if self.enable_persistent_state and self.checkpointer:
                # 使用事件ID作为线程ID，实现跨会话状态管理
                thread_id = f"task_{task_event.event_id}"
                config = {
                    "configurable": {
                        "thread_id": thread_id
                    }
                }
                
                debug_logger.log_info('DynamicMultiAgentGraph', '使用持久化状态', {
                    'thread_id': thread_id
                })
                
                final_state = self.graph.invoke(initial_state, config=config)
            else:
                # 无状态执行
                final_state = self.graph.invoke(initial_state)
            
            if final_state.get('error'):
                return {
                    'success': False,
                    'error': final_state['error'],
                    'orchestration_plan': final_state.get('orchestration_plan'),
                    'agent_results': final_state.get('agent_results', {}),
                    'collaboration_logs': final_state.get('collaboration_logs', [])
                }
            
            # 检查智能体执行状态，判断任务是否真正成功
            orchestration_plan = final_state.get('orchestration_plan', {})
            agents = orchestration_plan.get('agents', [])
            strategy = orchestration_plan.get('execution_strategy', '')
            
            if agents:
                # 统计成功和失败的智能体数量
                successful_agents = [a for a in agents if a.get('status') == 'completed']
                failed_agents = [a for a in agents if a.get('status') == 'failed']
                
                # 如果所有智能体都失败，任务失败
                if failed_agents and not successful_agents:
                    error_details = []
                    for agent in failed_agents:
                        error_msg = agent.get('error', '未知错误')
                        error_details.append(f"[{agent.get('role', '未知')}]: {error_msg}")
                    
                    return {
                        'success': False,
                        'error': f"所有智能体执行失败。详情：\n" + "\n".join(error_details),
                        'result': final_state.get('final_result', '任务执行失败'),
                        'orchestration_plan': orchestration_plan,
                        'agent_results': final_state.get('agent_results', {}),
                        'collaboration_logs': final_state.get('collaboration_logs', []),
                        'failed_agents_count': len(failed_agents),
                        'successful_agents_count': len(successful_agents)
                    }
                
                # 如果有部分智能体失败，在结果中说明但仍标记为成功（部分成功）
                if failed_agents:
                    debug_logger.log_warning('DynamicMultiAgentGraph', 
                        f'任务部分完成：{len(successful_agents)}/{len(agents)}个智能体成功', {
                        'successful': len(successful_agents),
                        'failed': len(failed_agents)
                    })
            
            # 对于simple策略，返回结果但标记为需要用户确认
            # 避免在计划生成后立即标记为完成
            if strategy == 'simple':
                return {
                    'success': True,
                    'result': final_state.get('final_result', '任务完成'),
                    'orchestration_plan': orchestration_plan,
                    'agent_results': final_state.get('agent_results', {}),
                    'collaboration_logs': final_state.get('collaboration_logs', []),
                    'is_simple_result': True,  # 标记为简单结果，需要延迟状态更新
                    'requires_delivery_confirmation': True  # 需要确认结果已交付
                }
            
            return {
                'success': True,
                'result': final_state.get('final_result', '任务完成'),
                'orchestration_plan': orchestration_plan,
                'agent_results': final_state.get('agent_results', {}),
                'collaboration_logs': final_state.get('collaboration_logs', [])
            }
            
        except Exception as e:
            debug_logger.log_error('DynamicMultiAgentGraph', f'任务处理失败: {str(e)}', e)
            return {
                'success': False,
                'error': f'任务处理失败: {str(e)}',
                'orchestration_plan': initial_state.get('orchestration_plan'),
                'agent_results': initial_state.get('agent_results', {}),
                'collaboration_logs': initial_state.get('collaboration_logs', [])
            }
