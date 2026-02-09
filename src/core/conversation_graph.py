"""
LangGraph对话流程管理模块
使用LangGraph实现状态管理和对话流程编排
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator
from langgraph.graph import StateGraph, END

from src.tools.debug_logger import get_debug_logger

# 获取debug日志记录器
debug_logger = get_debug_logger()


class ConversationState(TypedDict):
    """
    对话状态
    定义对话流程中的所有状态变量
    """
    # 用户输入
    user_input: str
    
    # 消息历史
    messages: Annotated[List[Dict[str, str]], operator.add]
    
    # 理解阶段的结果
    understanding: Dict[str, Any]
    
    # 知识库检索结果
    knowledge: Dict[str, Any]
    
    # 视觉上下文
    vision_context: Optional[Dict[str, Any]]
    
    # 日程上下文
    schedule_context: Optional[str]
    schedule_action: Optional[str]
    
    # NPS工具上下文
    nps_context: Optional[str]
    
    # 是否需要情感分析
    need_emotion_analysis: bool
    
    # 情感分析结果
    emotion_data: Optional[Dict[str, Any]]
    
    # AI回复
    ai_response: str
    
    # 错误信息
    error: Optional[str]


class ConversationGraph:
    """
    对话流程图
    使用LangGraph编排对话的各个阶段
    """
    
    def __init__(self, chat_agent):
        """
        初始化对话流程图
        
        Args:
            chat_agent: ChatAgent实例，提供各种功能模块的访问
        """
        self.agent = chat_agent
        self.graph = self._build_graph()
        
        debug_logger.log_module('ConversationGraph', '对话流程图初始化完成', {})
    
    def _build_graph(self) -> StateGraph:
        """
        构建对话流程状态图
        
        Returns:
            StateGraph实例
        """
        # 创建状态图
        workflow = StateGraph(ConversationState)
        
        # 添加节点
        workflow.add_node("understand", self._understand_node)
        workflow.add_node("retrieve_knowledge", self._retrieve_knowledge_node)
        workflow.add_node("check_vision", self._check_vision_node)
        workflow.add_node("check_schedule", self._check_schedule_node)
        workflow.add_node("check_nps", self._check_nps_node)
        workflow.add_node("generate_response", self._generate_response_node)
        workflow.add_node("analyze_emotion", self._analyze_emotion_node)
        
        # 设置入口点
        workflow.set_entry_point("understand")
        
        # 添加边（流程路径）
        workflow.add_edge("understand", "retrieve_knowledge")
        workflow.add_edge("retrieve_knowledge", "check_vision")
        workflow.add_edge("check_vision", "check_schedule")
        workflow.add_edge("check_schedule", "check_nps")
        workflow.add_edge("check_nps", "generate_response")
        
        # 条件边：是否需要情感分析
        workflow.add_conditional_edges(
            "generate_response",
            self._should_analyze_emotion,
            {
                "analyze": "analyze_emotion",
                "end": END
            }
        )
        
        workflow.add_edge("analyze_emotion", END)
        
        # 编译图
        return workflow.compile()
    
    def _understand_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        理解阶段节点：初始化状态
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '理解阶段开始', {
            'input_length': len(state['user_input'])
        })
        
        return {
            "understanding": {
                "stage": "understand",
                "completed": True
            }
        }
    
    def _retrieve_knowledge_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        知识检索节点：从知识库检索相关信息
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '知识检索阶段', {})
        
        # 调用知识库检索
        relevant_knowledge = self.agent.memory_manager.knowledge_base.get_relevant_knowledge_for_query(
            state['user_input']
        )
        
        return {
            "knowledge": relevant_knowledge
        }
    
    def _check_vision_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        视觉检查节点：检查是否需要视觉工具
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '视觉检查阶段', {})
        
        # 检测环境切换意图
        switch_intent = self.agent.vision_tool.detect_environment_switch_intent(state['user_input'])
        if switch_intent and switch_intent.get('can_switch'):
            from_env = switch_intent['from_env']
            to_env = switch_intent['to_env']
            
            success = self.agent.vision_tool.switch_environment(to_env['uuid'])
            if success:
                switch_msg = f"\n🚪 [环境切换] 已从「{from_env['name']}」移动到「{to_env['name']}」"
                print(switch_msg)
                self.agent.memory_manager.add_message('system', switch_msg)
        
        # 检查是否需要使用视觉工具
        vision_context = self.agent.vision_tool.get_vision_context(state['user_input'])
        if vision_context:
            vision_summary = self.agent.vision_tool.get_vision_summary(vision_context)
            print(f"\n{vision_summary}")
        
        return {
            "vision_context": vision_context
        }
    
    def _check_schedule_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        日程检查节点：处理日程相关逻辑
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '日程检查阶段', {})
        
        schedule_context = None
        schedule_action = None
        
        # 这里可以添加日程相关的逻辑
        # 为了保持简洁，暂时返回空值
        
        return {
            "schedule_context": schedule_context,
            "schedule_action": schedule_action
        }
    
    def _check_nps_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        NPS工具检查节点：调用NPS工具系统
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', 'NPS工具检查阶段', {})
        
        nps_context = None
        nps_result = self.agent.nps_invoker.invoke_relevant_tools(state['user_input'])
        if nps_result['has_context']:
            nps_context = nps_result['context_info']
            invoked_tools = [r['tool_name'] for r in nps_result['tools_invoked'] if r['success']]
            if invoked_tools:
                print(f"\n🔧 [NPS工具] 已调用: {', '.join(invoked_tools)}")
        
        return {
            "nps_context": nps_context
        }
    
    def _generate_response_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        生成回复节点：使用LLM生成最终回复
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '生成回复阶段', {})
        
        # 这里将在后续实现中调用LLM生成回复
        # 暂时返回占位符
        return {
            "ai_response": "",
            "need_emotion_analysis": False
        }
    
    def _analyze_emotion_node(self, state: ConversationState) -> Dict[str, Any]:
        """
        情感分析节点：进行情感关系分析
        
        Args:
            state: 当前状态
            
        Returns:
            更新的状态
        """
        debug_logger.log_module('ConversationGraph', '情感分析阶段', {})
        
        emotion_data = self.agent.analyze_emotion()
        
        return {
            "emotion_data": emotion_data
        }
    
    def _should_analyze_emotion(self, state: ConversationState) -> str:
        """
        决定是否需要进行情感分析
        
        Args:
            state: 当前状态
            
        Returns:
            下一步行动 ("analyze" 或 "end")
        """
        if state.get('need_emotion_analysis', False):
            return "analyze"
        else:
            return "end"
    
    def process(self, user_input: str, messages: List[Dict[str, str]]) -> ConversationState:
        """
        处理对话
        
        Args:
            user_input: 用户输入
            messages: 消息历史
            
        Returns:
            最终状态
        """
        # 初始化状态
        initial_state: ConversationState = {
            "user_input": user_input,
            "messages": messages,
            "understanding": {},
            "knowledge": {},
            "vision_context": None,
            "schedule_context": None,
            "schedule_action": None,
            "nps_context": None,
            "need_emotion_analysis": False,
            "emotion_data": None,
            "ai_response": "",
            "error": None
        }
        
        # 执行流程图
        try:
            final_state = self.graph.invoke(initial_state)
            return final_state
        except Exception as e:
            debug_logger.log_error('ConversationGraph', f'流程执行错误: {str(e)}', e)
            return {
                **initial_state,
                "error": str(e),
                "ai_response": f"抱歉，处理请求时出现错误: {str(e)}"
            }
