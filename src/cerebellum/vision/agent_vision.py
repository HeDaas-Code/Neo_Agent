"""
智能体视觉工具模块
通过读取数据库中的环境描述来模拟智能体的伪视觉功能
当用户询问周围环境时，智能体自动决定是否使用此工具
"""

import os
import re
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from dotenv import load_dotenv
import requests
from src.core.database_manager import DatabaseManager
from src.core import llm_providers  # v3.1.0: 统一供应商解析
from src.tools.debug_logger import get_debug_logger

load_dotenv()

# 获取debug日志记录器
debug_logger = get_debug_logger()


class AgentVisionTool:
    """
    智能体视觉工具类
    负责检测用户查询是否涉及环境，并从数据库读取相应的环境描述
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化视觉工具

        Args:
            db_manager: 数据库管理器实例
        """
        self.db = db_manager or DatabaseManager()

        # API配置（用于智能判断是否需要使用视觉工具）
        # v3.1.0: 用 llm_providers 解析（保留旧 SILICONFLOW_API_KEY 兼容）
        self.api_key = llm_providers.resolve_api_key()
        try:
            self.api_url = llm_providers.resolve_base_url(llm_providers.resolve_provider())
        except Exception:
            self.api_url = os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')
        
        # 环境相关关键词（用于快速判断）
        # 包含常见的位置查询关键词，如"在哪"用于检测"你在哪？"等查询
        self.environment_keywords = [
            '周围', '周边', '环境', '这里', '附近', '哪里', '什么地方', '在哪',
            '看到', '看见', '观察', '眼前', '面前', '旁边', '身边',
            '房间', '屋子', '地方', '场景', '景色', '风景',
            '有什么', '有哪些', '能看到', '可以看到'
        ]
        
        debug_logger.log_module('AgentVisionTool', '视觉工具初始化完成', {
            'keywords_count': len(self.environment_keywords)
        })

    def should_use_vision_llm(self, user_query: str) -> bool:
        """
        使用LLM智能判断是否需要使用视觉工具
        
        注意：
        - 输入清理可防止基本的注入攻击，但不是完全安全
        - 响应解析目前仅支持中文，需要国际化时需修改
        - 同步HTTP请求可能造成阻塞，高频调用时建议使用异步方式
        
        Args:
            user_query: 用户查询
            
        Returns:
            是否需要使用视觉
        """
        debug_logger.log_module('AgentVisionTool', '使用LLM判断是否需要视觉', {
            'query': user_query
        })
        
        try:
            # 对用户输入进行清理和验证，防止prompt注入攻击
            # 1. 移除可疑模式（系统提示、角色扮演等）
            suspicious_patterns = [
                'system:', 'assistant:', 'user:', 
                'ignore previous', 'ignore all previous',
                'new instructions', 'forget everything',
                '###', '---', '```'
            ]
            
            # 检查是否包含可疑模式
            query_lower = user_query.lower()
            for pattern in suspicious_patterns:
                if pattern in query_lower:
                    debug_logger.log_error('AgentVisionTool', f"检测到可疑输入模式: {pattern}", None)
                    # 对于可疑输入，使用关键词匹配而非LLM
                    return self._check_vision_keywords(user_query)
            
            # 2. 基本清理
            cleaned_query = user_query.replace('"', '\\"').replace('\n', ' ').strip()
            
            # 3. 限制查询长度
            if len(cleaned_query) > 500:
                cleaned_query = cleaned_query[:500]
            
            # 构建判断提示词
            judge_prompt = f"""请判断以下用户问题是否需要智能体观察周围环境才能回答。

用户问题："{cleaned_query}"

需要观察环境的情况包括但不限于：
1. 询问智能体的位置或所在地（如：你在哪？你在哪里？）
2. 询问周围有什么、看到什么
3. 询问环境、房间、场景相关的问题
4. 询问附近、旁边、面前的事物
5. 需要了解当前环境状态才能回答的问题

请只回答"是"或"否"，不要有其他内容。"""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # 从环境变量读取配置或使用默认值
            try:
                llm_temperature = float(os.getenv('VISION_LLM_TEMPERATURE', '0.3'))
            except ValueError:
                llm_temperature = 0.3
                debug_logger.log_info('AgentVisionTool', '无效的VISION_LLM_TEMPERATURE，使用默认值0.3')
            
            try:
                llm_max_tokens = int(os.getenv('VISION_LLM_MAX_TOKENS', '10'))
            except ValueError:
                llm_max_tokens = 10
                debug_logger.log_info('AgentVisionTool', '无效的VISION_LLM_MAX_TOKENS，使用默认值10')
            
            try:
                llm_timeout = int(os.getenv('VISION_LLM_TIMEOUT', '10'))
            except ValueError:
                llm_timeout = 10
                debug_logger.log_info('AgentVisionTool', '无效的VISION_LLM_TIMEOUT，使用默认值10')
            
            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个智能判断助手，负责判断用户问题是否需要观察环境。'},
                    {'role': 'user', 'content': judge_prompt}
                ],
                'temperature': llm_temperature,
                'max_tokens': llm_max_tokens
            }
            
            debug_logger.log_info('AgentVisionTool', '发送LLM判断请求')
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=llm_timeout
            )
            
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                answer = result['choices'][0]['message']['content'].strip()
                # 更精确的判断：完全匹配"是"或以"是"开头
                # 注意：此判断逻辑仅适用于中文，国际化时需要修改
                needs_vision = (answer == '是' or answer.startswith('是，') or answer.startswith('是。'))
                
                debug_logger.log_info('AgentVisionTool', 'LLM判断完成', {
                    'query': user_query,
                    'answer': answer,
                    'needs_vision': needs_vision
                })
                
                return needs_vision
            else:
                debug_logger.log_info('AgentVisionTool', 'LLM响应无效，回退到关键词匹配')
                return self._fallback_to_keyword(user_query)
                
        except Exception as e:
            debug_logger.log_error('AgentVisionTool', f'LLM判断失败: {str(e)}', e)
            # 如果LLM调用失败，回退到关键词匹配
            return self._fallback_to_keyword(user_query)

    def _fallback_to_keyword(self, user_query: str) -> bool:
        """
        回退到关键词匹配（内部方法）
        
        Args:
            user_query: 用户查询
            
        Returns:
            是否需要使用视觉
        """
        debug_logger.log_info('AgentVisionTool', '使用关键词匹配作为后备方案')
        return self.should_use_vision_keyword(user_query)

    def should_use_vision_keyword(self, user_query: str) -> bool:
        """
        判断是否需要使用视觉工具（基于关键词快速判断）
        这是备用方法，当LLM不可用时使用

        Args:
            user_query: 用户查询

        Returns:
            是否需要使用视觉
        """
        debug_logger.log_module('AgentVisionTool', '使用关键词判断是否需要视觉', {
            'query_length': len(user_query)
        })
        
        # 快速关键词匹配
        query_lower = user_query.lower()
        for keyword in self.environment_keywords:
            if keyword in query_lower:
                debug_logger.log_info('AgentVisionTool', '检测到环境相关关键词', {
                    'keyword': keyword,
                    'query': user_query
                })
                return True
        
        debug_logger.log_info('AgentVisionTool', '未检测到环境相关关键词', {
            'query': user_query
        })
        return False

    def should_use_vision(self, user_query: str, use_llm: bool = True) -> bool:
        """
        判断是否需要使用视觉工具（智能判断）
        优先使用LLM进行智能判断，如果LLM不可用或禁用则使用关键词匹配

        Args:
            user_query: 用户查询
            use_llm: 是否使用LLM进行智能判断，默认为True

        Returns:
            是否需要使用视觉
        """
        if use_llm:
            return self.should_use_vision_llm(user_query)
        else:
            return self.should_use_vision_keyword(user_query)

    def get_vision_context(self, user_query: str) -> Optional[Dict[str, Any]]:
        """
        获取视觉上下文（环境描述）

        Args:
            user_query: 用户查询

        Returns:
            视觉上下文字典，包含环境描述和物体信息
        """
        debug_logger.log_module('AgentVisionTool', '开始获取视觉上下文', {
            'query': user_query
        })
        
        # 检查是否需要使用视觉
        if not self.should_use_vision(user_query):
            debug_logger.log_info('AgentVisionTool', '不需要使用视觉工具', {
                'reason': '未检测到环境相关查询'
            })
            return None
        
        # 获取当前激活的环境
        environment = self.db.get_active_environment()
        if not environment:
            debug_logger.log_info('AgentVisionTool', '没有激活的环境', {
                'suggestion': '请先创建并激活一个环境'
            })
            return None
        
        debug_logger.log_info('AgentVisionTool', '找到激活的环境', {
            'env_name': environment['name'],
            'env_uuid': (environment['uuid'][:8] + '...') if len(environment['uuid']) > 8 else environment['uuid']
        })
        
        # 获取环境中的物体
        objects = self.db.get_environment_objects(environment['uuid'], visible_only=True)
        
        debug_logger.log_info('AgentVisionTool', '获取环境物体', {
            'objects_count': len(objects)
        })
        
        # 构建视觉上下文
        vision_context = {
            'environment': environment,
            'objects': objects,
            'object_count': len(objects),
            'query': user_query,
            'timestamp': datetime.now().isoformat()
        }
        
        # 记录视觉工具使用
        objects_viewed = ', '.join([obj['name'] for obj in objects])
        context_text = self._format_vision_context(vision_context)
        
        self.db.log_vision_tool_usage(
            query=user_query,
            environment_uuid=environment['uuid'],
            objects_viewed=objects_viewed,
            context_provided=context_text[:500],  # 只保存前500字符
            triggered_by='auto'
        )
        
        debug_logger.log_info('AgentVisionTool', '视觉上下文获取完成', {
            'environment': environment['name'],
            'objects_count': len(objects),
            'context_length': len(context_text)
        })
        
        return vision_context

    def _format_vision_context(self, vision_context: Dict[str, Any]) -> str:
        """
        格式化视觉上下文为文本描述

        Args:
            vision_context: 视觉上下文字典

        Returns:
            格式化的文本描述
        """
        if not vision_context:
            return ""
        
        # 检查是否为域级别的上下文
        if vision_context.get('type') == 'domain':
            domain = vision_context['domain']
            current_env = vision_context.get('current_environment')
            
            context_parts = ["【智能体视觉感知 - 域级别】"]
            context_parts.append(f"\n所在域: {domain['name']}")
            if domain.get('description'):
                context_parts.append(f"\n域描述: {domain['description']}")
            if current_env:
                context_parts.append(f"\n当前具体位置: {current_env['name']}")
            
            # 获取域中的环境列表
            environments = self.db.get_domain_environments(domain['uuid'])
            if environments:
                env_names = [env['name'] for env in environments]
                context_parts.append(f"\n域包含的区域: {', '.join(env_names)}")
            
            context_parts.append("\n\n💡 请基于域级别的位置信息回答用户的问题。如需更详细信息，可询问用户具体位置。")
            
            return '\n'.join(context_parts)
        
        # 原有的环境级别上下文格式化
        environment = vision_context.get('environment')
        objects = vision_context.get('objects', [])
        
        if not environment:
            return ""
        
        context_parts = ["【智能体视觉感知】"]
        context_parts.append(f"\n环境名称: {environment['name']}")
        context_parts.append(f"\n整体描述: {environment['overall_description']}")
        
        # 添加感官细节
        if environment.get('atmosphere'):
            context_parts.append(f"氛围: {environment['atmosphere']}")
        if environment.get('lighting'):
            context_parts.append(f"光照: {environment['lighting']}")
        if environment.get('sounds'):
            context_parts.append(f"声音: {environment['sounds']}")
        if environment.get('smells'):
            context_parts.append(f"气味: {environment['smells']}")
        
        # 添加物体信息
        if objects:
            context_parts.append(f"\n可见物体（共{len(objects)}个）:")
            for obj in objects:
                obj_desc = f"\n  🔹 {obj['name']}"
                obj_desc += f"\n     描述: {obj['description']}"
                if obj.get('position'):
                    obj_desc += f"\n     位置: {obj['position']}"
                if obj.get('properties'):
                    obj_desc += f"\n     属性: {obj['properties']}"
                if obj.get('interaction_hints'):
                    obj_desc += f"\n     交互: {obj['interaction_hints']}"
                context_parts.append(obj_desc)
        else:
            context_parts.append("\n当前环境中没有可见物体。")
        
        context_parts.append("\n\n💡 请基于以上视觉感知信息回答用户的问题。")
        
        return '\n'.join(context_parts)

    def format_vision_prompt(self, vision_context: Dict[str, Any]) -> str:
        """
        将视觉上下文格式化为系统提示词

        Args:
            vision_context: 视觉上下文字典

        Returns:
            格式化的提示词
        """
        return self._format_vision_context(vision_context)

    def get_vision_summary(self, vision_context: Dict[str, Any]) -> str:
        """
        获取视觉上下文的简要摘要（用于显示）

        Args:
            vision_context: 视觉上下文字典

        Returns:
            简要摘要
        """
        if not vision_context:
            return "未获取到视觉信息"
        
        # 检查是否为域级别的上下文
        if vision_context.get('type') == 'domain':
            domain = vision_context['domain']
            current_env = vision_context.get('current_environment')
            summary = f"👁️ [视觉感知-域] 域: {domain['name']}"
            if current_env:
                summary += f" | 位置: {current_env['name']}"
            return summary
        
        # 原有的环境级别摘要
        env = vision_context.get('environment')
        obj_count = vision_context.get('object_count', 0)
        
        if not env:
            return "未获取到视觉信息"
        
        summary = f"👁️ [视觉感知] 环境: {env['name']}"
        if obj_count > 0:
            summary += f" | 可见物体: {obj_count}个"
        
        return summary

    def create_default_environment(self) -> str:
        """
        创建默认环境（用于初始化或测试）

        Returns:
            环境UUID
        """
        debug_logger.log_module('AgentVisionTool', '创建默认环境')
        
        env_uuid = self.db.create_environment(
            name="小可的房间",
            overall_description="这是一个温馨舒适的学生卧室，约15平方米。墙壁刷成淡粉色，地板铺着浅色木地板。房间整洁有序，充满学习的氛围。",
            atmosphere="温馨、宁静、充满书香气息",
            lighting="柔和的自然光从窗户洒入，桌上的台灯散发着暖黄色的光",
            sounds="偶尔能听到窗外鸟鸣和微风拂过树叶的沙沙声",
            smells="空气中弥漫着淡淡的书香和薰衣草香薰的味道"
        )
        
        # 设置为激活环境
        self.db.set_active_environment(env_uuid)
        
        # 添加一些默认物体
        default_objects = [
            {
                "name": "书桌",
                "description": "一张简约的白色书桌，约120cm宽，上面摆放着各种学习用品",
                "position": "靠窗的位置",
                "properties": "材质: 实木, 颜色: 白色, 状态: 整洁",
                "interaction_hints": "可以在这里学习、写作业、看书",
                "priority": 90
            },
            {
                "name": "书架",
                "description": "一个四层的白色书架，摆满了各类书籍，尤其是历史类书籍特别多",
                "position": "书桌右侧的墙边",
                "properties": "材质: 木质, 层数: 4层, 书籍数量: 约100本",
                "interaction_hints": "可以挑选书籍阅读，历史类书籍最多",
                "priority": 85
            },
            {
                "name": "床",
                "description": "一张单人床，铺着淡粉色的床单和被套，上面放着几个可爱的抱枕",
                "position": "房间左侧靠墙",
                "properties": "大小: 单人床(1.2m), 颜色: 粉色系, 状态: 整理好的",
                "interaction_hints": "可以休息、睡觉",
                "priority": 80
            },
            {
                "name": "台灯",
                "description": "一盏护眼台灯，设计简洁，可以调节亮度和色温",
                "position": "书桌右上角",
                "properties": "品牌: 明基, 类型: LED护眼灯, 状态: 关闭",
                "interaction_hints": "可以开启用于学习照明",
                "priority": 70
            },
            {
                "name": "笔记本电脑",
                "description": "一台轻薄的笔记本电脑，银色外壳，通常用于查资料和学习",
                "position": "书桌中央",
                "properties": "品牌: 华为, 颜色: 银色, 状态: 合上的",
                "interaction_hints": "可以打开用于学习、查资料",
                "priority": 85
            },
            {
                "name": "窗户",
                "description": "一扇宽大的窗户，透过窗户可以看到外面的树木和天空",
                "position": "书桌后方",
                "properties": "类型: 推拉窗, 尺寸: 大型, 状态: 半开",
                "interaction_hints": "可以打开通风，欣赏外面的景色",
                "priority": 75
            },
            {
                "name": "挂钟",
                "description": "一个圆形的挂钟，简约的设计，静音机芯",
                "position": "门的上方墙壁",
                "properties": "类型: 石英钟, 颜色: 白色, 特点: 静音",
                "interaction_hints": "可以查看时间",
                "priority": 60
            }
        ]
        
        for obj_data in default_objects:
            self.db.add_environment_object(
                environment_uuid=env_uuid,
                name=obj_data['name'],
                description=obj_data['description'],
                position=obj_data.get('position', ''),
                properties=obj_data.get('properties', ''),
                interaction_hints=obj_data.get('interaction_hints', ''),
                priority=obj_data.get('priority', 50)
            )
        
        debug_logger.log_info('AgentVisionTool', '默认环境创建完成', {
            'env_uuid': (env_uuid[:8] + '...') if len(env_uuid) > 8 else env_uuid,
            'objects_count': len(default_objects)
        })
        
        print(f"✓ 默认环境创建完成: 小可的房间（{len(default_objects)}个物体）")
        
        return env_uuid

    def detect_environment_switch_intent(self, user_query: str) -> Optional[Dict[str, Any]]:
        """
        检测用户是否有切换环境的意图

        Args:
            user_query: 用户查询

        Returns:
            如果检测到切换意图，返回包含目标环境等信息的字典，否则返回None
        """
        debug_logger.log_module('AgentVisionTool', '检测环境切换意图', {
            'query': user_query
        })

        # 环境切换关键词
        switch_keywords = [
            '去', '走', '移动', '前往', '过去', '进入', '离开', '出去',
            '回到', '返回', '切换', '换到', '转移'
        ]

        query_lower = user_query.lower()
        has_switch_keyword = any(keyword in query_lower for keyword in switch_keywords)

        if not has_switch_keyword:
            debug_logger.log_info('AgentVisionTool', '未检测到切换关键词')
            return None

        # 获取当前环境
        current_env = self.db.get_active_environment()
        if not current_env:
            debug_logger.log_info('AgentVisionTool', '没有当前激活的环境')
            return None

        # 获取所有连通的环境
        connected_envs = self.db.get_connected_environments(current_env['uuid'])
        if not connected_envs:
            debug_logger.log_info('AgentVisionTool', '当前环境没有连通的环境')
            return None

        # 尝试匹配环境名称
        matched_env = None
        for env in connected_envs:
            if env['name'] in user_query:
                matched_env = env
                break

        if matched_env:
            debug_logger.log_info('AgentVisionTool', '检测到环境切换意图', {
                'from': current_env['name'],
                'to': matched_env['name']
            })
            return {
                'intent': 'switch_environment',
                'from_env': current_env,
                'to_env': matched_env,
                'can_switch': True
            }

        debug_logger.log_info('AgentVisionTool', '未匹配到目标环境')
        return None

    def switch_environment(self, to_env_uuid: str) -> bool:
        """
        切换到指定环境

        Args:
            to_env_uuid: 目标环境UUID

        Returns:
            是否切换成功
        """
        debug_logger.log_module('AgentVisionTool', '执行环境切换', {
            'to_env_uuid': (to_env_uuid[:8] + '...') if len(to_env_uuid) > 8 else to_env_uuid
        })

        current_env = self.db.get_active_environment()
        if not current_env:
            debug_logger.log_info('AgentVisionTool', '没有当前激活的环境')
            return False

        # 检查是否可以切换（是否连通）
        if not self.db.can_move_to_environment(current_env['uuid'], to_env_uuid):
            debug_logger.log_info('AgentVisionTool', '不能切换到目标环境', {
                'reason': '环境不连通'
            })
            return False

        # 执行切换
        success = self.db.set_active_environment(to_env_uuid)
        if success:
            to_env = self.db.get_environment(to_env_uuid)
            debug_logger.log_info('AgentVisionTool', '环境切换成功', {
                'from': current_env['name'],
                'to': to_env['name'] if to_env else 'Unknown'
            })
            print(f"✓ 环境已切换: {current_env['name']} → {to_env['name'] if to_env else 'Unknown'}")
        else:
            debug_logger.log_info('AgentVisionTool', '环境切换失败')

        return success

    def get_available_environments_for_switch(self) -> List[Dict[str, Any]]:
        """
        获取可以切换到的环境列表

        Returns:
            可切换环境列表
        """
        current_env = self.db.get_active_environment()
        if not current_env:
            return []

        return self.db.get_connected_environments(current_env['uuid'])

    # ==================== 环境域相关方法 ====================

    def get_current_domain(self) -> Optional[Dict[str, Any]]:
        """
        获取当前环境所属的域
        如果当前环境属于多个域，返回第一个域

        Returns:
            域信息字典或None
        """
        current_env = self.db.get_active_environment()
        if not current_env:
            debug_logger.log_info('AgentVisionTool', '没有当前激活的环境')
            return None

        domains = self.db.get_environment_domains(current_env['uuid'])
        if domains:
            debug_logger.log_info('AgentVisionTool', '找到当前环境所属的域', {
                'domain_name': domains[0]['name'],
                'domain_count': len(domains)
            })
            return domains[0]

        debug_logger.log_info('AgentVisionTool', '当前环境不属于任何域')
        return None

    def get_domain_description(self, domain_uuid: str, use_default_env: bool = False) -> str:
        """
        获取域的描述信息
        
        Args:
            domain_uuid: 域UUID
            use_default_env: 是否使用默认环境的详细描述

        Returns:
            域的描述文本
        """
        domain = self.db.get_domain(domain_uuid)
        if not domain:
            return ""

        # 获取域中的环境列表
        environments = self.db.get_domain_environments(domain_uuid)
        
        if use_default_env and domain['default_environment_uuid']:
            # 使用默认环境的详细描述
            default_env = self.db.get_environment(domain['default_environment_uuid'])
            if default_env:
                desc = f"【{domain['name']}】\n"
                desc += f"{domain['description']}\n" if domain['description'] else ""
                desc += f"当前位置: {default_env['name']}\n"
                desc += f"{default_env['overall_description']}"
                return desc
        
        # 使用域级别的概括描述
        desc = f"【{domain['name']}】\n"
        desc += f"{domain['description']}\n" if domain['description'] else ""
        
        if environments:
            env_names = [env['name'] for env in environments]
            desc += f"包含环境: {', '.join(env_names)}"
        
        return desc

    def get_vision_context_with_precision(self, user_query: str, 
                                          high_precision: bool = False) -> Optional[Dict[str, Any]]:
        """
        根据精度要求获取视觉上下文
        
        Args:
            user_query: 用户查询
            high_precision: 是否需要高精度（具体环境）描述
                          False: 返回域级别的描述
                          True: 返回具体环境的详细描述

        Returns:
            视觉上下文字典，包含环境或域的描述信息
        """
        debug_logger.log_module('AgentVisionTool', '根据精度获取视觉上下文', {
            'query': user_query,
            'high_precision': high_precision
        })
        
        # 检查是否需要使用视觉
        if not self.should_use_vision(user_query):
            debug_logger.log_info('AgentVisionTool', '不需要使用视觉工具')
            return None
        
        # 获取当前激活的环境
        current_env = self.db.get_active_environment()
        if not current_env:
            debug_logger.log_info('AgentVisionTool', '没有激活的环境')
            return None
        
        # 检查当前环境是否属于某个域
        domains = self.db.get_environment_domains(current_env['uuid'])
        
        if not high_precision and domains:
            # 低精度模式：返回域级别的描述
            domain = domains[0]  # 使用第一个域
            domain_desc = self.get_domain_description(domain['uuid'], use_default_env=False)
            
            vision_context = {
                'type': 'domain',
                'domain': domain,
                'current_environment': current_env,
                'description': domain_desc,
                'query': user_query,
                'timestamp': datetime.now().isoformat()
            }
            
            debug_logger.log_info('AgentVisionTool', '返回域级别视觉上下文', {
                'domain_name': domain['name']
            })
            
            return vision_context
        else:
            # 高精度模式或不属于域：返回具体环境的详细描述
            return self.get_vision_context(user_query)

    def detect_precision_requirement(self, user_query: str) -> bool:
        """
        检测用户查询是否需要高精度的环境信息
        
        Args:
            user_query: 用户查询

        Returns:
            是否需要高精度（True=需要具体环境，False=域级别即可）
        """
        # 高精度关键词（需要具体环境描述）
        high_precision_keywords = [
            '具体', '详细', '什么东西', '有什么', '有哪些', '看到',
            '周围', '附近', '房间', '屋子', '物体', '物品'
        ]
        
        query_lower = user_query.lower()
        for keyword in high_precision_keywords:
            if keyword in query_lower:
                debug_logger.log_info('AgentVisionTool', '检测到高精度需求', {
                    'keyword': keyword
                })
                return True
        
        debug_logger.log_info('AgentVisionTool', '低精度需求（域级别）')
        return False

    def switch_to_domain(self, domain_uuid: str) -> bool:
        """
        切换到指定域（会切换到该域的默认环境）

        Args:
            domain_uuid: 目标域UUID

        Returns:
            是否切换成功
        """
        # 安全截取UUID用于日志显示
        uuid_display = domain_uuid[:8] + '...' if len(domain_uuid) > 8 else domain_uuid
        debug_logger.log_module('AgentVisionTool', '切换到域', {
            'domain_uuid': uuid_display
        })

        domain = self.db.get_domain(domain_uuid)
        if not domain:
            debug_logger.log_info('AgentVisionTool', '域不存在')
            return False

        # 如果域有默认环境，切换到默认环境
        if domain['default_environment_uuid']:
            default_env = self.db.get_environment(domain['default_environment_uuid'])
            if default_env:
                success = self.db.set_active_environment(domain['default_environment_uuid'])
                if success:
                    debug_logger.log_info('AgentVisionTool', '已切换到域的默认环境', {
                        'domain': domain['name'],
                        'default_env': default_env['name']
                    })
                    print(f"✓ 已切换到域: {domain['name']} (默认位置: {default_env['name']})")
                return success
            else:
                debug_logger.log_info('AgentVisionTool', '域的默认环境不存在')
                return False
        else:
            # 如果没有设置默认环境，切换到域中的第一个环境
            environments = self.db.get_domain_environments(domain_uuid)
            if environments:
                first_env = environments[0]
                success = self.db.set_active_environment(first_env['uuid'])
                if success:
                    debug_logger.log_info('AgentVisionTool', '已切换到域的第一个环境', {
                        'domain': domain['name'],
                        'env': first_env['name']
                    })
                    print(f"✓ 已切换到域: {domain['name']} (位置: {first_env['name']})")
                return success
            else:
                debug_logger.log_info('AgentVisionTool', '域中没有环境')
                return False

    def detect_domain_switch_intent(self, user_query: str) -> Optional[Dict[str, Any]]:
        """
        检测用户是否有切换到域的意图

        Args:
            user_query: 用户查询

        Returns:
            如果检测到切换意图，返回包含目标域等信息的字典，否则返回None
        """
        debug_logger.log_module('AgentVisionTool', '检测域切换意图', {
            'query': user_query
        })

        # 域切换关键词
        switch_keywords = [
            '去', '走', '移动', '前往', '过去', '进入', '离开', '出去',
            '回到', '返回', '切换', '换到', '转移'
        ]

        query_lower = user_query.lower()
        has_switch_keyword = any(keyword in query_lower for keyword in switch_keywords)

        if not has_switch_keyword:
            debug_logger.log_info('AgentVisionTool', '未检测到切换关键词')
            return None

        # 获取所有域
        all_domains = self.db.get_all_domains()
        if not all_domains:
            debug_logger.log_info('AgentVisionTool', '没有已定义的域')
            return None

        # 尝试匹配域名称
        matched_domain = None
        for domain in all_domains:
            if domain['name'] in user_query:
                matched_domain = domain
                break

        if matched_domain:
            current_env = self.db.get_active_environment()
            debug_logger.log_info('AgentVisionTool', '检测到域切换意图', {
                'from_env': current_env['name'] if current_env else 'None',
                'to_domain': matched_domain['name']
            })
            return {
                'intent': 'switch_domain',
                'from_env': current_env,
                'to_domain': matched_domain,
                'can_switch': True
            }

        debug_logger.log_info('AgentVisionTool', '未匹配到目标域')
        return None


