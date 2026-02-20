"""
全能代理模块（OmniAgent）
参考openclaw的工作方式，实现具有技能系统和自主学习功能的全能代理

全能代理特性：
1. 拥有所有可用技能
2. 可以自主生成专业子智能体，每个子智能体拥有对应技能子集
3. 完成任务后自动学习，将成功经验提炼为新技能
4. 跨会话状态持久化
"""

import os
import re
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from dotenv import load_dotenv
from deepagents import create_deep_agent, SubAgent as DeepSubAgent
from deepagents.backends import StateBackend
from langgraph.checkpoint.memory import MemorySaver

from src.tools.debug_logger import get_debug_logger
from src.core.skill_registry import get_skill_registry, SKILL_PATH_BUILTIN, SKILL_PATH_LEARNED, SKILL_PATH_USER

load_dotenv()

debug_logger = get_debug_logger()

# 是否启用全能代理（默认开启）
USE_OMNI_AGENT = os.getenv('USE_OMNI_AGENT', 'true').lower() == 'true'
# 是否在任务完成后触发自主学习（默认开启）
ENABLE_AUTO_LEARNING = os.getenv('ENABLE_AUTO_LEARNING', 'true').lower() == 'true'
# 触发学习的最小任务输出长度（太短的任务不值得学习）
LEARNING_MIN_OUTPUT_LEN = int(os.getenv('LEARNING_MIN_OUTPUT_LEN', '200'))
# 提炼技能时用于提示词的最大结果文本长度
_LEARNING_RESULT_PREVIEW_LEN = 500


# 技能名称到角色类型的推荐映射（用于自动为子智能体分配技能）
_ROLE_SKILL_MAPPING: Dict[str, List[str]] = {
    "研究员": ["information_retrieval", "knowledge_extraction"],
    "分析师": ["information_retrieval", "result_synthesis"],
    "规划师": ["task_decomposition"],
    "执行者": ["error_recovery"],
    "综合师": ["result_synthesis", "knowledge_extraction"],
    "任务分析专家": ["task_decomposition", "information_retrieval"],
    "任务规划专家": ["task_decomposition"],
    "任务执行专家": ["error_recovery"],
    "任务验证专家": ["result_synthesis"],
}


def _get_skills_for_role(role: str) -> List[str]:
    """
    根据角色名称推荐适用技能名称列表

    Args:
        role: 角色名称

    Returns:
        推荐的技能名称列表
    """
    # 精确匹配
    if role in _ROLE_SKILL_MAPPING:
        return _ROLE_SKILL_MAPPING[role]
    # 模糊匹配
    for key, skills in _ROLE_SKILL_MAPPING.items():
        if key in role or role in key:
            return skills
    # 默认返回全部内置技能名称
    builtin_skills = get_skill_registry().list_skills(category="builtin")
    return [s["name"] for s in builtin_skills]


