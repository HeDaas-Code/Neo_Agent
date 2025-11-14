"""
知识库管理模块
负责从对话中提取和管理知识性记忆
"""

import os
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import requests

load_dotenv()


class KnowledgeBase:
    """
    知识库管理器
    每5轮对话提取一次知识，形成结构化的知识性记忆
    """

    def __init__(self,
                 knowledge_file: str = None,
                 api_key: str = None,
                 api_url: str = None,
                 model_name: str = None):
        """
        初始化知识库管理器

        Args:
            knowledge_file: 知识库文件路径（默认knowledge_base.json）
            api_key: API密钥
            api_url: API地址
            model_name: 模型名称
        """
        # 文件路径配置
        self.knowledge_file = knowledge_file or 'knowledge_base.json'

        # API配置（用于提取知识）
        self.api_key = api_key or os.getenv('SILICONFLOW_API_KEY')
        self.api_url = api_url or os.getenv('SILICONFLOW_API_URL', 'https://api.siliconflow.cn/v1/chat/completions')
        self.model_name = model_name or os.getenv('MODEL_NAME', 'Qwen/Qwen2.5-7B-Instruct')

        # 知识数据
        self.knowledge_items: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}

        # 加载现有知识库
        self.load_knowledge()

    def load_knowledge(self):
        """
        从文件加载知识库
        """
        try:
            if os.path.exists(self.knowledge_file):
                with open(self.knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.knowledge_items = data.get('knowledge_items', [])
                    self.metadata = data.get('metadata', {})
                    print(f"✓ 成功加载知识库: {len(self.knowledge_items)} 条知识")
            else:
                print("○ 未找到知识库文件，创建新的知识库")
                self.knowledge_items = []
                self.metadata = {
                    'created_at': datetime.now().isoformat(),
                    'total_knowledge': 0,
                    'last_extraction': None
                }
        except Exception as e:
            print(f"✗ 加载知识库时出错: {e}")
            self.knowledge_items = []
            self.metadata = {}

    def save_knowledge(self):
        """
        保存知识库到文件
        """
        try:
            data = {
                'knowledge_items': self.knowledge_items,
                'metadata': self.metadata,
                'last_updated': datetime.now().isoformat()
            }

            with open(self.knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 知识库已保存: {len(self.knowledge_items)} 条知识")
        except Exception as e:
            print(f"✗ 保存知识库时出错: {e}")

    def extract_knowledge(self, messages: List[Dict[str, Any]]) -> Optional[List[Dict[str, Any]]]:
        """
        从最近的对话中提取知识

        Args:
            messages: 最近5轮的对话消息列表

        Returns:
            提取的知识列表，每个知识包含标题、内容、类型等
        """
        try:
            # 构建对话文本
            conversation_text = ""
            for msg in messages:
                role_name = "用户" if msg['role'] == 'user' else "助手"
                conversation_text += f"{role_name}: {msg['content']}\n"

            # 构建知识提取请求
            extraction_prompt = f"""请从以下对话中提取用户提到的关键信息和知识点。

要求：
1. 识别用户分享的事实性信息、个人信息、偏好、经历等
2. 每个知识点包含：
   - 标题（简短概括，10字以内）
   - 内容（详细描述知识点）
   - 类型（如：个人信息、偏好、事实、经历、观点等）
3. 只提取明确的、有价值的信息，避免重复和模糊的内容
4. 如果没有值得记录的知识，返回空列表
5. 以JSON格式返回，格式如下：
[
  {{
    "title": "知识标题",
    "content": "知识详细内容",
    "type": "知识类型",
    "source": "来源概述"
  }}
]

对话内容：
{conversation_text}

请提取知识点（只返回JSON数组，不要其他文字）："""

            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }

            payload = {
                'model': self.model_name,
                'messages': [
                    {'role': 'system', 'content': '你是一个专业的知识提取助手，擅长从对话中识别和提取有价值的信息。你只返回JSON格式的数据，不添加任何解释。'},
                    {'role': 'user', 'content': extraction_prompt}
                ],
                'temperature': 0.3,
                'max_tokens': 1000,
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

            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content'].strip()

                # 尝试解析JSON
                # 清理可能的markdown代码块标记
                if content.startswith('```'):
                    content = content.split('```')[1]
                    if content.startswith('json'):
                        content = content[4:]
                content = content.strip()

                try:
                    knowledge_list = json.loads(content)
                    if isinstance(knowledge_list, list):
                        return knowledge_list
                    else:
                        print(f"✗ 返回的不是列表格式: {type(knowledge_list)}")
                        return None
                except json.JSONDecodeError as e:
                    print(f"✗ JSON解析失败: {e}")
                    print(f"原始内容: {content[:200]}...")
                    return None
            else:
                print("✗ 未能获取有效的知识提取结果")
                return None

        except Exception as e:
            print(f"✗ 提取知识时出错: {e}")
            return None

    def add_knowledge(self, knowledge_data: Dict[str, Any], source_messages: List[Dict[str, Any]]) -> str:
        """
        添加一条知识到知识库

        Args:
            knowledge_data: 知识数据（包含title, content, type等）
            source_messages: 来源消息列表

        Returns:
            知识的UUID
        """
        knowledge_uuid = str(uuid.uuid4())

        knowledge_item = {
            'uuid': knowledge_uuid,
            'title': knowledge_data.get('title', '未命名知识'),
            'content': knowledge_data.get('content', ''),
            'type': knowledge_data.get('type', '其他'),
            'source': knowledge_data.get('source', '对话记录'),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'source_time_range': {
                'start': source_messages[0].get('timestamp', '') if source_messages else '',
                'end': source_messages[-1].get('timestamp', '') if source_messages else ''
            },
            'tags': self._generate_tags(knowledge_data)
        }

        self.knowledge_items.append(knowledge_item)
        self.metadata['total_knowledge'] = len(self.knowledge_items)
        self.metadata['last_extraction'] = datetime.now().isoformat()

        return knowledge_uuid

    def _generate_tags(self, knowledge_data: Dict[str, Any]) -> List[str]:
        """
        根据知识数据生成标签

        Args:
            knowledge_data: 知识数据

        Returns:
            标签列表
        """
        tags = []

        # 根据类型添加标签
        knowledge_type = knowledge_data.get('type', '')
        if knowledge_type:
            tags.append(knowledge_type)

        # 可以根据内容添加更多标签
        # 这里简化处理

        return tags

    def search_knowledge(self, keyword: str = None, knowledge_type: str = None) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            keyword: 关键词
            knowledge_type: 知识类型

        Returns:
            匹配的知识列表
        """
        results = self.knowledge_items.copy()

        if keyword:
            keyword_lower = keyword.lower()
            results = [
                k for k in results
                if keyword_lower in k.get('title', '').lower() or
                   keyword_lower in k.get('content', '').lower()
            ]

        if knowledge_type:
            results = [k for k in results if k.get('type', '') == knowledge_type]

        return results

    def get_all_knowledge(self) -> List[Dict[str, Any]]:
        """
        获取所有知识

        Returns:
            知识列表
        """
        return self.knowledge_items

    def get_knowledge_by_uuid(self, knowledge_uuid: str) -> Optional[Dict[str, Any]]:
        """
        根据UUID获取知识

        Args:
            knowledge_uuid: 知识UUID

        Returns:
            知识项，如果不存在返回None
        """
        for item in self.knowledge_items:
            if item.get('uuid') == knowledge_uuid:
                return item
        return None

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取知识库统计信息

        Returns:
            统计信息字典
        """
        # 统计各类型知识数量
        type_counts = {}
        for item in self.knowledge_items:
            item_type = item.get('type', '其他')
            type_counts[item_type] = type_counts.get(item_type, 0) + 1

        return {
            'total_knowledge': len(self.knowledge_items),
            'type_distribution': type_counts,
            'last_extraction': self.metadata.get('last_extraction', 'Never'),
            'created_at': self.metadata.get('created_at', 'Unknown'),
            'knowledge_file': self.knowledge_file
        }

    def clear_knowledge(self):
        """
        清空知识库
        """
        self.knowledge_items = []
        self.metadata = {
            'created_at': datetime.now().isoformat(),
            'total_knowledge': 0,
            'last_extraction': None
        }
        self.save_knowledge()
        print("✓ 知识库已清空")

    def delete_knowledge(self, knowledge_uuid: str) -> bool:
        """
        删除指定的知识

        Args:
            knowledge_uuid: 知识UUID

        Returns:
            是否删除成功
        """
        for i, item in enumerate(self.knowledge_items):
            if item.get('uuid') == knowledge_uuid:
                del self.knowledge_items[i]
                self.metadata['total_knowledge'] = len(self.knowledge_items)
                self.save_knowledge()
                print(f"✓ 已删除知识: {item.get('title', '')}")
                return True
        return False


if __name__ == '__main__':
    print("=" * 60)
    print("知识库管理器测试")
    print("=" * 60)

    kb = KnowledgeBase()

    print("\n当前知识库统计:")
    stats = kb.get_statistics()
    print(f"总知识数: {stats['total_knowledge']}")
    print(f"类型分布: {stats['type_distribution']}")

    if kb.knowledge_items:
        print("\n知识列表:")
        for i, knowledge in enumerate(kb.knowledge_items, 1):
            print(f"{i}. [{knowledge['type']}] {knowledge['title']}")
            print(f"   内容: {knowledge['content'][:50]}...")
            print(f"   UUID: {knowledge['uuid']}")

