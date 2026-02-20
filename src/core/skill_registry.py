"""
技能注册表模块
实现全能代理所需的技能管理系统

技能（Skill）是可复用的能力描述文件，存储在虚拟文件系统中。
智能体可以读取这些技能并在任务中应用，也可以通过自主学习写入新技能。
"""

import os
import json
import re
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

from src.tools.debug_logger import get_debug_logger

load_dotenv()

debug_logger = get_debug_logger()

# 技能存储路径（在虚拟文件系统中）
SKILL_PATH_BUILTIN = "/skills/builtin/"
SKILL_PATH_LEARNED = "/skills/learned/"
SKILL_PATH_USER = "/skills/user/"

# 所有技能路径
ALL_SKILL_PATHS = [SKILL_PATH_BUILTIN, SKILL_PATH_LEARNED, SKILL_PATH_USER]

# 内置技能定义（开箱即用）
BUILTIN_SKILLS: Dict[str, str] = {
    "information_retrieval": """# 信息检索技能

## 描述
从用户问题中提取关键词并整合多源信息得出结论。

## 步骤
1. 分析问题，识别核心关键词
2. 搜索相关知识库和上下文
3. 整合信息，去除冗余
4. 生成结构化答案

## 注意事项
- 优先使用已知知识，必要时再搜索
- 信息来源多样时需交叉验证
- 对不确定信息标注置信度
""",
    "task_decomposition": """# 任务分解技能

## 描述
将复杂任务拆分为可并行或顺序执行的子任务。

## 步骤
1. 分析任务目标和约束条件
2. 识别独立子任务（可并行）
3. 识别依赖子任务（需顺序）
4. 为每个子任务分配角色和技能
5. 输出结构化执行计划

## 适用场景
- 多步骤研究任务
- 内容创作任务
- 数据处理流程
""",
    "result_synthesis": """# 结果综合技能

## 描述
将多个智能体的部分结果整合为完整、连贯的最终答案。

## 步骤
1. 收集所有子任务的输出
2. 检查内容重叠和矛盾
3. 按逻辑顺序组织信息
4. 生成统一格式的最终答案

## 注意事项
- 保留每个智能体的核心贡献
- 解决矛盾时优先选择更详细的描述
- 最终答案需完整覆盖原始任务要求
""",
    "error_recovery": """# 错误恢复技能

## 描述
当任务执行失败时，分析原因并尝试替代方案。

## 步骤
1. 分析错误类型（网络/权限/逻辑/数据等）
2. 根据错误类型选择恢复策略
3. 记录失败原因和恢复方法
4. 在恢复后验证结果

## 恢复策略
- 网络错误：重试，最多3次
- 数据错误：清理数据后重新处理
- 逻辑错误：降级到更简单的方案
""",
    "knowledge_extraction": """# 知识提取技能

## 描述
从对话和任务执行中提取可复用的知识点。

## 步骤
1. 分析对话内容，识别事实陈述
2. 提取人物、事件、关系等实体信息
3. 识别可重用的方法和流程
4. 将知识结构化存储

## 输出格式
```json
{
  "entities": [{"name": "实体名", "type": "类型", "description": "描述"}],
  "facts": [{"subject": "主体", "predicate": "谓语", "object": "客体"}],
  "procedures": [{"name": "流程名", "steps": ["步骤1", "步骤2"]}]
}
```
""",
}


