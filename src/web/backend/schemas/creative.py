"""
Creative schemas - Pydantic v2 models for creative project endpoints.
长期创作项目相关的 Pydantic v2 模型。

Stage C.6: 为 /api/creative/* 提供 list/detail/advance 契约。
字段命名与前端 ``src/web/frontend/src/types/creative.ts`` 对齐。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =====================================================================
# Story Bible 子结构
# =====================================================================


class CharacterRelation(BaseModel):
    """
    角色关系条目。
    Attributes:
        target: 目标角色名
        relation: 关系描述
    """
    target: str = ""
    relation: str = ""


class Character(BaseModel):
    """
    角色条目。
    Attributes:
        uuid: 角色 uuid
        name: 角色名
        role: 角色定位（主角/配角/...）
        description: 角色描述
        relations: 与其他角色的关系
    """
    uuid: str = ""
    name: str = ""
    role: str = ""
    description: str = ""
    relations: List[CharacterRelation] = Field(default_factory=list)


class Chapter(BaseModel):
    """
    章节条目。
    Attributes:
        uuid: 章节 uuid
        chapter_title: 章节标题
        word_count: 字数
        content: 章节正文
    """
    uuid: str = ""
    chapter_title: str = ""
    word_count: int = 0
    content: str = ""


class StoryBible(BaseModel):
    """
    Story Bible（项目级线索状态机）。
    Attributes:
        characters: 角色列表
        worldview: 世界观描述
        chapters: 章节列表
        mainline_direction: 主线方向（与 creative_writer 对齐）
        active_themes: 当前活跃主题
        unresolved_threads: 未解线索
        resolved_threads: 已解线索
        important_facts: 重要事实
        next_direction: 下一段方向
        recent_keywords: 最近关键词
    """
    characters: List[Character] = Field(default_factory=list)
    worldview: str = ""
    chapters: List[Chapter] = Field(default_factory=list)
    mainline_direction: str = ""
    active_themes: List[str] = Field(default_factory=list)
    unresolved_threads: List[str] = Field(default_factory=list)
    resolved_threads: List[str] = Field(default_factory=list)
    important_facts: List[str] = Field(default_factory=list)
    next_direction: str = ""
    recent_keywords: List[str] = Field(default_factory=list)


# =====================================================================
# Project 模型
# =====================================================================


class CreativeProject(BaseModel):
    """
    创作项目（详情/统一形态）。
    Attributes:
        uuid: 项目 uuid
        title: 标题
        status: 业务状态（active / paused / completed / drafting / finished）
        word_count: 累计字数
        current_chars: 当前字数（与数据库 current_chars 一致）
        target_chars: 目标字数
        chapter_count: 章节数量
        work_type: 体裁
        premise: 故事前提
        tone: 语气
        point_of_view: 视角
        inspiration_source: 灵感来源
        outline: 大纲
        characters: 角色列表
        draft_chunks: 续写片段
        next_advance_at: 下次续写时间
        last_advanced_at: 上次续写时间
        created_at: ISO 8601 创建时间
        updated_at: ISO 8601 更新时间
        story_bible: Story Bible（详情场景下填充）
    """
    uuid: str
    title: str
    status: str = "drafting"
    word_count: int = 0
    current_chars: int = 0
    target_chars: int = 5000
    chapter_count: int = 0
    work_type: str = "短篇"
    premise: str = ""
    tone: str = ""
    point_of_view: str = "第一人称"
    inspiration_source: str = ""
    outline: List[Any] = Field(default_factory=list)
    characters: List[Any] = Field(default_factory=list)
    draft_chunks: List[Any] = Field(default_factory=list)
    next_advance_at: Optional[str] = None
    last_advanced_at: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""
    story_bible: Optional[StoryBible] = None


class CreativeProjectCreate(BaseModel):
    """
    创建创作项目请求体（POST /api/creative/projects）。
    Attributes:
        title: 标题（必填，1-200 字符）
        work_type: 体裁（短篇/中篇/长篇/散文/诗歌）
        premise: 故事前提
        tone: 语气
        point_of_view: 视角
        target_chars: 目标字数
        inspiration_source: 灵感来源描述
        outline: 大纲（每项一段话）
        characters: 角色列表
    """
    title: str = Field(..., min_length=1, max_length=200)
    work_type: str = Field("短篇", max_length=50)
    premise: str = Field("", max_length=2000)
    tone: str = Field("", max_length=200)
    point_of_view: str = Field("第一人称", max_length=50)
    target_chars: int = Field(5000, ge=100, le=1_000_000)
    inspiration_source: str = Field("", max_length=1000)
    outline: List[str] = Field(default_factory=list)
    characters: List[Dict[str, Any]] = Field(default_factory=list)


# =====================================================================
# Advance（续写）模型
# =====================================================================


class AdvanceRequest(BaseModel):
    """
    续写请求体。
    Attributes:
        user: 触发用户标识（默认 "default"）
        hint: 可选风格/方向提示（保留给未来扩展）
        advance_async: 是否异步触发（默认 True）
                       - True: 立即返回 task_id，异步生成内容并通过 'creative_progress' 事件推送
                       - False: 同步触发，更新 last_advanced_at 后立即返回
    """
    user: str = Field("default", max_length=100)
    hint: Optional[str] = Field(None, max_length=2000)
    advance_async: bool = True


class AdvanceResponse(BaseModel):
    """
    续写响应。
    Attributes:
        project_uuid: 项目 uuid
        task_id: 异步任务 id（同步模式时为空）
        status: 任务状态（queued / completed / failed）
        last_advanced_at: 上次续写时间（同步模式下为写入时间）
        project_status: 续写后项目状态
        message: 人类可读的描述
    """
    project_uuid: str
    task_id: str = ""
    status: str = "completed"
    last_advanced_at: Optional[str] = None
    project_status: str = "drafting"
    message: str = ""


# =====================================================================
# 列表响应包装
# =====================================================================


class CreativeProjectListResponse(BaseModel):
    """
    创作项目列表响应。
    Attributes:
        projects: 项目列表
        total: 总条数
    """
    projects: List[CreativeProject] = Field(default_factory=list)
    total: int = 0


# =====================================================================
# 兼容旧版命名（保留以防其他地方引用）
# =====================================================================


class CreativeProjectSummary(BaseModel):
    """
    创作项目摘要（列表项）。
    Attributes:
        uuid: 项目唯一标识
        title: 标题
        status: 业务状态（drafting / finished / paused）
        chapter_count: 章节数量（从 draft_chunks 派生）
        created_at: ISO 8601 创建时间
        updated_at: ISO 8601 更新时间
    """
    uuid: str
    title: str
    status: str
    chapter_count: int = 0
    created_at: str
    updated_at: str


class CreativeProjectDetail(CreativeProjectSummary):
    """
    创作项目详情。
    Attributes:
        story_bible: Story Bible 全文（含 mainline_direction / active_themes / 等）
        chapters: 章节列表（从 draft_chunks 派生）
        memory_pool_summary: 记忆池摘要（计数 + 最新若干条）
    """
    story_bible: Dict[str, Any] = Field(default_factory=dict)
    chapters: List[Dict[str, Any]] = Field(default_factory=list)
    memory_pool_summary: Dict[str, Any] = Field(default_factory=dict)


class CreativeAdvanceRequest(BaseModel):
    """
    续写请求体（payload 可选）。
    Attributes:
        user: 触发用户标识（默认 "default"）
        hint: 可选风格/方向提示（保留给未来扩展）
    """
    user: str = "default"
    hint: Optional[str] = None


class CreativeAdvanceResponse(BaseModel):
    """
    续写响应。
    Attributes:
        project_uuid: 项目 uuid
        new_chapter: 续写后追加的新章节（content / created_at / char_count）
        project_status: 续写后项目状态
    """
    project_uuid: str
    new_chapter: Dict[str, Any]
    project_status: str = "drafting"


__all__ = [
    # 主体模型
    "CreativeProject",
    "CreativeProjectCreate",
    "CreativeProjectListResponse",
    # Story Bible
    "StoryBible",
    "Character",
    "CharacterRelation",
    "Chapter",
    # Advance
    "AdvanceRequest",
    "AdvanceResponse",
    # 兼容旧名
    "CreativeProjectSummary",
    "CreativeProjectDetail",
    "CreativeAdvanceRequest",
    "CreativeAdvanceResponse",
]