# 测试代码
if __name__ == '__main__':
    print("=" * 60)
    print("智能体视觉工具测试")
    print("=" * 60)
    
    # 创建视觉工具实例
    vision_tool = AgentVisionTool()
    
    # 创建默认环境
    print("\n创建默认环境:")
    env_uuid = vision_tool.create_default_environment()
    
    # 测试视觉工具
    print("\n" + "=" * 60)
    print("测试视觉工具")
    print("=" * 60)
    
    test_queries = [
        "周围有什么？",
        "我能看到什么？",
        "房间里有哪些东西？",
        "你在哪？",  # 应该触发视觉（需要环境信息）
        "你在哪里？",  # 应该触发视觉（需要环境信息）
        "今天天气怎么样？",  # 不应该触发视觉
        "帮我讲个历史故事",  # 不应该触发视觉
    ]
    
    for query in test_queries:
        print(f"\n测试查询: {query}")
        should_use = vision_tool.should_use_vision(query)
        print(f"  是否使用视觉: {'是' if should_use else '否'}")
        
        if should_use:
            vision_context = vision_tool.get_vision_context(query)
            if vision_context:
                summary = vision_tool.get_vision_summary(vision_context)
                print(f"  {summary}")
                print(f"\n  视觉上下文预览:")
                prompt = vision_tool.format_vision_prompt(vision_context)
                print(f"  {prompt[:300]}...")
    
    print("\n" + "=" * 60)
    print("✓ 测试完成")
    print("=" * 60)
