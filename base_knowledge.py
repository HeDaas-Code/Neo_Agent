"""
基础知识库模块
存储智能体的核心基础知识，这些知识：
1. 拥有最高优先级（100%正确）
2. 不可被覆盖或更改
3. 即使与现实相悖也以该知识为准
4. 不以上下文形式存在，而是直接嵌入到提示词中
"""

import os
import json
from typing import Dict, List, Any
from datetime import datetime


class BaseKnowledge:
    """
    基础知识库管理器
    管理智能体的核心基础知识，这些知识具有绝对权威性
    """

    def __init__(self, base_knowledge_file: str = None):
        """
        初始化基础知识库

        Args:
            base_knowledge_file: 基础知识库文件路径（默认base_knowledge.json）
        """
        self.base_knowledge_file = base_knowledge_file or 'base_knowledge.json'

        # 基础知识字典：{实体名��: 知识内容}
        self.base_facts: Dict[str, Dict[str, Any]] = {}

        # 加载基础知识库
        self.load_base_knowledge()

        # 如果没有基础知识，初始化默认知识
        if not self.base_facts:
            self._initialize_default_knowledge()

    def _initialize_default_knowledge(self):
        """
        初始化默认的基础知识
        """
        print("○ 初始化默认基础知识...")

        # 添加默认知识：HeDaas是一个高校
        self.add_base_fact(
            entity_name="HeDaas",
            fact_content="HeDaas是一个高校",
            category="机构类型",
            description="HeDaas的基本定义",
            immutable=True
        )

        self.save_base_knowledge()
        print("✓ 默认基础知识已初始化")

    def load_base_knowledge(self):
        """
        从文件加载基础知识库
        """
        try:
            if os.path.exists(self.base_knowledge_file):
                with open(self.base_knowledge_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.base_facts = data.get('base_facts', {})
                    print(f"✓ 成功加载基础知识库: {len(self.base_facts)} 条基础事实")
            else:
                print("○ 未找到基础知识库文件，将创建新的基础知识库")
                self.base_facts = {}
        except Exception as e:
            print(f"✗ 加载基础知识库时出错: {e}")
            self.base_facts = {}

    def save_base_knowledge(self):
        """
        保存基础知识库到文件
        """
        try:
            data = {
                'base_facts': self.base_facts,
                'metadata': {
                    'total_facts': len(self.base_facts),
                    'last_updated': datetime.now().isoformat(),
                    'version': '1.0',
                    'description': '基础知识库 - 存储最高优先级的不可更改事实'
                }
            }

            with open(self.base_knowledge_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✓ 基础知识库已保存: {len(self.base_facts)} 条基础事实")
        except Exception as e:
            print(f"✗ 保存基础知识库时出错: {e}")

    def add_base_fact(self,
                      entity_name: str,
                      fact_content: str,
                      category: str = "通用",
                      description: str = "",
                      immutable: bool = True) -> bool:
        """
        添加一条基础事实到基础知识库

        Args:
            entity_name: 实体名称（如"HeDaas"）
            fact_content: 事实内容（如"HeDaas是一个高校"）
            category: 分类（如"机构类型"、"定义"等）
            description: 描述说明
            immutable: 是否不可变（默认True，基础知识应该不可变）

        Returns:
            是否添加成功
        """
        try:
            # 标准化实体名称
            normalized_name = entity_name.strip()

            # 检查是否已存在
            if normalized_name in self.base_facts:
                print(f"⚠ 基础事实已存在: {normalized_name}")
                print(f"  现有内容: {self.base_facts[normalized_name]['content']}")
                print(f"  → 基础知识不可覆盖，保持原有内容")
                return False

            # 添加基础事实
            self.base_facts[normalized_name] = {
                'entity_name': entity_name,
                'content': fact_content,
                'category': category,
                'description': description,
                'immutable': immutable,
                'priority': 100,  # 最高优先级
                'confidence': 1.0,  # 100%置信度
                'created_at': datetime.now().isoformat()
            }

            print(f"✓ 已添加基础事实: {entity_name} -> {fact_content}")
            self.save_base_knowledge()
            return True

        except Exception as e:
            print(f"✗ 添加基础事实时出错: {e}")
            return False

    def get_base_fact(self, entity_name: str) -> Dict[str, Any] | None:
        """
        获取指定实体的基础事实（支持不区分大小写的查找）

        Args:
            entity_name: 实体名称

        Returns:
            基础事实字典，如果不存在返回None
        """
        # 首先尝试精确匹配
        normalized_name = entity_name.strip()
        if normalized_name in self.base_facts:
            return self.base_facts[normalized_name]

        # 如果精确匹配失败，尝试不区分大小写的匹配
        lower_name = normalized_name.lower()
        for key, value in self.base_facts.items():
            if key.lower() == lower_name:
                return value

        return None

    def check_conflict_with_base(self, entity_name: str, new_content: str) -> bool:
        """
        检查新知识是否与基础知识冲突

        Args:
            entity_name: 实体名称
            new_content: 新的知识内容

        Returns:
            True表示存在冲突，False表示无冲突
        """
        normalized_name = entity_name.strip()

        if normalized_name not in self.base_facts:
            return False

        base_fact = self.base_facts[normalized_name]

        # 如果新内容与基础事实不同，则存在冲突
        if new_content.strip() != base_fact['content'].strip():
            print(f"⚠ 检测到与基础知识冲突:")
            print(f"  实体: {entity_name}")
            print(f"  基础知识: {base_fact['content']}")
            print(f"  新知识: {new_content}")
            print(f"  → 基础知识优先级最高，将保持基础知识不变")
            return True

        return False

    def get_all_base_facts(self) -> List[Dict[str, Any]]:
        """
        获取所有基础事实

        Returns:
            基础事实列表
        """
        return list(self.base_facts.values())

    def generate_base_knowledge_prompt(self) -> str:
        """
        生成用于嵌入提示词的基础知识文本
        这些知识将直接嵌入到系统提示词中，确保AI始终遵循

        Returns:
            基础知识提示词文本
        """
        if not self.base_facts:
            return ""

        prompt_parts = [
            "\n【核心基础知识 - 最高优先级】",
            "以下是你必须遵守的核心基础知识，这些知识具有绝对权威性：",
            "- 优先级：100%（最高）",
            "- 准确性：100%（绝对正确）",
            "- 即使与其他信息相悖，也必须以这些基础知识为准",
            ""
        ]

        # 按分类组织基础知识
        by_category = {}
        for fact in self.base_facts.values():
            category = fact.get('category', '通用')
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(fact)

        # 生成每个分类的知识
        for category, facts in by_category.items():
            prompt_parts.append(f"[{category}]")
            for fact in facts:
                prompt_parts.append(f"• {fact['content']}")
                if fact.get('description'):
                    prompt_parts.append(f"  说明: {fact['description']}")
            prompt_parts.append("")

        prompt_parts.append("请在所有回答中严格遵循以上基础知识。")
        prompt_parts.append("=" * 60)

        return "\n".join(prompt_parts)

    def get_statistics(self) -> Dict[str, Any]:
        """
        获取基础知识库统计信息

        Returns:
            统计信息字典
        """
        # 按分类统计
        by_category = {}
        for fact in self.base_facts.values():
            category = fact.get('category', '通用')
            by_category[category] = by_category.get(category, 0) + 1

        return {
            'total_facts': len(self.base_facts),
            'category_distribution': by_category,
            'file_path': self.base_knowledge_file,
            'all_immutable': all(f.get('immutable', True) for f in self.base_facts.values())
        }

    def remove_base_fact(self, entity_name: str) -> bool:
        """
        删除基础事实（谨慎使用，基础知识一般不应删除）

        Args:
            entity_name: 实体名称

        Returns:
            是否删除成功
        """
        normalized_name = entity_name.strip()

        if normalized_name in self.base_facts:
            fact = self.base_facts[normalized_name]

            # 检查是否不可变
            if fact.get('immutable', True):
                print(f"⚠ 该基础事实被标记为不可变，不能删除: {entity_name}")
                return False

            del self.base_facts[normalized_name]
            self.save_base_knowledge()
            print(f"✓ 已删除基础事实: {entity_name}")
            return True
        else:
            print(f"✗ 基础事实不存在: {entity_name}")
            return False


if __name__ == '__main__':
    print("=" * 60)
    print("基础知识库测试")
    print("=" * 60)

    # 创建基础知识库实例
    base_kb = BaseKnowledge()

    # 显示统计信息
    print("\n基础知识库统计:")
    stats = base_kb.get_statistics()
    print(f"总事实数: {stats['total_facts']}")
    print(f"分类分布: {stats['category_distribution']}")
    print(f"全部不可变: {stats['all_immutable']}")

    # 显示所有基础事实
    print("\n所有基础事实:")
    for fact in base_kb.get_all_base_facts():
        print(f"• {fact['entity_name']}: {fact['content']}")
        print(f"  分类: {fact['category']}, 优先级: {fact['priority']}, 置信度: {fact['confidence']}")

    # 生成基础知识提示词
    print("\n生成的基础知识提示词:")
    print(base_kb.generate_base_knowledge_prompt())

    # 测试冲突检测
    print("\n测试冲突检测:")
    has_conflict = base_kb.check_conflict_with_base("HeDaas", "HeDaas是一家公司")
    print(f"冲突检测结果: {has_conflict}")