class SkillRegistry:
    """
    技能注册表
    管理所有可用技能，支持内置技能、用户自定义技能和自主学习技能
    """

    def __init__(self, db_path: Optional[str] = None):
        """
        初始化技能注册表

        Args:
            db_path: SQLite数据库路径，用于持久化已学习的技能
        """
        self.db_path = db_path or os.getenv("SKILL_DB_PATH", "skill_registry.db")
        self._init_db()
        self._init_builtin_skills()

        debug_logger.log_module("SkillRegistry", "技能注册表初始化完成", {
            "db_path": self.db_path,
            "builtin_skills": len(BUILTIN_SKILLS)
        })

    def _init_db(self):
        """初始化SQLite数据库"""
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL DEFAULT 'learned',
                    content TEXT NOT NULL,
                    description TEXT,
                    usage_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 1.0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS skill_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    skill_name TEXT NOT NULL,
                    task_type TEXT,
                    outcome TEXT,
                    timestamp TEXT NOT NULL
                )
            """)
            conn.commit()
        finally:
            conn.close()

    def _init_builtin_skills(self):
        """将内置技能写入数据库（若未存在）"""
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now().isoformat()
            for name, content in BUILTIN_SKILLS.items():
                # 提取第一行标题作为描述
                first_line = content.strip().split('\n')[0].lstrip('#').strip()
                conn.execute("""
                    INSERT OR IGNORE INTO skills
                    (name, category, content, description, created_at, updated_at)
                    VALUES (?, 'builtin', ?, ?, ?, ?)
                """, (name, content, first_line, now, now))
            conn.commit()
        finally:
            conn.close()

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """
        获取指定技能

        Args:
            name: 技能名称

        Returns:
            技能信息字典，不存在时返回None
        """
        conn = sqlite3.connect(self.db_path)
        try:
            row = conn.execute(
                "SELECT name, category, content, description, usage_count, success_rate FROM skills WHERE name = ?",
                (name,)
            ).fetchone()
            if row:
                return {
                    "name": row[0],
                    "category": row[1],
                    "content": row[2],
                    "description": row[3],
                    "usage_count": row[4],
                    "success_rate": row[5]
                }
            return None
        finally:
            conn.close()

    def list_skills(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        列出所有技能

        Args:
            category: 按类别过滤（'builtin'/'learned'/'user'，None表示全部）

        Returns:
            技能列表
        """
        conn = sqlite3.connect(self.db_path)
        try:
            if category:
                rows = conn.execute(
                    "SELECT name, category, description, usage_count, success_rate FROM skills WHERE category = ? ORDER BY usage_count DESC",
                    (category,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT name, category, description, usage_count, success_rate FROM skills ORDER BY category, usage_count DESC"
                ).fetchall()
            return [
                {"name": r[0], "category": r[1], "description": r[2],
                 "usage_count": r[3], "success_rate": r[4]}
                for r in rows
            ]
        finally:
            conn.close()

    def add_skill(
        self,
        name: str,
        content: str,
        category: str = "user",
        description: str = ""
    ) -> bool:
        """
        添加或更新技能

        Args:
            name: 技能名称（小写下划线格式）
            content: 技能内容（Markdown格式）
            category: 类别（'user'/'learned'）
            description: 简短描述

        Returns:
            是否成功
        """
        # 验证技能名称格式
        if not re.match(r'^[a-z][a-z0-9_]*$', name):
            debug_logger.log_error("SkillRegistry", f"技能名称格式无效: {name}", None)
            return False

        # 禁止覆盖内置技能
        existing = self.get_skill(name)
        if existing and existing["category"] == "builtin":
            debug_logger.log_error("SkillRegistry", f"不允许覆盖内置技能: {name}", None)
            return False

        now = datetime.now().isoformat()
        if not description:
            first_line = content.strip().split('\n')[0].lstrip('#').strip()
            description = first_line[:100]

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute("""
                INSERT INTO skills (name, category, content, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    content = excluded.content,
                    description = excluded.description,
                    updated_at = excluded.updated_at
            """, (name, category, content, description, now, now))
            conn.commit()
            debug_logger.log_info("SkillRegistry", f"技能已添加/更新: {name} [{category}]")
            return True
        except Exception as e:
            debug_logger.log_error("SkillRegistry", f"添加技能失败: {str(e)}", e)
            return False
        finally:
            conn.close()

    def learn_skill(
        self,
        name: str,
        content: str,
        description: str = "",
        source_task: str = ""
    ) -> bool:
        """
        从任务经验中学习并保存新技能（自主学习入口）

        Args:
            name: 技能名称
            content: 技能描述内容（通常由LLM生成）
            description: 简短描述
            source_task: 来源任务描述

        Returns:
            是否成功
        """
        if source_task:
            content = f"{content}\n\n---\n*学习来源: {source_task}*\n*学习时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}*"

        success = self.add_skill(name, content, category="learned", description=description)
        if success:
            debug_logger.log_info("SkillRegistry", f"自主学习新技能: {name}", {
                "description": description,
                "source_task": source_task
            })
        return success

    def record_usage(self, skill_name: str, task_type: str = "", outcome: str = "success"):
        """
        记录技能使用情况并更新成功率

        Args:
            skill_name: 技能名称
            task_type: 任务类型
            outcome: 结果（'success'/'failure'）
        """
        conn = sqlite3.connect(self.db_path)
        try:
            now = datetime.now().isoformat()
            # 记录使用日志
            conn.execute(
                "INSERT INTO skill_usage_log (skill_name, task_type, outcome, timestamp) VALUES (?, ?, ?, ?)",
                (skill_name, task_type, outcome, now)
            )
            # 更新使用计数
            conn.execute(
                "UPDATE skills SET usage_count = usage_count + 1, updated_at = ? WHERE name = ?",
                (now, skill_name)
            )
            # 更新成功率（滑动平均）
            if outcome in ("success", "failure"):
                score = 1.0 if outcome == "success" else 0.0
                conn.execute("""
                    UPDATE skills SET success_rate = (success_rate * 0.9 + ? * 0.1), updated_at = ?
                    WHERE name = ?
                """, (score, now, skill_name))
            conn.commit()
        finally:
            conn.close()

    def get_skills_for_agent(
        self,
        skill_names: Optional[List[str]] = None,
        categories: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        构建智能体所需的技能文件字典（传入deepagents的invoke files参数）

        Args:
            skill_names: 指定的技能名称列表（None表示所有）
            categories: 指定的类别列表（None表示所有）

        Returns:
            {虚拟路径: 内容} 的字典，供 deepagents.invoke(files={...}) 使用
        """
        files: Dict[str, str] = {}

        conn = sqlite3.connect(self.db_path)
        try:
            conditions = []
            params: List[Any] = []

            if skill_names:
                placeholders = ",".join("?" * len(skill_names))
                conditions.append(f"name IN ({placeholders})")
                params.extend(skill_names)

            if categories:
                placeholders = ",".join("?" * len(categories))
                conditions.append(f"category IN ({placeholders})")
                params.extend(categories)

            where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
            rows = conn.execute(
                f"SELECT name, category, content FROM skills {where}",
                params
            ).fetchall()

            for name, category, content in rows:
                if category == "builtin":
                    path = f"{SKILL_PATH_BUILTIN}{name}.md"
                elif category == "learned":
                    path = f"{SKILL_PATH_LEARNED}{name}.md"
                else:
                    path = f"{SKILL_PATH_USER}{name}.md"
                files[path] = content

        finally:
            conn.close()

        debug_logger.log_info("SkillRegistry", "构建技能文件字典", {"skill_count": len(files)})
        return files

    def get_skill_summary(self) -> str:
        """
        获取所有技能的摘要，用于注入智能体系统提示词

        Returns:
            技能列表的Markdown文本
        """
        skills = self.list_skills()
        if not skills:
            return "当前无可用技能。"

        lines = ["## 可用技能列表\n"]
        current_category = None
        category_names = {"builtin": "内置技能", "learned": "已学习技能", "user": "用户自定义技能"}

        for skill in skills:
            cat = skill["category"]
            if cat != current_category:
                current_category = cat
                lines.append(f"\n### {category_names.get(cat, cat)}\n")
            desc = skill["description"] or skill["name"]
            lines.append(f"- **{skill['name']}**: {desc}")

        return "\n".join(lines)


# 全局单例
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """
    获取全局技能注册表单例

    Returns:
        SkillRegistry实例
    """
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
    return _registry
