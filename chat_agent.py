"""
智能对话代理模块
基于LangChain实现的连续对话智能体，支持角色扮演和长效记忆
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv
import requests

# 加载环境变量
load_dotenv()


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

            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=30
            )

            response.raise_for_status()
            result = response.json()

            # 提取回复内容
            if 'choices' in result and len(result['choices']) > 0:
                return result['choices'][0]['message']['content']
            else:
                return "抱歉，我没有收到有效的回复。"

        except requests.exceptions.RequestException as e:
            print(f"API请求错误: {e}")
            return f"抱歉，网络连接出现问题: {str(e)}"
        except Exception as e:
            print(f"处理回复时出错: {e}")
            return f"抱歉，处理回复时出现错误: {str(e)}"


class ChatAgent:
    """
    聊天代理主类
    整合记忆管理、角色设定和LLM调用
    """

    def __init__(self):
        """
        初始化聊天代理
        """
        self.memory_manager = MemoryManager()
        self.character = CharacterProfile()
        self.llm = SiliconFlowLLM()
        self.system_prompt = self.character.get_system_prompt()

        print(f"聊天代理初始化完成，当前角色: {self.character.name}")
        print(f"记忆系统已加载: {len(self.memory_manager.messages)} 条历史消息")

    def chat(self, user_input: str) -> str:
        """
        处理用户输入并生成回复

        Args:
            user_input: 用户输入的消息

        Returns:
            AI角色的回复
        """
        # 添加用户消息到记忆
        self.memory_manager.add_message('user', user_input)

        # 构建消息列表
        messages = [
            {'role': 'system', 'content': self.system_prompt}
        ]

        # 添加历史对话（最近10条）
        recent_messages = self.memory_manager.get_recent_messages(count=10)
        messages.extend(recent_messages)

        # 调用LLM获取回复
        response = self.llm.chat(messages)

        # 添加助手回复到记忆
        self.memory_manager.add_message('assistant', response)

        # 保存记忆
        self.memory_manager.save_memory()

        return response

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
        self.memory_manager.clear_memory()

    def get_conversation_history(self, count: int = None) -> List[Dict[str, Any]]:
        """
        获取对话历史

        Args:
            count: 要获取的消息数量，None表示全部

        Returns:
            对话历史列表
        """
        if count is None:
            return self.memory_manager.messages
        else:
            return self.memory_manager.messages[-count:] if len(self.memory_manager.messages) > count else self.memory_manager.messages


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