class OmniAgent:
    """
    全能代理
    参考openclaw的全能代理设计：
    - 拥有所有已注册技能
    - 可动态派生有特定技能的子智能体
    - 完成任务后自主学习，将成功经验写入技能注册表
    """

    def __init__(
        self,
        agent_id: str = "omni_agent",
        system_prompt_extra: str = "",
        memory_paths: Optional[List[str]] = None,
        tools: Optional[List[Any]] = None,
        progress_callback: Optional[Callable[[str], None]] = None,
        enable_auto_learning: bool = ENABLE_AUTO_LEARNING,
        **kwargs
    ):
        """
        初始化全能代理

        Args:
            agent_id: 代理唯一标识
            system_prompt_extra: 额外的系统提示词（追加到默认提示词之后）
            memory_paths: 长期记忆文件路径
            tools: 额外工具列表
            progress_callback: 进度回调函数
            enable_auto_learning: 是否启用任务后自主学习
            **kwargs: 其他参数（向后兼容）
        """
        self.agent_id = agent_id
        self.progress_callback = progress_callback
        self.enable_auto_learning = enable_auto_learning
        self.memory_paths = memory_paths or []
        self.tools = tools or []

        # 技能注册表
        self.skill_registry = get_skill_registry()

        # checkpointer用于跨会话状态持久化
        self.checkpointer = MemorySaver()

        # 构建系统提示词
        self.system_prompt = self._build_system_prompt(system_prompt_extra)

        # 创建LLM
        self._model = self._create_model()

        # 构建子智能体规格列表（deepagents SubAgent TypedDict）
        self._subagent_specs = self._build_subagent_specs()

        # 创建核心深度智能体
        self._agent = self._create_agent()

        debug_logger.log_module("OmniAgent", "全能代理初始化完成", {
            "agent_id": agent_id,
            "skills_count": len(self.skill_registry.list_skills()),
            "subagents_count": len(self._subagent_specs),
            "auto_learning": enable_auto_learning
        })

    def _build_system_prompt(self, extra: str = "") -> str:
        """构建系统提示词"""
        skill_summary = self.skill_registry.get_skill_summary()
        prompt = f"""你是一个全能智能代理（OmniAgent）。

你拥有以下能力：
1. 分析复杂任务并自主制定执行计划
2. 根据任务需要派生具有专项技能的子智能体
3. 从技能库（/skills/目录）中读取技能指导
4. 在任务完成后提炼经验，将有价值的方法写入/skills/learned/目录（自主学习）
5. 通过跨会话状态管理，记住历史任务经验

{skill_summary}

## 自主学习指南
当你完成一个复杂任务并找到了有效的解决方法，请：
1. 思考这个方法是否可以复用
2. 如果可以，使用 write_file 工具将方法保存到 /skills/learned/<技能名>.md
3. 技能文件应包含：描述、步骤、适用场景、注意事项

## 子智能体使用
你可以使用 task 工具调用专业子智能体处理特定任务：
- 每个子智能体拥有特定角色的技能子集
- 子智能体可以并行或顺序执行
"""
        if extra:
            prompt += f"\n\n{extra}"
        return prompt

    def _create_model(self):
        """创建LLM模型"""
        try:
            from src.core.langchain_llm import LangChainLLM, ModelType
            llm_wrapper = LangChainLLM(ModelType.MAIN)
            return llm_wrapper.llm
        except Exception as e:
            debug_logger.log_error("OmniAgent", f"创建主模型失败: {str(e)}", e)
            from langchain_openai import ChatOpenAI
            api_base = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1')
            if '/chat/completions' in api_base:
                api_base = api_base.replace('/chat/completions', '')
            return ChatOpenAI(
                model=os.getenv('MAIN_MODEL_NAME', 'deepseek-ai/DeepSeek-V3'),
                openai_api_base=api_base,
                openai_api_key=os.getenv('SILICONFLOW_API_KEY', ''),
                temperature=float(os.getenv('MAIN_MODEL_TEMPERATURE', '0.7'))
            )

    def _build_subagent_specs(self) -> List[DeepSubAgent]:
        """
        构建子智能体规格列表

        Returns:
            DeepSubAgent TypedDict列表
        """
        specs: List[DeepSubAgent] = []
        for role, skill_names in _ROLE_SKILL_MAPPING.items():
            # 获取此角色的技能文件
            skill_files = self.skill_registry.get_skills_for_agent(skill_names=skill_names)
            # 构建技能路径列表（在这些路径下有对应技能文件）
            skill_paths_for_role = list({
                p.rsplit('/', 2)[0] + '/'  # 从文件路径提取目录路径
                for p in skill_files.keys()
            })

            role_id = re.sub(r'[^a-z0-9]', '_', role.lower())
            spec: DeepSubAgent = {
                "name": role_id,
                "description": f"专业{role}，擅长：{', '.join(skill_names)}",
                "system_prompt": (
                    f"你是一个专业的{role}。\n"
                    f"你的专长技能：{', '.join(skill_names)}\n"
                    f"请参考/skills/目录下的技能文件来指导你的工作。\n"
                    "完成任务后提供结构化的结果。"
                ),
                "skills": skill_paths_for_role if skill_paths_for_role else [SKILL_PATH_BUILTIN],
            }
            specs.append(spec)

        debug_logger.log_info("OmniAgent", f"构建了{len(specs)}个子智能体规格")
        return specs

    def _create_agent(self):
        """创建核心深度智能体"""
        try:
            # 所有技能路径
            all_skill_paths = [SKILL_PATH_BUILTIN, SKILL_PATH_LEARNED, SKILL_PATH_USER]

            agent = create_deep_agent(
                model=self._model,
                tools=self.tools,
                system_prompt=self.system_prompt,
                subagents=self._subagent_specs,
                skills=all_skill_paths,
                memory=self.memory_paths if self.memory_paths else None,
                checkpointer=self.checkpointer,
                backend=StateBackend,
                name=self.agent_id
            )
            debug_logger.log_info("OmniAgent", "核心深度智能体创建成功")
            return agent
        except Exception as e:
            debug_logger.log_error("OmniAgent", f"创建深度智能体失败: {str(e)}", e)
            raise

    def execute_task(
        self,
        task_description: str,
        context: Dict[str, Any],
        thread_id: Optional[str] = None,
        extra_files: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        执行任务

        Args:
            task_description: 任务描述
            context: 上下文信息
            thread_id: 线程ID（用于跨会话状态管理）
            extra_files: 额外注入的文件内容

        Returns:
            结果字典，含 success、result、learned_skills 等字段
        """
        if thread_id is None:
            thread_id = f"{self.agent_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        self._emit_progress(f"全能代理开始处理任务: {task_description[:50]}...")

        # 合并技能文件和额外文件
        skill_files = self.skill_registry.get_skills_for_agent()
        files = dict(skill_files)
        if extra_files:
            files.update(extra_files)

        input_data = {
            "messages": [
                {
                    "role": "user",
                    "content": (
                        f"任务：{task_description}\n\n"
                        f"上下文：\n{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
                        "请完成这个任务。如需要，可以：\n"
                        "1. 使用 task 工具调用专业子智能体\n"
                        "2. 读取 /skills/ 目录获取技能指导\n"
                        "3. 完成后将成功方法写入 /skills/learned/ 目录"
                    )
                }
            ]
        }

        if files:
            input_data["files"] = files

        config = {"configurable": {"thread_id": thread_id}}

        try:
            result = self._agent.invoke(input_data, config=config)

            # 提取输出
            output = ""
            if "messages" in result:
                last = result["messages"][-1]
                output = last.content if hasattr(last, "content") else str(last)
            else:
                output = str(result)

            # 自主学习：从结果中提取并保存新技能
            learned_skills = []
            if self.enable_auto_learning and len(output) >= LEARNING_MIN_OUTPUT_LEN:
                learned_skills = self._auto_learn_from_result(
                    task_description=task_description,
                    result=output,
                    thread_id=thread_id
                )

            self._emit_progress(f"✅ 全能代理任务完成，学习了 {len(learned_skills)} 个新技能")

            return {
                "success": True,
                "result": output,
                "learned_skills": learned_skills,
                "thread_id": thread_id
            }

        except Exception as e:
            debug_logger.log_error("OmniAgent", f"任务执行失败: {str(e)}", e)
            return {
                "success": False,
                "error": str(e),
                "result": f"【执行失败】{str(e)}",
                "learned_skills": [],
                "thread_id": thread_id
            }

    def _auto_learn_from_result(
        self,
        task_description: str,
        result: str,
        thread_id: str
    ) -> List[str]:
        """
        自主学习：从任务结果中提炼可复用的技能

        Args:
            task_description: 任务描述
            result: 任务结果
            thread_id: 线程ID

        Returns:
            新学习到的技能名称列表
        """
        try:
            from src.core.langchain_llm import LangChainLLM, ModelType
            llm = LangChainLLM(ModelType.TOOL)

            prompt = f"""分析以下任务和结果，判断是否有值得保存为技能的方法。

任务：{task_description}

结果摘要：{result[:_LEARNING_RESULT_PREVIEW_LEN]}

请判断：
1. 这个任务是否用了可复用的方法？
2. 如果有，请用JSON格式输出（否则返回空数组[]）：
[
  {{
    "name": "技能名称（小写下划线，如data_cleaning）",
    "description": "一句话描述",
    "content": "## 技能名称\\n\\n## 描述\\n...\\n\\n## 步骤\\n1. ...\\n2. ...\\n\\n## 适用场景\\n..."
  }}
]

只返回JSON，不要其他内容。如果没有值得提炼的技能，返回空数组[]。"""

            messages = [
                {"role": "system", "content": "你是一个技能提炼专家。"},
                {"role": "user", "content": prompt}
            ]

            response = llm.chat(messages).strip()

            # 解析JSON
            if response.startswith('```'):
                lines = response.split('\n')
                response = '\n'.join(lines[1:-1])

            skills_data = json.loads(response)
            if not isinstance(skills_data, list):
                return []

            learned = []
            for skill_info in skills_data:
                name = skill_info.get("name", "").strip()
                if not name or not re.match(r'^[a-z][a-z0-9_]*$', name):
                    continue
                content = skill_info.get("content", "")
                desc = skill_info.get("description", "")
                if content and self.skill_registry.learn_skill(
                    name=name,
                    content=content,
                    description=desc,
                    source_task=task_description[:100]
                ):
                    learned.append(name)
                    debug_logger.log_info("OmniAgent", f"自主学习新技能: {name}")

            return learned

        except Exception as e:
            debug_logger.log_error("OmniAgent", f"自主学习失败（非致命）: {str(e)}", e)
            return []

    def _emit_progress(self, message: str):
        """输出进度信息"""
        print(f"📢 {message}")
        if self.progress_callback:
            self.progress_callback(f"📢 {message}")

    def add_skill(
        self,
        name: str,
        content: str,
        description: str = "",
        category: str = "user"
    ) -> bool:
        """
        手动添加技能到注册表

        Args:
            name: 技能名称
            content: 技能内容
            description: 描述
            category: 类别

        Returns:
            是否成功
        """
        return self.skill_registry.add_skill(name, content, category, description)

    def list_skills(self) -> List[Dict[str, Any]]:
        """获取所有可用技能列表"""
        return self.skill_registry.list_skills()


def create_omni_agent(
    agent_id: str = "omni_agent",
    progress_callback: Optional[Callable[[str], None]] = None,
    **kwargs
) -> OmniAgent:
    """
    工厂函数：创建全能代理

    Args:
        agent_id: 代理ID
        progress_callback: 进度回调
        **kwargs: 其他参数传递给OmniAgent

    Returns:
        OmniAgent实例
    """
    return OmniAgent(
        agent_id=agent_id,
        progress_callback=progress_callback,
        **kwargs
    )
