"""
基础知识库模块
存储智能体的核心基础知识，这些知识：
1. 拥有最高优先级（100%正确）
2. 不可被覆盖或更改
3. 即使与现实相悖也以该知识为准
4. 不以上下文形式存在，而是直接嵌入到提示词中
"""

import os
from typing import Dict, List, Any
from database_manager import DatabaseManager


class BaseKnowledge:
    """
    基础知识库管理器
    管理智能体的核心基础知识，这些知识具有绝对权威性
    使用数据库存储替代JSON文件
    """

    def __init__(self, db_manager: DatabaseManager = None):
        """
        初始化基础知识库

        Args:
            db_manager: 数据库管理器实例（如果为None则创建新实例）
        """
        self.db = db_manager or DatabaseManager()

        # 检查是否需要初始化默认知识
        base_facts = self.db.get_all_base_facts()
        if not base_facts:
            self._initialize_default_knowledge()

        # 检查是否需要从JSON迁移数据
        if os.path.exists('base_knowledge.json'):
            print("○ 检测到旧的JSON文件，正在迁移到数据库...")
            self.db.migrate_from_json('base_knowledge.json', 'base_knowledge')
            # 迁移完成后可以选择重命名或删除JSON文件
            os.rename('base_knowledge.json', 'base_knowledge.json.bak')
            print("✓ JSON文件已备份为 base_knowledge.json.bak")

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

        print("✓ 默认基础知识已初始化")


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
            # 检查是否已存在
            existing = self.db.get_base_fact(entity_name)
            if existing:
                print(f"⚠ 基础事实已存在: {entity_name}")
                print(f"  现有内容: {existing['content']}")
                print(f"  → 基础知识不可覆盖，保持原有内容")
                return False

            # 添加基础事实
            result = self.db.add_base_fact(
                entity_name=entity_name,
                content=fact_content,
                category=category,
                description=description,
                immutable=immutable
            )

            if result:
                print(f"✓ 已添加基础事实: {entity_name} -> {fact_content}")
            return result

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
        return self.db.get_base_fact(entity_name)

    def check_conflict_with_base(self, entity_name: str, new_content: str) -> bool:
        """
        检查新知识是否与基础知识冲突

        Args:
            entity_name: 实体名称
            new_content: 新的知识内容

        Returns:
            True表示存在冲突，False表示无冲突
        """
        base_fact = self.db.get_base_fact(entity_name)

        if not base_fact:
            return False


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
        return self.db.get_all_base_facts()

    def generate_base_knowledge_prompt(self) -> str:
        """
        生成用于嵌入提示词的基础知识文本
        这些知识将直接嵌入到系统提示词中，确保AI始终遵循

        Returns:
            基础知识提示词文本
        """
        base_facts = self.get_all_base_facts()

        if not base_facts:
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
        for fact in base_facts:
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
        base_facts = self.get_all_base_facts()

        # 按分类统计
        by_category = {}
        for fact in base_facts:
            category = fact.get('category', '通用')
            by_category[category] = by_category.get(category, 0) + 1

        return {
            'total_facts': len(base_facts),
            'category_distribution': by_category,
            'all_immutable': all(f.get('immutable', True) for f in base_facts)
        }

    def remove_base_fact(self, entity_name: str) -> bool:
        """
        删除基础事实（谨慎使用，基础知识一般不应删除）

        Args:
            entity_name: 实体名称

        Returns:
            是否删除成功
        """
        return self.db.delete_base_fact(entity_name)


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

