"""Global Textual control plane for the Neo Agent runtime."""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import uuid
from threading import Lock
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Collapsible, Footer, Header, Input, Label, ListItem, ListView, Select, SelectionList, Static, TabbedContent, TabPane, TextArea

from neo_agent.plugins import PluginRegistry
from neo_agent.runtime import (AgentRuntime, DomainRegistry, EnvironmentService, SceneService, SceneScheduler,
                               ExpressionService, langchain_expression_learner, ConfigurationService,
                               RuntimeControls, SingleRoleService, GroupReplyGate, IncomingMessage)
from neo_agent.services import SchedulePlanningService
from neo_agent.storage import DiskStore
from neo_agent.services import InterruptQuestionService


class NeoConsole(App[None]):
    TITLE = "NEO / AGENT OPERATIONS"
    SUB_TITLE = "VIRTUAL GROUP MEMBER · CONTROL PLANE"
    NAV_ITEMS = ("总览", "虚拟群友", "对话", "事件流", "日程", "知识库", "关系", "环境与域", "能力与 NPS", "运行记录", "存储与记忆", "频道连接", "系统设置", "实体管理", "表达风格", "人机协作", "任务编排", "认知与回放")
    CSS = """
    Screen { background: #0b1020; color: #e7edf7; }
    #shell { height: 1fr; padding: 1 2; }
    #rail { width: 27; border: round #334155; background: #111a2d; padding: 1; }
    #main { width: 1fr; padding: 0 2; }
    #brand { height: 3; color: #55e6c1; text-style: bold; }
    #nav { height: 1fr; border: none; background: transparent; }
    #nav ListItem { padding: 0 1; height: 3; }
    #nav ListItem.--highlight { background: #173a43; color: #55e6c1; }
    .eyebrow { color: #8ba0ba; text-style: bold; height: 2; }
    .panel { border: round #334155; background: #111a2d; padding: 1 2; height: auto; margin-bottom: 1; }
    .form-row { height: 3; }
    .editor { height: 8; margin: 1 0; }
    .editor-panel { display: none; height: auto; border: round #334155; background: #111a2d; padding: 1 2; margin-top: 1; }
    .muted { color: #94a3b8; height: auto; }
    #character-profile { height: auto; min-height: 8; margin-top: 1; }
    #character-editor-tabs { height: 19; margin-top: 1; }
    #character-editor-tabs TabPane { padding: 1; }
    .section-hint { color: #94a3b8; height: 2; }
    .editor-drawer { height: auto; border: round #334155; background: #0e1728; margin: 1 0; }
    .editor-drawer > Contents {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        grid-gutter: 0 1;
        padding: 1 2;
    }
    .editor-drawer > Contents > Label,
    .editor-drawer > Contents > Static,
    .editor-drawer > Contents > TextArea,
    .editor-drawer > Contents > Horizontal,
    .editor-drawer > Contents > Collapsible,
    .editor-drawer > Contents > SelectionList { column-span: 2; }
    .editor-drawer Input, .editor-drawer Select { width: 1fr; height: 3; }
    .editor-drawer TextArea { width: 1fr; height: 8; margin: 0; }
    .editor-drawer TextArea.code-editor { height: 12; }
    .editor-drawer .listing { height: auto; min-height: 3; max-height: 12; }
    .editor-drawer:focus-within { border: round #55e6c1; }
    .editor-note { color: #94a3b8; height: auto; margin-bottom: 1; }
    .editor-section-title { color: #55e6c1; text-style: bold; height: 1; margin-top: 1; }
    .danger-zone { border: round #7f1d1d; background: #1c1118; padding: 0 1; margin-top: 1; }
    .danger-zone > Title { color: #fca5a5; }
    .danger-zone Button { margin-top: 1; }
    .editor-result { height: auto; min-height: 3; }
    #content { height: 1fr; border: round #334155; background: #111a2d; padding: 1 2; }
    .page { height: 1fr; display: none; }
    .listing { height: 1fr; border: round #334155; background: #111a2d; padding: 1; overflow-y: auto; }
    .actions { height: 3; align-horizontal: right; }
    #character-list { height: 6; }
    #config-categories { height: 10; border: round #334155; margin: 1 0; }
    #characters .character-fields { height: 3; }
    #characters .profile-editor { height: 10; min-height: 6; margin: 0; }
    #characters .editor-actions { height: 3; align-horizontal: right; margin-top: 1; }
    #chat-character { height: 3; color: #55e6c1; }
    #chat-log { height: 1fr; border: round #334155; padding: 1; overflow-y: auto; }
    #chat-input { height: 5; margin-top: 1; }
    #service-status { height: auto; }
    #status { height: 2; color: #94a3b8; dock: bottom; }
    """
    BINDINGS = [
        Binding("q", "quit", "退出", show=True), Binding("r", "refresh", "刷新", show=True),
        Binding("e", "navigate('事件流')", "事件", show=True), Binding("s", "navigate('日程')", "日程", show=True),
        *[Binding(str(i), f"navigate_by_index({i - 1})", str(i), show=False) for i in range(1, 10)],
        Binding("0", "navigate_by_index(9)", "更多", show=False),
        Binding("ctrl+1", "navigate_by_index(10)", "记忆", show=False),
        Binding("ctrl+2", "navigate_by_index(11)", "频道", show=False),
        Binding("ctrl+3", "navigate_by_index(12)", "设置", show=False),
        Binding("ctrl+4", "navigate_by_index(13)", "实体", show=False),
        Binding("ctrl+5", "navigate_by_index(14)", "表达", show=False),
        Binding("ctrl+6", "navigate_by_index(15)", "提问", show=False),
        Binding("ctrl+7", "navigate_by_index(16)", "任务", show=False),
        Binding("ctrl+8", "navigate_by_index(17)", "认知", show=False),
    ]

    def __init__(self, store: DiskStore, *, coordinator_model: Any | None = None,
                 schedule_planning_model: Any | None = None):
        super().__init__()
        self.store = store
        self.coordinator_model = coordinator_model
        self.schedule_planner = SchedulePlanningService(store, model=schedule_planning_model)
        self._schedule_suggestions: list[dict[str, Any]] = []
        self._pending_similar_schedule: dict[str, Any] | None = None
        self.plugin_registry = PluginRegistry(store)
        self.nps = self.plugin_registry.nps
        self.environment_service = EnvironmentService(store)
        self.scene_service = SceneService(store, model=schedule_planning_model or coordinator_model)
        self.scene_scheduler = SceneScheduler(store, model=schedule_planning_model or coordinator_model, scenes=self.scene_service)
        self.domain_registry = DomainRegistry(store)
        self.expression_service = ExpressionService(store)
        self.configuration_service = ConfigurationService(store)
        self.controls = RuntimeControls(store)
        self.single_role = SingleRoleService(store)
        self.group_reply_gate = GroupReplyGate()
        self.question_service = InterruptQuestionService(store)
        self.active_view = "总览"
        self._busy = False
        self._scene_scheduler_lock = Lock()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="shell"):
            with Vertical(id="rail"):
                yield Label("◈ NEO / CONTROL", id="brand")
                yield ListView(*[ListItem(Label(item)) for item in self.NAV_ITEMS], id="nav")
                yield Static(id="service-status", classes="panel")
            with Vertical(id="main"):
                yield Label("AGENTIC CONTROL PLANE  /  LIVE", classes="eyebrow")
                yield Static(id="content", classes="page")
                with VerticalScroll(id="characters", classes="page"):
                    yield Label("单角色控制台 · 首次创建林依示范角色；后续自动使用唯一活动角色。", classes="eyebrow")
                    yield Select([], prompt="存在多个活动角色，请选择唯一主角色", id="primary-character")
                    yield Button("设为唯一活动角色（归档其余）", id="select-primary-character")
                    yield Static("", id="character-profile", classes="panel")
                    with Horizontal(classes="actions"):
                        yield Button("Debug：编辑角色设定", id="edit-character", variant="primary")
                        yield Button("归档角色", id="archive-character", variant="error")
                    with Vertical(id="character-editor", classes="editor-panel"):
                        yield Label("角色设定编辑器", classes="eyebrow")
                        yield Static("按主题分区编辑 · 角色 ID 自动生成并由系统管理", classes="muted")
                        with Horizontal(classes="editor-actions"):
                            yield Button("取消", id="cancel-character-edit")
                            yield Button("保存设定", id="save-character", variant="primary")
                        with TabbedContent(initial="character-basic", id="character-editor-tabs"):
                            with TabPane("基础资料", id="character-basic"):
                                yield Label("身份信息与日常兴趣", classes="section-hint")
                                with Horizontal(classes="character-fields"):
                                    yield Input(placeholder="显示名称", id="character-name", classes="form-row")
                                    yield Input(placeholder="性别", id="character-gender", classes="form-row")
                                with Horizontal(classes="character-fields"):
                                    yield Input(placeholder="身份 / 职业", id="character-role", classes="form-row")
                                    yield Input(placeholder="年龄", id="character-age", classes="form-row")
                                with Horizontal(classes="character-fields"):
                                    yield Input(placeholder="身高", id="character-height", classes="form-row")
                                    yield Input(placeholder="体重", id="character-weight", classes="form-row")
                                yield Input(placeholder="爱好", id="character-hobby", classes="form-row")
                            with TabPane("性格表达", id="character-personality-pane"):
                                yield Label("描述说话方式、性格特点与行为倾向", classes="section-hint")
                                yield TextArea(id="character-personality", soft_wrap=True, classes="editor profile-editor")
                            with TabPane("背景故事", id="character-background-pane"):
                                yield Label("补充经历、关系、日常与世界观；也可以完全重写", classes="section-hint")
                                yield TextArea(id="character-background", soft_wrap=True, classes="editor profile-editor")
                with Vertical(id="chat", classes="page"):
                    yield Static("", id="chat-character", classes="panel")
                    yield Static(id="chat-log")
                    yield TextArea(id="chat-input", soft_wrap=True)
                    with Horizontal(classes="actions"):
                        yield Button("发送消息", id="send-chat", variant="primary")
                with VerticalScroll(id="events", classes="page"):
                    yield Static(id="events-list", classes="listing")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="过滤事件类型（可选）", id="event-filter")
                        yield Button("过滤 / 刷新", id="filter-events")
                    with Collapsible(title="＋ 追加审计事件", collapsed=True, id="event-log-editor", classes="editor-drawer debug-editor"):
                        yield Label("追加的事件会写入不可变审计日志。", classes="editor-note")
                        yield Label("事件信息", classes="editor-section-title")
                        yield Input(placeholder="事件类型，如 group.message", id="event-type")
                        yield Input(placeholder="事件摘要", id="event-summary")
                        yield Button("写入不可变事件日志", id="append-event", variant="primary")
                    yield Label("事件管理记录（可更新生命周期；所有操作另写审计日志）", classes="eyebrow")
                    yield Static(id="event-record-list", classes="listing")
                    with Collapsible(title="＋ 创建 / 管理事件记录", collapsed=True, id="event-record-editor", classes="editor-drawer debug-editor"):
                        yield Label("由 Agent 建立的工作流事件请在任务编排中推进，不要手动覆盖。", classes="editor-note")
                        yield Label("新建或定位", classes="editor-section-title")
                        yield Input(placeholder="事件记录 ID（必填，限 22 位英文 / 数字 / _ / -）", id="event-record-id")
                        yield Input(placeholder="事件标题", id="event-record-title")
                        yield Input(placeholder="事件类型", id="event-record-type")
                        yield Input(placeholder="事件详情", id="event-record-details")
                        yield Input(placeholder="状态：pending / triggered / awaiting_user / needs_review / completed / failed / cancelled", id="event-record-status", value="pending")
                        with Horizontal(classes="actions"):
                            yield Button("创建事件", id="create-event-record", variant="primary")
                            yield Button("更新状态", id="update-event-record")
                            yield Button("触发事件", id="trigger-event-record")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除事件记录不可撤销；审计日志仍会保留操作痕迹。", classes="editor-note")
                            yield Button("删除记录", id="delete-event-record", variant="error")
                with VerticalScroll(id="human-questions", classes="page"):
                    yield Label("Agent 中断提问 · 待回答请求会持久化，回答后可由会话恢复", classes="eyebrow")
                    yield Static(id="question-list", classes="listing")
                    with Collapsible(title="回复 Agent 的澄清问题", collapsed=True, id="question-reply-editor", classes="editor-drawer"):
                        yield Input(placeholder="待回答 question_id", id="question-id")
                        yield Input(placeholder="给 Agent 的回答", id="question-answer")
                        with Horizontal(classes="actions"):
                            yield Button("刷新待回答", id="refresh-questions")
                            yield Button("提交回答", id="resolve-question", variant="primary")
                with VerticalScroll(id="collaboration", classes="page"):
                    yield Label("任务型事件 · LangChain 多角色分析 / 规划 / 执行 / 验收", classes="eyebrow")
                    yield Static(id="collaboration-runs", classes="listing")
                    with Collapsible(title="＋ 新建 / 恢复任务", collapsed=True, id="collaboration-editor", classes="editor-drawer debug-editor"):
                        yield Label("描述目标与验收标准；Agent 会在 PyVDisk VFS 工作区内分步执行。", classes="editor-note")
                        yield Label("发起新任务", classes="editor-section-title")
                        yield Input(placeholder="任务标题", id="collaboration-title")
                        yield TextArea(id="collaboration-description", soft_wrap=True, classes="editor", placeholder="任务描述")
                        yield Input(placeholder="要求（可选）", id="collaboration-requirements")
                        yield Input(placeholder="完成标准（可选）", id="collaboration-criteria")
                        yield Button("发起协作任务", id="start-collaboration", variant="primary")
                        with Collapsible(title="恢复待答任务", collapsed=True):
                            yield Label("仅恢复处于等待用户回答状态的运行。", classes="editor-note")
                            yield Input(placeholder="待恢复 run_id", id="collaboration-run-id")
                            yield Button("恢复任务", id="resume-collaboration")
                with VerticalScroll(id="schedules", classes="page"):
                    yield Static(id="schedule-list", classes="listing")
                    with Horizontal(classes="character-fields"):
                        yield Select([("全部日期", "all"), ("今天", "today"), ("明天", "tomorrow"), ("本周", "week")], value="all", id="schedule-date-filter")
                        yield Select([("全部状态", "all"), ("进行中 / 待开始", "pending"), ("已完成", "completed"), ("已取消", "cancelled"), ("周期冲突", "recurrence_blocked")], value="all", id="schedule-status-filter")
                        yield Button("应用筛选", id="filter-schedules")
                    with Collapsible(title="＋ 新建日程记录", collapsed=True, id="schedule-create-editor", classes="editor-drawer debug-editor"):
                        yield Label("填写明确时间；记录仅作为生活上下文，不会发送或暂存提醒。用户个人日程只读，Agent 不会改写。", classes="editor-note")
                        yield Label("日程内容与归属", classes="editor-section-title")
                        yield Input(placeholder="schedule_id（必填且唯一）", id="schedule-id")
                        yield Input(placeholder="标题", id="schedule-title")
                        yield Input(placeholder="ISO-8601 时间，例如 2026-10-03T18:00:00+08:00", id="schedule-due")
                        yield Input(placeholder="结束时间 ISO-8601（可选）", id="schedule-end")
                        yield Input(placeholder="描述（可选）", id="schedule-description")
                        yield Select([("Agent 个人", "agent"), ("用户个人（只读信息）", "user"), ("双方共同活动", "shared")], value="agent", id="schedule-category")
                        yield Label("重复规则与优先级（可选）", classes="editor-section-title")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="类型 appointment / recurring / temporary", id="schedule-type", value="appointment")
                            yield Input(placeholder="优先级 low / medium / high / critical（按类型默认）", id="schedule-priority")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="周期星期：周一 0 … 周日 6", id="schedule-weekday")
                            yield Input(placeholder="周期说明，如 every-week", id="schedule-recurrence")
                        with Horizontal(classes="actions"):
                            yield Button("创建日程记录", id="create-schedule", variant="primary")
                            yield Button("复核后仍然创建", id="confirm-create-similar-schedule", variant="warning", disabled=True)
                    with Collapsible(title="✎ 编辑 / 删除日程", collapsed=True, id="schedule-edit-editor", classes="editor-drawer debug-editor"):
                        yield Label("编辑或删除 Debug 日程记录；系统不会投递通知。", classes="editor-note")
                        yield Label("编辑目标", classes="editor-section-title")
                        yield Input(placeholder="编辑目标 schedule_id", id="schedule-edit-id")
                        yield Label("日程内容", classes="editor-section-title")
                        yield Input(placeholder="新标题", id="schedule-edit-title")
                        yield Input(placeholder="新 ISO-8601 时间（含时区）", id="schedule-edit-due")
                        yield Input(placeholder="新描述", id="schedule-edit-description")
                        yield Input(placeholder="新结束时间 ISO-8601（可选）", id="schedule-edit-end")
                        yield Label("周期与优先级（留空保持原值）", classes="editor-section-title")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="新类型 appointment / recurring / temporary", id="schedule-edit-type")
                            yield Input(placeholder="新优先级 low / medium / high / critical", id="schedule-edit-priority")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="周期星期 0–6", id="schedule-edit-weekday")
                            yield Input(placeholder="周期规则", id="schedule-edit-recurrence")
                        yield Button("保存日程修改", id="update-schedule", variant="primary")
                        with Collapsible(title="危险操作与协作决策", collapsed=True, classes="danger-zone"):
                            yield Label("删除会移除持久队列任务；协作决定会改变请求状态。", classes="editor-note")
                            yield Input(placeholder="要删除的 schedule_id", id="schedule-delete-id")
                            yield Button("删除日程", id="delete-schedule", variant="error")
                            yield Button("确认协作", id="confirm-schedule", variant="primary")
                            yield Button("拒绝协作", id="reject-schedule", variant="error")
                    with Collapsible(title="⌕ 时间范围与空闲查询", collapsed=True, id="schedule-query-tools", classes="editor-drawer"):
                        yield Label("范围分析", classes="editor-section-title")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="范围开始 ISO-8601（含时区）", id="schedule-range-start")
                            yield Input(placeholder="范围结束 ISO-8601（含时区）", id="schedule-range-end")
                            yield Input(placeholder="最短空闲分钟数", id="schedule-free-minutes", value="30")
                        with Horizontal(classes="actions"):
                            yield Button("查询范围", id="query-schedule-range")
                            yield Button("查找空闲时段", id="find-free-slots")
                            yield Button("日程统计", id="schedule-statistics")
                        yield Label("单项详情", classes="editor-section-title")
                        with Horizontal(classes="actions"):
                            yield Input(placeholder="详情 schedule_id", id="schedule-detail-id")
                            yield Button("查看详情", id="schedule-details")
                        yield Static(id="schedule-analysis", classes="listing editor-result")
                    with Collapsible(title="✦ 临时活动建议", collapsed=True, id="schedule-suggestions-editor", classes="editor-drawer"):
                        yield Label("生成建议本身不写入日程；采用建议需要开启 Debug。", classes="editor-note")
                        with Horizontal(classes="character-fields"):
                            yield Input(placeholder="角色名称", id="schedule-character-name", value="智能体")
                            yield Input(placeholder="角色兴趣", id="schedule-character-hobbies", value="阅读、学习")
                            yield Input(placeholder="建议时长下限（分钟）", id="schedule-suggestion-minutes", value="60")
                        yield Input(placeholder="对话上下文（可选）", id="schedule-suggestion-context")
                        yield Button("生成活动建议", id="generate-schedule-suggestions")
                        yield Static(id="schedule-suggestions", classes="listing")
                        with Collapsible(title="采用建议并创建日程", collapsed=True, id="schedule-suggestion-apply", classes="editor-drawer debug-editor"):
                            with Horizontal(classes="actions"):
                                yield Input(placeholder="采用建议编号（从 1 开始）", id="schedule-suggestion-index", value="1")
                                yield Button("采用所选建议", id="apply-schedule-suggestion", variant="primary")
                with VerticalScroll(id="knowledge", classes="page"):
                    yield Static(id="knowledge-list", classes="listing")
                    with Horizontal(classes="actions"):
                        yield Input(placeholder="搜索关键词", id="knowledge-search")
                        yield Button("搜索", id="search-knowledge")
                    with Collapsible(title="＋ 创建 / 编辑知识条目", collapsed=True, id="knowledge-editor", classes="editor-drawer debug-editor"):
                        yield Label("按主题组织条目；Agent 自动沉淀的知识也会显示在上方列表。", classes="editor-note")
                        yield Label("条目身份", classes="editor-section-title")
                        yield Input(placeholder="知识 ID（必填）", id="knowledge-id")
                        yield Input(placeholder="标题", id="knowledge-title")
                        yield TextArea(placeholder="知识内容 / 事实说明", id="knowledge-content", soft_wrap=True, classes="editor")
                        yield Button("保存知识条目", id="save-knowledge", variant="primary")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除不可撤销；请先确认上方 ID。", classes="editor-note")
                            yield Button("删除知识", id="delete-knowledge", variant="error")
                    with Collapsible(title="＋ 编辑基础知识事实", collapsed=True, id="base-knowledge-editor", classes="editor-drawer debug-editor"):
                        yield Label("适合记录实体相关的稳定事实；置信度取值 0–1。", classes="editor-note")
                        yield Label("事实索引", classes="editor-section-title")
                        yield Input(placeholder="事实 ID（必填）", id="base-knowledge-id")
                        yield Input(placeholder="实体名称", id="base-knowledge-entity")
                        yield Input(placeholder="分类", id="base-knowledge-category")
                        yield Input(placeholder="置信度 0–1", id="base-knowledge-confidence", value="1")
                        yield TextArea(placeholder="稳定事实内容", id="base-knowledge-content", soft_wrap=True, classes="editor")
                        yield Button("保存基础知识", id="save-base-knowledge", variant="primary")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除不可撤销；请先确认上方事实 ID。", classes="editor-note")
                            yield Button("删除基础知识", id="delete-base-knowledge", variant="error")
                with VerticalScroll(id="relationships", classes="page"):
                    yield Static(id="relationship-list", classes="listing")
                    with Collapsible(title="＋ 记录人工互动", collapsed=True, id="relationship-editor", classes="editor-drawer debug-editor"):
                        yield Label("人工记录仅作为可审计证据；关系分数变化仍受运行时规则约束。", classes="editor-note")
                        yield Input(placeholder="关系 ID（角色-用户）", id="relationship-id")
                        yield Input(placeholder="对方名称 / 群组", id="relationship-peer")
                        yield Input(placeholder="互动备注", id="relationship-note")
                        yield Input(placeholder="本次关系分值变化，例如 1 或 -1", id="relationship-delta", value="0")
                        yield Button("记录互动", id="record-relationship", variant="primary")
                    with Collapsible(title="＋ 人工标注情绪", collapsed=True, id="emotion-editor", classes="editor-drawer debug-editor"):
                        yield Label("情绪是单轮临时状态；人工标注会留下来源与证据。", classes="editor-note")
                        yield Input(placeholder="情绪标签", id="emotion-tone")
                        yield Input(placeholder="情绪分值 -1 至 1", id="emotion-score", value="0")
                        yield Input(placeholder="证据 / 上下文", id="emotion-evidence")
                        yield Button("记录情绪", id="record-emotion")
                    yield Label("最近一次关系印象 · 维度可视化", classes="eyebrow")
                    yield Static(id="emotion-radar", classes="listing")
                    yield Label("对话主题时间线 · 来自该会话的长期摘要", classes="eyebrow")
                    yield Static(id="topic-timeline", classes="listing")
                    yield Label("可审计情绪 / 关系历史", classes="eyebrow")
                    yield Static(id="emotion-list", classes="listing")
                    with Collapsible(title="⌕ 分析关系与对话主题", collapsed=True, id="relationship-analysis-tools", classes="editor-drawer"):
                        yield Label("分析会读取指定会话的历史摘要，不会修改关系分值。", classes="editor-note")
                        yield Input(placeholder="分析来源 conversation_id", id="emotion-conversation-id", value="default")
                        with Horizontal(classes="actions"):
                            yield Button("分析所选关系", id="analyze-emotion", variant="primary")
                            yield Button("刷新关系 / 主题视图", id="refresh-relationships")
                with VerticalScroll(id="environment", classes="page"):
                    yield Static(id="environment-list", classes="listing")
                    yield Label("当前场景与已访问场景池", classes="eyebrow")
                    yield Static(id="scene-pool", classes="listing")
                    with Collapsible(title="＋ 创建 / 编辑环境", collapsed=True, id="environment-editor", classes="editor-drawer debug-editor"):
                        yield Label("维护世界中的地点及其结构化详情；关联操作会写入审计记录。", classes="editor-note")
                        yield Label("地点资料", classes="editor-section-title")
                        yield Input(placeholder="类型：environment 或 domain", id="environment-kind", value="environment")
                        yield Input(placeholder="ID（新建留空）", id="environment-id")
                        yield Input(placeholder="名称", id="environment-name")
                        yield TextArea(placeholder="地点说明、氛围与结构化详情", id="environment-details", soft_wrap=True, classes="editor")
                        yield Label("域关联", classes="editor-section-title")
                        yield Input(placeholder="关联域 ID / 成员环境 ID", id="environment-domain-id")
                        yield Input(placeholder="域默认环境 ID（创建/编辑域时）", id="domain-default-environment")
                        with Horizontal(classes="actions"):
                            yield Button("保存环境", id="save-environment", variant="primary")
                            yield Button("设为当前环境", id="activate-environment")
                            yield Button("关联域", id="link-environment-domain")
                            yield Button("从域移除环境", id="unlink-environment-domain")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除环境会影响其物体与连接；请先检查关联。", classes="editor-note")
                            yield Button("删除", id="delete-environment", variant="error")
                    with Collapsible(title="＋ 管理环境物体", collapsed=True, id="environment-object-editor", classes="editor-drawer debug-editor"):
                        yield Label("为场景中的对象填写位置、属性和交互提示。", classes="editor-note")
                        yield Label("物体与场景", classes="editor-section-title")
                        yield Input(placeholder="物体 ID（新建可留空）", id="environment-object-id")
                        yield Input(placeholder="所属环境 ID", id="environment-object-environment")
                        yield Input(placeholder="物体名称", id="environment-object-name")
                        yield Input(placeholder="位置 / 场景方位", id="environment-object-position")
                        yield Input(placeholder="优先级 0–100", id="environment-object-priority", value="50")
                        yield Input(placeholder="属性 JSON object", id="environment-object-properties", value="{}")
                        yield TextArea(placeholder="描述与交互提示", id="environment-object-description", soft_wrap=True, classes="editor")
                        with Horizontal(classes="actions"):
                            yield Button("保存物体", id="save-environment-object", variant="primary")
                            yield Button("切换物体可见性", id="toggle-environment-object", variant="warning")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除物体不可撤销。", classes="editor-note")
                            yield Button("删除物体", id="delete-environment-object", variant="error")
                    yield Label("环境连接关系图 / 移动可达性", classes="eyebrow")
                    yield Static(id="environment-graph", classes="listing")
                    with Collapsible(title="＋ 编辑环境连接", collapsed=True, id="environment-connection-editor", classes="editor-drawer debug-editor"):
                        yield Label("连接端点与通行规则", classes="editor-section-title")
                        yield Input(placeholder="起始环境 ID", id="connection-from")
                        yield Input(placeholder="目标环境 ID", id="connection-to")
                        yield Input(placeholder="连接类型", id="connection-type", value="normal")
                        yield Select((("双向", "bidirectional"), ("单向", "one_way")), value="bidirectional", id="connection-direction")
                        yield Input(placeholder="连接描述", id="connection-description")
                        yield Button("创建连接", id="create-environment-connection", variant="primary")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Input(placeholder="待删除连接 ID", id="connection-id")
                            yield Button("删除连接", id="delete-environment-connection", variant="error")
                    with Collapsible(title="⌕ 检查移动可达性", collapsed=True, id="environment-move-check", classes="editor-drawer"):
                        yield Input(placeholder="待验证目标环境 ID", id="connection-check-to")
                        yield Button("检查当前环境可达", id="check-environment-move")
                    yield Button("刷新环境视图", id="refresh-environment")
                    yield Label("伪视觉工具审计记录", classes="eyebrow")
                    yield Static(id="vision-log-list", classes="listing")
                    with Collapsible(title="＋ 记录模拟视觉观察", collapsed=True, id="vision-audit-editor", classes="editor-drawer debug-editor"):
                        yield Label("仅用于离线审计与上下文模拟，不连接真实视觉模型。", classes="editor-note")
                        yield Input(placeholder="查询 / 用户问题", id="vision-query")
                        yield Input(placeholder="查看物体 ID，逗号分隔", id="vision-objects")
                        yield Input(placeholder="触发方式 auto / manual", id="vision-trigger", value="manual")
                        yield TextArea(placeholder="提供给 Agent 的视觉上下文", id="vision-context", soft_wrap=True, classes="editor")
                        yield Button("记录视觉观察", id="log-vision-usage", variant="primary")
                    yield Label("域工作区 · 成员 / 默认位置 / 切换", classes="eyebrow")
                    yield Static(id="domain-list", classes="listing")
                    with Collapsible(title="＋ 管理环境域", collapsed=True, id="domain-editor", classes="editor-drawer debug-editor"):
                        yield Label("创建或更新域后，可添加成员环境并切换当前域。", classes="editor-note")
                        yield Label("域定义", classes="editor-section-title")
                        yield Input(placeholder="域 ID（新建可留空）", id="domain-id")
                        yield Input(placeholder="域名称", id="domain-name")
                        yield Input(placeholder="域描述", id="domain-description")
                        yield Label("成员与默认位置", classes="editor-section-title")
                        yield Input(placeholder="成员环境 ID", id="domain-member-environment")
                        yield Input(placeholder="默认环境 ID（需先加入域）", id="domain-default-environment-id")
                        with Horizontal(classes="actions"):
                            yield Button("保存域", id="save-domain", variant="primary")
                            yield Button("添加成员环境", id="add-domain-environment")
                            yield Button("移除成员", id="remove-domain-environment", variant="warning")
                        yield Label("当前域", classes="editor-section-title")
                        with Horizontal(classes="actions"):
                            yield Input(placeholder="切换目标域 ID", id="switch-domain-id")
                            yield Button("切换到域", id="switch-domain")
                with VerticalScroll(id="expressions", classes="page"):
                    yield Static(id="expression-list", classes="listing")
                    with Collapsible(title="＋ 编辑表达风格", collapsed=True, id="expression-editor", classes="editor-drawer debug-editor"):
                        yield Label("用自然语言描述语气特征，并提供少量代表性例句。", classes="editor-note")
                        yield Label("风格定义", classes="editor-section-title")
                        yield Input(placeholder="表达风格 ID（新建留空）", id="expression-id")
                        yield Input(placeholder="风格名称", id="expression-name")
                        yield Input(placeholder="分类，如感叹词 / 网络用语", id="expression-category", value="通用")
                        yield Input(placeholder="说明 / 特征", id="expression-description")
                        yield TextArea(placeholder="代表性例句（每行一条）", id="expression-examples", soft_wrap=True, classes="editor")
                        yield Button("保存表达风格", id="save-expression", variant="primary")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除表达风格不可撤销。", classes="editor-note")
                            yield Button("删除表达风格", id="delete-expression", variant="error")
                    with Collapsible(title="✦ 学习 / 清理用户表达习惯", collapsed=True, id="user-expression-editor", classes="editor-drawer debug-editor"):
                        yield Label("从指定会话的用户消息中提取表达习惯；结果会进入可审计列表。", classes="editor-note")
                        yield Label("学习来源", classes="editor-section-title")
                        yield Input(placeholder="学习来源 conversation_id", id="expression-conversation-id", value="default")
                        yield Button("立即学习", id="learn-user-expressions", variant="primary")
                        with Collapsible(title="危险操作 · 清空已学习习惯", collapsed=True, classes="danger-zone"):
                            yield Input(placeholder="输入 CLEAR USER HABITS 确认清空", id="clear-user-expressions-confirm")
                            yield Button("清空用户习惯", id="clear-user-expressions", variant="error")
                    yield Static(id="user-expression-list", classes="listing")
                with VerticalScroll(id="entities", classes="page"):
                    yield Static(id="entity-list", classes="listing")
                    with Collapsible(title="＋ 创建 / 编辑实体", collapsed=True, id="entity-editor", classes="editor-drawer debug-editor"):
                        yield Label("维护可复用实体与定义；实体 ID 可留空以自动生成。", classes="editor-note")
                        yield Label("实体身份", classes="editor-section-title")
                        yield Input(placeholder="实体 ID（必填）", id="entity-id")
                        yield Input(placeholder="实体名称", id="entity-name")
                        yield Input(placeholder="实体类型", id="entity-type")
                        yield TextArea(placeholder="实体定义 / 背景说明", id="entity-definition", soft_wrap=True, classes="editor")
                        yield Button("保存实体", id="save-entity", variant="primary")
                        with Collapsible(title="危险操作", collapsed=True, classes="danger-zone"):
                            yield Label("删除实体不可撤销；请先检查引用它的记录。", classes="editor-note")
                            yield Button("删除实体", id="delete-entity", variant="error")
                with VerticalScroll(id="plugins", classes="page"):
                    yield Static(id="plugin-list", classes="listing")
                    with Collapsible(title="⚙ 插件管理与 NPS 工作台", collapsed=True, id="plugin-editor", classes="editor-drawer debug-editor"):
                        yield Label("仅编辑新版 NPS manifest / VScript；Python 扩展遵循独立权限与隔离策略。", classes="editor-note")
                        yield Label("已安装能力", classes="editor-section-title")
                        yield Input(placeholder="内置 plugin_id / NPS id", id="plugin-id")
                        with Horizontal(classes="actions"):
                            yield Button("启用", id="enable-plugin", variant="primary")
                            yield Button("停用", id="disable-plugin", variant="warning")
                        with Collapsible(title="危险操作 · 删除 NPS", collapsed=True, classes="danger-zone"):
                            yield Label("只允许删除自定义 NPS；内置插件不可删除。", classes="editor-note")
                            yield Button("删除 NPS", id="delete-nps", variant="error")
                        yield Label("创建新版 NPS", classes="editor-section-title")
                        yield Input(placeholder="NPS id（例如 custom.hello）", id="nps-id")
                        yield Input(placeholder="名称", id="nps-name")
                        yield Input(placeholder="一句话说明此能力", id="nps-description")
                        yield Input(placeholder="VScript entrypoint（固定 main）", id="nps-entrypoint", value="main")
                        yield Input(placeholder='能力 JSON 数组，例如 ["python.call"]', id="nps-capabilities", value="[]")
                        with Collapsible(title="工具参数与测试", collapsed=False):
                            yield Label("参数 schema v1：object，支持 string / integer / number / boolean。", classes="editor-note")
                            yield TextArea(placeholder="工具参数 JSON Schema", id="nps-parameters", soft_wrap=True, classes="editor")
                            yield Input(placeholder="测试参数 JSON", id="nps-args", value="{}")
                        with Collapsible(title="VScript 主程序", collapsed=False):
                            yield Label("VScript 为插件主控入口。", classes="editor-note")
                            yield TextArea(placeholder="VScript source", id="nps-vscript", soft_wrap=True, classes="editor")
                        with Collapsible(title="可选 Python 扩展", collapsed=True):
                            yield Label("Python 在隔离进程执行；请仅声明最小能力。", classes="editor-note")
                            yield Input(placeholder="Python entrypoint（默认 main）", id="nps-python-entrypoint", value="main")
                            yield TextArea(placeholder="Python extension source（可留空）", id="nps-python", soft_wrap=True, classes="editor")
                        with Horizontal(classes="actions"):
                            yield Button("校验并保存 NPS", id="save-nps", variant="primary")
                            yield Button("测试 NPS", id="test-nps")
                        with Collapsible(title="导入 / 导出新版 NPS 包", collapsed=True):
                            yield Label("导入会校验 manifest、脚本入口与能力声明。", classes="editor-note")
                            yield TextArea(placeholder="NPS bundle JSON", id="nps-import-export", soft_wrap=True, classes="editor")
                            with Horizontal(classes="actions"):
                                yield Button("导入新版 JSON", id="import-nps")
                                yield Button("导出选中 NPS", id="export-nps")
                with VerticalScroll(id="records", classes="page"):
                    with Horizontal(classes="character-fields"):
                        yield Select([("全部记录", "all"), ("错误 / 失败", "errors"), ("对话", "conversation"), ("插件", "plugin"), ("日程", "schedule"), ("关系", "relationship")], value="all", id="runtime-log-filter")
                        yield Input(placeholder="搜索事件 / payload", id="runtime-log-search")
                        yield Button("筛选 / 刷新", id="refresh-runtime-logs")
                    yield Static(id="records-view", classes="listing")
                    with Collapsible(title="清理日志视图（不删除原始审计日志）", collapsed=True, id="runtime-log-maintenance", classes="editor-drawer debug-editor"):
                        yield Label("操作会记录新的审计事件；只设置可见水位，不修改 PyVDisk LogDisk 原始事件。", classes="editor-note")
                        yield Input(placeholder="输入 CLEAR LOG VIEW 确认隐藏旧记录", id="clear-runtime-logs-confirm")
                        yield Button("清除当前日志视图", id="clear-runtime-logs", variant="error")
                with VerticalScroll(id="storage", classes="page"):
                    yield Static(id="storage-view", classes="listing")
                    with Collapsible(title="⌕ 搜索长期记忆", collapsed=True, id="memory-search-tools", classes="editor-drawer"):
                        yield Label("基于语义搜索保存的长期记忆。", classes="editor-note")
                        yield Input(placeholder="记忆检索", id="memory-query")
                        yield Input(placeholder="角色 ID（可选）", id="memory-character")
                        yield Button("语义检索", id="search-memory")
                    with Collapsible(title="＋ 写入长期记忆", collapsed=True, id="memory-editor", classes="editor-drawer debug-editor"):
                        yield Label("人工写入会标记 operator 来源；Agent 仍可在对话中自动沉淀记忆。", classes="editor-note")
                        yield Input(placeholder="记忆文本", id="memory-text")
                        yield Button("保存长期记忆", id="save-memory", variant="primary")
                    yield Static(id="memory-results", classes="listing")
                    with Collapsible(title="⌕ 短期记忆与长期摘要查询", collapsed=True, id="memory-layer-query", classes="editor-drawer"):
                        yield Label("Conversation ID 最多 22 个 ASCII 字符。", classes="editor-note")
                        yield Input(placeholder="Conversation ID", id="memory-conversation-id")
                        yield Button("查看短期 / 长期记忆", id="refresh-memory-layers")
                        yield Static(id="memory-layers", classes="listing")
                    with Collapsible(title="＋ 编辑摘要 / 清理会话记忆", collapsed=True, id="summary-editor", classes="editor-drawer debug-editor"):
                        yield Label("更新摘要会覆盖所填 ID；删除会话短期记忆前请先查看上方内容。", classes="editor-note")
                        yield Input(placeholder="摘要 ID（留空新建；填写可覆盖）", id="long-term-summary-id")
                        yield TextArea(placeholder="长期摘要内容", id="long-term-summary", soft_wrap=True, classes="editor")
                        yield Button("保存长期摘要", id="save-summary", variant="primary")
                        with Collapsible(title="危险操作 · 删除摘要或清空会话短期记忆", collapsed=True, classes="danger-zone"):
                            yield Label("先在上方查询并核对会话内容，再执行清理。", classes="editor-note")
                            yield Button("删除长期摘要", id="delete-summary", variant="error")
                            yield Button("清空该会话短期记忆", id="clear-short-term", variant="error")
                    with Collapsible(title="⚠ 批量清理记忆", collapsed=True, id="memory-cleanup-editor", classes="editor-drawer debug-editor"):
                        yield Label("逐项清理，并逐字输入对应确认口令；语义长期记忆不会被清除。", classes="editor-note")
                        with Collapsible(title="清空全部短期记忆", collapsed=True, classes="danger-zone"):
                            yield Input(placeholder="输入 CLEAR SHORT TERM", id="clear-short-confirm")
                            yield Button("清空全部短期记忆", id="clear-all-short-term", variant="error")
                        with Collapsible(title="清空全部长期摘要", collapsed=True, classes="danger-zone"):
                            yield Input(placeholder="输入 CLEAR LONG TERM", id="clear-long-confirm")
                            yield Button("清空全部长期摘要", id="clear-all-long-term", variant="error")
                    yield Label("存储概况", classes="eyebrow")
                    yield Static(id="database-statistics", classes="listing")
                    yield Button("刷新存储统计", id="refresh-storage-statistics")
                    yield Label("会话历史（删除会话会清除 transcript 与短期记忆；长期摘要保留）", classes="eyebrow")
                    yield Static(id="conversation-history", classes="listing")
                    with Horizontal(classes="actions"):
                        yield Button("刷新会话", id="refresh-conversations")
                    with Collapsible(title="删除当前会话", collapsed=True, id="conversation-delete-editor", classes="editor-drawer debug-editor"):
                        yield Label("目标为上方短期 / 长期记忆查询所选的 Conversation ID。", classes="editor-note")
                        yield Button("删除会话及其对话记录", id="delete-conversation", variant="error")
                    with Collapsible(title="配置导出", collapsed=True, id="config-export-editor", classes="editor-drawer"):
                        yield Label("选择要包含的数据类别；密钥不会导出。", classes="editor-note")
                        yield SelectionList(
                            ("角色档案", "characters", True),
                            *[(label, namespace, True) for label, namespace in self.configuration_service.category_labels()],
                            id="config-categories",
                        )
                        with Horizontal(classes="actions"):
                            yield Button("全选类别", id="select-all-config-categories")
                            yield Button("清空选择", id="clear-config-categories")
                            yield Button("导出配置", id="export-config")
                    with Collapsible(title="导入 / 校验配置包", collapsed=True, id="config-import-editor", classes="editor-drawer debug-editor"):
                        yield Label("新格式 neo-agent/config/v2；导入会写入所选类别，需开启 Debug。", classes="editor-note")
                        yield TextArea(placeholder="粘贴 neo-agent/config/v2 配置包 JSON", id="config-json", soft_wrap=True, classes="editor")
                        yield Static("导入前先校验并查看将写入的记录数量。", id="config-preview", classes="listing")
                        with Horizontal(classes="actions"):
                            yield Button("校验 / 预览导入", id="preview-config")
                            yield Button("导入新格式配置", id="import-config", variant="primary")
                with VerticalScroll(id="channels", classes="page"):
                    yield Static(id="channel-list", classes="listing")
                    with Collapsible(title="＋ 编辑频道连接配置", collapsed=True, id="channel-editor", classes="editor-drawer debug-editor"):
                        yield Label("只填写公开连接参数；密钥由环境变量或受管凭据服务提供。", classes="editor-note")
                        yield Label("连接身份", classes="editor-section-title")
                        yield Input(placeholder="连接器 ID（必填）", id="channel-id")
                        yield Input(placeholder="平台与频道名称", id="channel-name")
                        yield Input(placeholder="平台类型（adapter）", id="channel-platform")
                        yield Input(placeholder="公开配置 JSON（不得放密钥）", id="channel-config")
                        yield Button("保存频道连接配置", id="save-channel", variant="primary")
                with VerticalScroll(id="settings", classes="page"):
                    yield Static(id="settings-view", classes="listing")
                    yield Label("模型密钥由环境变量提供，不写入 PyVDisk 配置备份。", classes="eyebrow")
                    yield Button("切换 Debug", id="toggle-debug", variant="warning")
                with VerticalScroll(id="cognition", classes="page"):
                    yield Static(id="cognition-status", classes="listing")
                    yield Button("刷新认知与审计状态", id="refresh-cognition")
                    with Collapsible(title="离线群聊回放", collapsed=True, id="cognition-replay-editor", classes="editor-drawer"):
                        yield Label("输入 IncomingMessage JSON 数组；只运行离线样例，不连接真实群平台。", classes="editor-note")
                        yield TextArea(id="replay-input", soft_wrap=True, classes="editor")
                        yield Button("运行离线回放", id="run-cognition-replay", variant="primary")
                        yield Static(id="cognition-replay-result", classes="listing")
                yield Label("↑↓ 选择 · Enter 打开 · R 刷新 · Q 退出", id="status")
        yield Footer()

    def on_collapsible_expanded(self, event: Collapsible.Expanded) -> None:
        """Keep each page focused on one top-level operation drawer at a time."""
        active = event.collapsible
        if "editor-drawer" not in active.classes:
            return

        page = active
        while page is not None and "page" not in page.classes:
            page = page.parent
        if page is None:
            return

        collapsed_other = False
        for other in page.query(".editor-drawer"):
            if other is active:
                continue
            # Preserve containing drawers when opening a nested editor; collapse
            # sibling and nested drawers so their fields don't crowd this workflow.
            ancestor = active.parent
            while ancestor is not None and ancestor is not other:
                ancestor = ancestor.parent
            if ancestor is other:
                continue
            if not other.collapsed:
                other.collapsed = True
                collapsed_other = True

        if collapsed_other:
            self.notify("同一页面仅展开一个操作面板，已收起其他面板。", timeout=2)

    def on_mount(self) -> None:
        # Model-backed itinerary/world generation is lazy so offline operation
        # and browsing the console never require credentials.
        if self.schedule_planner.model is None and (os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY")):
            try:
                self.schedule_planner.model = AgentRuntime._build_model()
                self.scene_service.model = self.schedule_planner.model
                self.scene_scheduler = SceneScheduler(self.store, model=self.schedule_planner.model, scenes=self.scene_service)
            except Exception:
                pass
        self._apply_debug_visibility()
        rows = self.store.characters()
        active = self.single_role.active()
        if not rows:
            self._populate_character_form(self._sample_character_profile())
            self._show_character_editor(True)
            self.active_view = "虚拟群友"
        elif active is not None:
            self._populate_character_form(active)
            self._show_character_editor(False)
        elif len(rows) > 1:
            self.active_view = "虚拟群友"
            self._show_character_editor(False)
        self.query_one("#nav", ListView).index = self.NAV_ITEMS.index(self.active_view)
        # Keep network/model calls and PyVDisk recovery out of Textual's UI
        # event loop. Otherwise a slow/unreachable model makes the entire TUI
        # appear frozen before it can process q, navigation, or Ctrl+C.
        self._run_scene_scheduler(generate=True)
        self.set_interval(5, self._run_scheduled_scene_tick)
        self.refresh_view()

    def _run_scheduled_scene_tick(self) -> None:
        from datetime import datetime, time
        generate = datetime.now().astimezone().time() >= time(0, 5)
        self._run_scene_scheduler(generate=generate)

    def _run_scene_scheduler(self, *, generate: bool = True) -> None:
        # The scheduler is also polled periodically. Never queue a second run
        # while a model request or storage operation from the previous run is
        # still in progress.
        # Before first-role setup there is nothing to schedule. Avoid touching
        # the DataDisk concurrently with the role-creation form in this state.
        if not self.store.characters():
            return
        if not self._scene_scheduler_lock.acquire(blocking=False):
            return
        try:
            self.run_worker(
                lambda: self._run_scene_scheduler_worker(generate=generate),
                name="scene-scheduler", group="scene-scheduler", thread=True,
                exclusive=False, exit_on_error=False,
            )
        except Exception:
            self._scene_scheduler_lock.release()
            raise

    def _run_scene_scheduler_worker(self, *, generate: bool) -> None:
        try:
            character = self.single_role.active()
            self.scene_scheduler.run_once(character=character, generate=generate and character is not None)
        except Exception as exc:
            summary = f"{type(exc).__name__}: {exc}"[:300]
            audit_id = "audit_" + hashlib.sha256(summary.encode("utf-8")).hexdigest()[:16]
            if self.store.get_document("scene_audits", audit_id) is None:
                self.store.save_document("scene_audits", audit_id, {
                    "action": "scene.scheduler.error", "summary": summary,
                    "occurred_at": datetime.now().astimezone().isoformat(),
                })
                self.store.append_event("scene.scheduler.error", {
                    "error_type": type(exc).__name__, "summary": summary,
                })
            current_date = date.today().isoformat()
            itinerary_id = "day_" + current_date.replace("-", "")
            itinerary = self.store.get_document("itineraries", itinerary_id)
            if itinerary is not None:
                retry_at = datetime.now().astimezone() + timedelta(minutes=15)
                self.store.save_document("itineraries", itinerary_id, {
                    **itinerary, "status": "failed", "error": summary,
                    "retry_at": retry_at.isoformat(),
                    "failed_at": datetime.now().astimezone().isoformat(),
                })
        finally:
            self._scene_scheduler_lock.release()
            try:
                self.call_from_thread(self._refresh_after_scene_scheduler)
            except RuntimeError:
                # The app may have been closed while an in-flight network call
                # was completing; its durable work is already finished.
                pass

    def _refresh_after_scene_scheduler(self) -> None:
        if self.active_view == "日程":
            self.query_one("#schedule-list", Static).update(self._schedule_listing())
        elif self.active_view == "环境与域":
            self.refresh_view()

    def _status_text(self) -> str:
        configured = bool(os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY"))
        return f"● Runtime 在线\n◉ PyVDisk 已连接\n◇ 模型 {'已配置' if configured else '未配置'}\n⌁ 生活场景调度活跃"

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        nav = self.query_one("#nav", ListView)
        if nav.index is not None:
            self.action_navigate(self.NAV_ITEMS[nav.index])

    def action_navigate_by_index(self, index: int) -> None:
        self.action_navigate(self.NAV_ITEMS[index % len(self.NAV_ITEMS)])

    def action_navigate(self, view: str) -> None:
        self.active_view = view
        nav = self.query_one("#nav", ListView)
        if view in self.NAV_ITEMS:
            nav.index = self.NAV_ITEMS.index(view)
        self.refresh_view()

    def action_refresh(self) -> None:
        self.query_one("#service-status", Static).update(self._status_text())
        self.refresh_view()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        action = event.button.id
        try:
            if self._is_manual_authoring(action) and not self._manual_authoring_allowed(action):
                raise PermissionError("人工创作/编辑入口仅在 Debug 开启时可用；Agent 自动创作不受此限制")
            if action == "send-chat": await self.send_chat()
            elif action == "select-primary-character": self.select_primary_character()
            elif action == "toggle-debug": self.toggle_debug()
            elif action == "run-cognition-replay": self.run_cognition_replay()
            elif action == "refresh-cognition": self.refresh_cognition_status()
            elif action == "save-character": self.save_character()
            elif action == "edit-character": self.open_character_editor()
            elif action == "cancel-character-edit": self.cancel_character_edit()
            elif action == "archive-character": self.archive_character()
            elif action == "append-event": self.append_event()
            elif action == "filter-events": self.refresh_events()
            elif action == "refresh-runtime-logs": self.refresh_runtime_logs()
            elif action == "clear-runtime-logs": self.clear_runtime_logs()
            elif action == "create-event-record": self.create_event_record()
            elif action == "update-event-record": self.update_event_record()
            elif action == "trigger-event-record": self.trigger_event_record()
            elif action == "delete-event-record": self.delete_event_record()
            elif action == "refresh-questions": self.refresh_questions()
            elif action == "resolve-question": self.resolve_question()
            elif action == "start-collaboration": self.start_collaboration()
            elif action == "resume-collaboration": self.resume_collaboration()
            elif action == "refresh-collaboration": self.refresh_collaboration()
            elif action == "create-schedule": self.create_schedule()
            elif action == "confirm-create-similar-schedule": self.confirm_create_similar_schedule()
            elif action == "filter-schedules": self._update("#schedule-list", self._schedule_listing())
            elif action == "update-schedule": self.update_schedule()
            elif action == "query-schedule-range": self.query_schedule_range()
            elif action == "find-free-slots": self.find_free_slots()
            elif action == "schedule-statistics": self.show_schedule_statistics()
            elif action == "schedule-details": self.show_schedule_details()
            elif action == "generate-schedule-suggestions": self.generate_temporary_suggestions()
            elif action == "apply-schedule-suggestion": self.apply_temporary_suggestion()
            elif action == "delete-schedule": self.delete_schedule()
            elif action == "confirm-schedule": self.decide_schedule(True)
            elif action == "reject-schedule": self.decide_schedule(False)
            elif action == "save-knowledge": self.save_knowledge()
            elif action == "search-knowledge": self.search_knowledge()
            elif action == "delete-knowledge": self.delete_knowledge()
            elif action == "save-base-knowledge": self.save_base_knowledge()
            elif action == "delete-base-knowledge": self.delete_base_knowledge()
            elif action == "record-relationship": self.record_relationship()
            elif action == "record-emotion": self.record_emotion()
            elif action == "analyze-emotion": self.analyze_emotion()
            elif action == "refresh-relationships": self.refresh_relationship_view()
            elif action == "save-entity": self.save_entity()
            elif action == "delete-entity": self.delete_entity()
            elif action == "save-environment": self.save_environment()
            elif action == "activate-environment": self.environment_service.activate(self._value("#environment-id"))
            elif action == "link-environment-domain": self.link_environment_domain(True)
            elif action == "unlink-environment-domain": self.link_environment_domain(False)
            elif action == "switch-domain": self.switch_domain()
            elif action == "delete-environment": self.delete_environment()
            elif action == "save-environment-object": self.save_environment_object()
            elif action == "delete-environment-object": self.delete_environment_object()
            elif action == "toggle-environment-object": self.toggle_environment_object()
            elif action == "delete-environment-connection": self.delete_environment_connection()
            elif action == "create-environment-connection": self.create_environment_connection()
            elif action == "save-domain": self.save_domain()
            elif action == "add-domain-environment": self.add_domain_environment()
            elif action == "remove-domain-environment": self.remove_domain_environment()
            elif action == "check-environment-move": self.check_environment_move()
            elif action == "log-vision-usage": self.log_vision_usage()
            elif action == "refresh-environment": pass
            elif action == "save-expression": self.save_expression()
            elif action == "delete-expression": self.delete_expression()
            elif action == "learn-user-expressions": self.learn_user_expressions()
            elif action == "clear-user-expressions": self.clear_user_expressions()
            elif action in ("enable-plugin", "disable-plugin"): self.toggle_plugin(action == "enable-plugin")
            elif action == "save-nps": self.save_nps()
            elif action == "test-nps": self.test_nps()
            elif action == "import-nps": self.import_nps()
            elif action == "export-nps": self.export_nps()
            elif action == "delete-nps": self.delete_nps()
            elif action == "save-memory": self.save_memory()
            elif action == "search-memory": self.search_memory()
            elif action == "save-summary": self.save_summary()
            elif action == "delete-summary": self.delete_summary()
            elif action == "refresh-memory-layers": self.refresh_memory_layers()
            elif action == "clear-short-term": self.clear_short_term()
            elif action == "clear-all-short-term": self.clear_all_short_term()
            elif action == "clear-all-long-term": self.clear_all_long_term()
            elif action == "refresh-storage-statistics": self.refresh_storage_statistics()
            elif action == "refresh-conversations": self.refresh_conversations()
            elif action == "delete-conversation": self.delete_conversation()
            elif action == "export-config": self.export_config()
            elif action == "preview-config": self.preview_config()
            elif action == "import-config": self.import_config()
            elif action == "select-all-config-categories": self.query_one("#config-categories", SelectionList).select_all()
            elif action == "clear-config-categories": self.query_one("#config-categories", SelectionList).deselect_all()
            elif action == "save-channel": self.save_channel()
        except Exception as exc:
            self.notify(f"{type(exc).__name__}: {exc}", title="操作失败", severity="error", timeout=8)
            self.store.append_event("tui.operation.failed", {
                "action": action, "error_type": type(exc).__name__,
            })
        self.refresh_view()

    @staticmethod
    def _is_manual_authoring(action: str | None) -> bool:
        if not action or action in {"toggle-debug", "edit-character", "cancel-character-edit"}:
            return False
        if action.startswith((
            "create-", "save-", "update-", "append-", "record-", "add-",
            "link-", "unlink-", "remove-", "import-", "delete-", "clear-",
            "enable-", "disable-", "activate-", "switch-", "toggle-",
            "confirm-", "reject-", "trigger-",
        )):
            return True
        return action in {
            "learn-user-expressions", "archive-character", "start-collaboration",
            "resume-collaboration", "apply-schedule-suggestion", "log-vision-usage",
            "clear-runtime-logs",
        }

    def _manual_authoring_allowed(self, action: str | None) -> bool:
        if self.controls.debug:
            return True
        # The first-run role wizard is the sole manual-write exception: a role
        # is required before the agent can operate. No other authoring is open.
        return action == "save-character" and not self.store.characters()

    def _apply_debug_visibility(self) -> None:
        if not self.is_mounted:
            return
        for editor in self.query(".debug-editor"):
            editor.display = self.controls.debug
        for button in self.query(Button):
            action = button.id or ""
            if self._is_manual_authoring(action):
                button.display = self._manual_authoring_allowed(action)
        self.query_one("#toggle-debug", Button).label = f"Debug：{'开启' if self.controls.debug else '关闭'}（点击切换）"
        active = self.single_role.active()
        self.query_one("#edit-character", Button).display = bool(active) and self.controls.debug and not self.query_one("#character-editor", Vertical).display
        if active and not self.controls.debug and self.query_one("#character-editor", Vertical).display:
            self._populate_character_form(active)
            self._show_character_editor(False)

    def toggle_debug(self) -> None:
        self.controls.set_debug(not self.controls.debug)
        self._apply_debug_visibility()

    def select_primary_character(self) -> None:
        selected = self.query_one("#primary-character", Select).value
        if selected in (Select.NULL, None):
            raise ValueError("请先选择要保留的主角色")
        character = self.single_role.initialize(str(selected))
        self._populate_character_form(character)
        self._show_character_editor(False)
        self._apply_debug_visibility()

    def run_cognition_replay(self) -> None:
        raw = self.query_one("#replay-input", TextArea).text.strip()
        rows = json.loads(raw or "[]")
        if not isinstance(rows, list):
            raise ValueError("回放输入必须是 JSON 数组")
        messages = [IncomingMessage(**item) for item in rows]
        candidates = self.group_reply_gate.replay(messages)
        for candidate in candidates:
            self.store.append_event("cognition.group_replay.decision", {
                "message_id": candidate.message_id, "group_id": candidate.group_id,
                "decision": candidate.decision, "reason": candidate.reason,
                "relevance": candidate.relevance, "confidence": candidate.confidence,
                "activity": candidate.activity, "cooldown": candidate.cooldown,
            })
        self._update("#cognition-replay-result", "\n\n".join(
            f"{row.group_id}/{row.message_id} · {row.decision} · {row.reason} · 相关 {row.relevance:.2f} / 置信 {row.confidence:.2f} / 活跃 {row.activity:.2f}"
            for row in candidates) or "无回放项目。")
        self.refresh_cognition_status()

    def refresh_cognition_status(self) -> None:
        rows = self.store.events(200)
        selected = [row for row in rows if row.get("message", "").startswith(("cognition.", "agent.action."))]
        text = "\n\n".join(f"{row.get('message')} · {json.dumps(row.get('fields', {}), ensure_ascii=False)}" for row in reversed(selected[-80:]))
        self._update("#cognition-status", text or "暂无认知决策或操作审计记录。")

    def _value(self, selector: str) -> str:
        return self.query_one(selector, Input).value.strip()

    def _textarea(self, selector: str) -> str:
        return self.query_one(selector, TextArea).text.strip()

    def _update(self, selector: str, value: str) -> None:
        self.query_one(selector, Static).update(value)

    def refresh_questions(self) -> None:
        rows = self.question_service.pending()
        self._update("#question-list", "\n\n".join(
            f"{row['id']} · {row.get('created_at', '')} · 会话 {row.get('conversation_id', 'default')}\n"
            f"问题：{row.get('question', '')}\n背景：{row.get('context', '')}"
            for row in rows
        ) or "当前没有待回答的问题。")
    def refresh_collaboration(self) -> None:
        rows = [item for item in self.store.list_documents("workflows") if item.get("kind") == "multi_agent_task"]
        self._update("#collaboration-runs", "\n\n".join(
            f"{row['id']} · {row.get('status')} · {row.get('task', {}).get('title', '')}\n"
            f"进度：{row.get('next_step', 0)}/{len(row.get('plan', []))} 步 · "
            f"问题：{row.get('question_id', '无')} · {row.get('verification', {}).get('reason', '')}\n"
            f"VFS 工作区：{row.get('workspace', '未分配')}"
            for row in rows[:30]
        ) or "暂无协作任务。")

    def start_collaboration(self) -> None:
        from neo_agent.services.collaboration import MultiAgentCoordinator
        coordinator = MultiAgentCoordinator(self.store, model=self.coordinator_model)
        result = coordinator.run_task(
            title=self._value("#collaboration-title"),
            description=self._textarea("#collaboration-description"),
            requirements=self._value("#collaboration-requirements"),
            completion_criteria=self._value("#collaboration-criteria"),
        )
        self._update("#collaboration-run-id", result["id"])
        self.notify(f"协作任务状态：{result['status']} · ID {result['id']}", title="任务执行")
        self.refresh_collaboration()

    def resume_collaboration(self) -> None:
        from neo_agent.services.collaboration import MultiAgentCoordinator
        coordinator = MultiAgentCoordinator(self.store, model=self.coordinator_model)
        result = coordinator.resume(self._value("#collaboration-run-id"))
        self.notify(f"协作任务状态：{result['status']} · ID {result['id']}", title="任务恢复")
        self.refresh_questions()
        self.refresh_collaboration()

    def resolve_question(self) -> None:
        row = self.question_service.resolve(self._value("#question-id"), self._value("#question-answer"))
        self.notify(f"回答已保存，会话 {row.get('conversation_id', 'default')} 可继续。", title="已提交")
        self._update("#question-answer", "")
        self.refresh_questions()

    def _schedule_listing(self) -> str:
        from datetime import datetime, timedelta

        date_filter = "all"
        status_filter = "all"
        if self.is_mounted:
            date_value = self.query_one("#schedule-date-filter", Select).value
            status_value = self.query_one("#schedule-status-filter", Select).value
            date_filter = str(date_value) if date_value is not Select.NULL else "all"
            status_filter = str(status_value) if status_value is not Select.NULL else "all"
        today = datetime.now().astimezone().date()
        if date_filter == "today":
            start_date = end_date = today
        elif date_filter == "tomorrow":
            start_date = end_date = today + timedelta(days=1)
        elif date_filter == "week":
            start_date = today - timedelta(days=today.weekday())
            end_date = start_date + timedelta(days=6)
        else:
            start_date = end_date = None

        rows = []
        for item in self.store.schedules():
            if status_filter != "all" and item.get("status", "pending") != status_filter:
                continue
            try:
                due = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            except (KeyError, TypeError, ValueError):
                if date_filter == "all":
                    rows.append(f"⚠ 无效日程时间 · {item.get('title', item.get('id', '未知记录'))} [{item.get('id', '')}] · {item.get('due_at', '缺少 due_at')}")
                continue
            if start_date is not None and not (start_date <= due.astimezone().date() <= end_date):
                continue
            end = f" — {item['end_at']}" if item.get("end_at") else " — 持续至下一条场景日程 / 当地日终"
            place = self.store.get_document("places", item.get("place_id", "")) if item.get("place_id") else None
            area = self.store.get_document("areas", item.get("area_id", "")) if item.get("area_id") else None
            scene = f" · 场景：{place.get('name', '')} / {area.get('name', '')}" if place and area else " · 无场景绑定"
            category = {"agent": "Agent 个人", "user": "用户个人（只读）", "shared": "双方共同"}.get(item.get("category", "agent"), item.get("category"))
            rows.append(f"◷ {item['due_at']}{end} · {item['title']} [{item['id']}]\n  {item.get('description', '')}\n  归属：{category} · 参与方：{'、'.join(item.get('participants', []))} · 来源：{item.get('schedule_source', '记录')}\n  类型：{item.get('type', 'appointment')} · 状态：{item.get('status', 'pending')}{scene}")
        from datetime import datetime
        today = datetime.now().astimezone().date().isoformat()
        itinerary = next((row for row in self.store.list_documents("itineraries") if row.get("local_date") == today), None)
        timeline = [row for row in self.store.schedules() if row.get("due_at", "").startswith(today)]
        timeline.sort(key=lambda row: row.get("due_at", ""))
        timeline_text = "\n".join(
            f"  {row['due_at'][11:16]}–{row.get('end_at', '')[11:16] if row.get('end_at') else '后续切换'} · {row.get('title')} · {'共同' if row.get('category') == 'shared' else 'Agent'}"
            for row in timeline
        ) or "  今天尚无时间条目。"
        decisions = self.store.list_documents("schedule_decisions")[:8]
        decision_text = "\n".join(f"  {row.get('summary', '')} [{row.get('action', '')}]" for row in decisions) or "  暂无冲突决定。"
        status_text = f"今日计划：{itinerary.get('status')} · {itinerary.get('timezone')} · {itinerary.get('error') or itinerary.get('summary', '')}" if itinerary else "今日计划尚未生成。"
        current = self.scene_service.current_context()
        return ("今日生活时间线\n" + timeline_text + "\n" + status_text + "\n\n共同日程冲突协调\n" + decision_text + "\n\n全部日程记录\n" + ("\n\n".join(rows) or "当前筛选条件下暂无日程。") + "\n\n" + current)

    def _event_listing(self) -> str:
        event_type = self._value("#event-filter") if self.is_mounted else ""
        rows = self.store.query_events(event_type=event_type or None, limit=100)
        return "\n\n".join(f"#{item.get('sequence', '-')} · {item.get('message')}\n  {item.get('fields', {}).get('payload', {})}" for item in reversed(rows)) or "暂无事件。"

    def refresh_events(self) -> None:
        self._update("#events-list", self._event_listing())
        self._update("#event-record-list", "\n\n".join(
            f"{item['id']} · {item.get('title', '')} [{item.get('status', 'pending')}]\n"
            f"{item.get('event_type', item.get('type', ''))} · {item.get('details', item.get('description', ''))}"
            f"{(' · 工作流 ' + item['workflow_id']) if item.get('workflow_id') else ''}"
            f"\n  VFS 工作区：{item.get('workspace', '未分配')}"
            for item in self.store.event_records()
        ) or "暂无可管理事件。")

    def create_event_record(self) -> None:
        self.store.create_event_record(self._value("#event-record-id"), {
            "title": self._value("#event-record-title"), "event_type": self._value("#event-record-type"),
            "details": self._value("#event-record-details"), "status": self._value("#event-record-status") or "pending",
        })

    def update_event_record(self) -> None:
        event_id = self._value("#event-record-id")
        status = self._value("#event-record-status")
        if not status:
            raise ValueError("事件状态不能为空")
        record = self.store.get_document("event_records", event_id)
        if not record:
            raise KeyError("找不到事件记录")
        if record.get("workflow_id"):
            raise ValueError("该记录由协作工作流驱动，请在任务编排中推进状态")
        self.store.update_event_record(event_id, {"status": status})

    def trigger_event_record(self) -> None:
        event_id = self._value("#event-record-id")
        record = self.store.get_document("event_records", event_id)
        if not record:
            raise KeyError("找不到事件记录")
        if record.get("workflow_id"):
            raise ValueError("该记录由协作工作流驱动，不能手动触发")
        if record.get("status") != "pending":
            raise ValueError("只有 pending 事件可以触发")
        self.store.update_event_record(event_id, {"status": "triggered"})
        self.store.append_event(record.get("event_type") or "event.triggered", {"record_id": event_id, "details": record.get("details", ""), "source": "operator"})

    def delete_event_record(self) -> None:
        event_id = self._value("#event-record-id")
        record = self.store.get_document("event_records", event_id)
        if not record:
            raise KeyError("找不到事件记录")
        if record.get("workflow_id"):
            raise ValueError("该记录关联持久化协作任务，不能单独删除")
        self.store.delete_event_record(event_id)

    def append_event(self) -> None:
        event_type, summary = self._value("#event-type"), self._value("#event-summary")
        if not event_type or not summary: raise ValueError("事件类型与摘要不能为空")
        self.store.append_event(event_type, {"summary": summary, "source": "operator"})

    def create_schedule(self) -> None:
        schedule_type = self._value("#schedule-type").casefold() or "appointment"
        priority = self._value("#schedule-priority").casefold()
        if priority == "normal":
            priority = "medium"
        if priority and priority not in {"low", "medium", "high", "critical"}:
            raise ValueError("优先级必须是 low / medium / high / critical")
        schedule = {
            "title": self._value("#schedule-title"), "due_at": self._value("#schedule-due"),
            "description": self._value("#schedule-description"),
            "type": schedule_type,
            "category": str(self.query_one("#schedule-category", Select).value),
            "participants": (["agent", "user"] if self.query_one("#schedule-category", Select).value == "shared"
                             else [str(self.query_one("#schedule-category", Select).value)]),
            "schedule_source": "debug_manual",
            "collaboration_status": "pending" if schedule_type == "temporary" else "not_required",
            "is_queryable": schedule_type != "temporary",
        }
        if priority:
            schedule["priority"] = priority
        if schedule_type == "recurring":
            weekday = self._value("#schedule-weekday")
            schedule["weekday"] = int(weekday) if weekday else -1
            schedule["recurrence_pattern"] = self._value("#schedule-recurrence")
        end_at = self._value("#schedule-end")
        if end_at:
            schedule["end_at"] = end_at
        similar = self.schedule_planner.compare_similar(schedule)
        if similar:
            self._pending_similar_schedule = {"id": self._value("#schedule-id"), "schedule": schedule}
            details = "\n\n".join(
                f"{row['schedule'].get('title', '')} [{row['schedule']['id']}] · 相似度 {row['similarity']:.2f}\n{row['reason']}"
                for row in similar
            )
            self._update("#schedule-analysis", "发现可能重复的日程，请复核后决定是否继续：\n\n" + details)
            self.query_one("#confirm-create-similar-schedule", Button).disabled = False
            self.notify("发现相似日程；尚未创建。请复核后再明确确认。", title="重复日程检查", severity="warning")
            return
        self._pending_similar_schedule = None
        self.query_one("#confirm-create-similar-schedule", Button).disabled = True
        record = self.store.create_schedule(self._value("#schedule-id"), schedule)
        self.notify(f"已创建日程记录：{record['title']}", title="日程")

    def confirm_create_similar_schedule(self) -> None:
        if self._pending_similar_schedule is None:
            raise ValueError("没有等待复核的相似日程")
        pending = self._pending_similar_schedule
        record = self.store.create_schedule(pending["id"], pending["schedule"])
        self._pending_similar_schedule = None
        self.query_one("#confirm-create-similar-schedule", Button).disabled = True
        self.notify(f"已按复核决定创建：{record['title']}", title="日程")

    def update_schedule(self) -> None:
        schedule_id = self._value("#schedule-edit-id")
        current = self.store.get_schedule(schedule_id)
        if current is None:
            raise KeyError("找不到要更新的日程")
        changes = {}
        for selector, key in (("#schedule-edit-title", "title"), ("#schedule-edit-due", "due_at"),
                              ("#schedule-edit-description", "description"), ("#schedule-edit-end", "end_at"),
                              ("#schedule-edit-type", "type"), ("#schedule-edit-priority", "priority"),
                              ("#schedule-edit-recurrence", "recurrence_pattern")):
            value = self._value(selector)
            if value:
                changes[key] = value
        weekday = self._value("#schedule-edit-weekday")
        if weekday:
            changes["weekday"] = int(weekday)
        if not changes:
            raise ValueError("至少填写一个要更新的字段")
        self.store.update_schedule(schedule_id, changes)
        self.notify(f"已更新日程：{schedule_id}", title="日程")

    def _schedule_window(self) -> tuple[str, str]:
        start, end = self._value("#schedule-range-start"), self._value("#schedule-range-end")
        if not start or not end:
            raise ValueError("请填写查询范围的起止时间")
        return start, end

    def query_schedule_range(self) -> None:
        start, end = self._schedule_window()
        rows = self.store.schedules_in_range(start, end, queryable_only=False)
        text = "\n\n".join(
            f"{item['id']} · {item.get('title', '')} [{item.get('status', 'pending')}]\n"
            f"{item['due_at']} → {item.get('end_at', '（未设置结束时间）')}\n{item.get('description', '')}"
            for item in rows
        ) or "该时间范围内没有日程。"
        self._update("#schedule-analysis", text)

    def find_free_slots(self) -> None:
        start, end = self._schedule_window()
        minutes = int(self._value("#schedule-free-minutes") or "30")
        rows = self.store.free_time_slots(start, end, duration_minutes=minutes)
        text = "\n".join(f"{item['start_at']} → {item['end_at']}" for item in rows)
        self._update("#schedule-analysis", text or f"没有不少于 {minutes} 分钟的空闲时段。")

    def generate_temporary_suggestions(self) -> None:
        start, end = self._schedule_window()
        if self.schedule_planner.model is None:
            # Reuse the configured LangChain provider and keep the planning
            # path lazy, so browsing the console does not require API secrets.
            self.schedule_planner.model = AgentRuntime._build_model()
        self._schedule_suggestions = self.schedule_planner.temporary_suggestions(
            start, end,
            duration_minutes=int(self._value("#schedule-suggestion-minutes") or "60"),
            character_name=self._value("#schedule-character-name") or "智能体",
            hobbies=self._value("#schedule-character-hobbies") or "阅读、学习",
            context=self._value("#schedule-suggestion-context"),
        )
        if not self._schedule_suggestions:
            self._update("#schedule-suggestions", "所选时间范围内没有满足时长要求的空闲时段。")
            return
        lines = []
        for index, suggestion in enumerate(self._schedule_suggestions, start=1):
            lines.append(
                f"{index}. {suggestion['title']} · {suggestion['due_at']} → {suggestion['end_at']}\n"
                f"   {suggestion.get('description', '')}\n"
                f"   用户参与：{'是' if suggestion.get('involves_user') else '否'} · 理由：{suggestion['reason']}"
            )
        self._update("#schedule-suggestions", "\n\n".join(lines))

    def apply_temporary_suggestion(self) -> None:
        if not self._schedule_suggestions:
            raise ValueError("请先生成活动建议")
        try:
            index = int(self._value("#schedule-suggestion-index")) - 1
        except ValueError as exc:
            raise ValueError("建议编号必须是正整数") from exc
        if not 0 <= index < len(self._schedule_suggestions):
            raise ValueError("建议编号超出范围")
        suggestion = self._schedule_suggestions[index]
        self.query_one("#schedule-id", Input).value = uuid.uuid4().hex[:20]
        self.query_one("#schedule-title", Input).value = suggestion["title"]
        self.query_one("#schedule-due", Input).value = suggestion["due_at"]
        self.query_one("#schedule-end", Input).value = suggestion["end_at"]
        self.query_one("#schedule-description", Input).value = suggestion.get("description", "")
        self.query_one("#schedule-type", Input).value = "temporary"
        self.query_one("#schedule-priority", Input).value = "low"
        self.query_one("#schedule-category", Select).value = "shared" if suggestion.get("involves_user") else "agent"
        self.notify("建议已填入日程表单；请检查并确认后写入日程记录。", title="待确认建议")

    def show_schedule_statistics(self) -> None:
        stats = self.store.schedule_statistics()
        lines = [f"日程总数：{stats['total']}", f"待确认协作：{stats['pending_collaboration']}"]
        for title, key in (("按状态", "by_status"), ("按类型", "by_type"), ("按优先级", "by_priority")):
            lines.append(title + "：" + ("、".join(f"{name} {count}" for name, count in sorted(stats[key].items())) or "无"))
        self._update("#schedule-analysis", "\n".join(lines))

    def show_schedule_details(self) -> None:
        schedule_id = self._value("#schedule-detail-id")
        item = self.store.get_schedule(schedule_id)
        if item is None:
            raise KeyError(f"找不到日程：{schedule_id}")
        self._update("#schedule-analysis", "\n".join((
            f"{item.get('title', '')} [{item['id']}]", f"类型：{item.get('type', 'appointment')}",
            f"优先级：{item.get('priority', 'medium')} · 状态：{item.get('status', 'pending')}",
            f"时间：{item['due_at']} → {item.get('end_at', '未设置')}",
            f"协作：{item.get('collaboration_status', 'not_required')} · 可查询：{item.get('is_queryable', True)}",
            f"描述：{item.get('description', '') or '（无）'}", f"创建：{item.get('created_at', '未知')}",
        )))

    def delete_schedule(self) -> None:
        schedule_id = self._value("#schedule-delete-id") or self._value("#schedule-edit-id")
        if not self.store.delete_schedule(schedule_id): raise KeyError("找不到该日程")

    def decide_schedule(self, confirmed: bool) -> None:
        schedule_id = self._value("#schedule-delete-id") or self._value("#schedule-edit-id") or self._value("#schedule-id")
        self.store.confirm_schedule(schedule_id, confirmed)

    @staticmethod
    def _sample_character_profile() -> dict[str, str]:
        return {
            "name": "林依", "gender": "女", "role": "女高中生",
            "age": "17", "height": "160cm", "weight": "50kg",
            "hobby": "听歌、散步、收集可爱的文具",
            "personality": "开朗但不吵闹，待人真诚，偶尔有点害羞。熟悉之后会变得健谈，喜欢用轻松自然的方式关心朋友。",
            "background": "就读于一所普通高中，平时认真上课，也会和朋友分享校园里的趣事。喜欢在放学后散步、听歌；遇到新鲜事时会忍不住多问几句。以上只是示范设定，可以自由修改或全部重写。",
        }

    def _populate_character_form(self, character: dict[str, Any]) -> None:
        for field in ("name", "gender", "role", "age", "height", "weight", "hobby"):
            self.query_one(f"#character-{field}", Input).value = str(character.get(field, ""))
        self.query_one("#character-personality", TextArea).text = str(character.get("personality", ""))
        self.query_one("#character-background", TextArea).text = str(character.get("background", ""))
        from rich.markup import escape
        details = [
            f"[bold #55e6c1]{escape(str(character.get('name', '未命名角色')))}[/bold #55e6c1]",
            f"{escape(str(character.get('gender', '未设置')))} · {escape(str(character.get('role', '身份未设置')))} · {escape(str(character.get('age', '年龄未设置')))} 岁",
            f"身高 {escape(str(character.get('height', '未设置')))} · 体重 {escape(str(character.get('weight', '未设置')))} · 爱好：{escape(str(character.get('hobby', '未设置')))}",
            f"角色 ID：{escape(str(character.get('id', '保存后生成')))}",
            "",
            f"[bold]性格[/bold]  {escape(str(character.get('personality', '尚未填写')))}",
            "",
            f"[bold]背景[/bold]  {escape(str(character.get('background', '尚未填写')))}",
        ]
        self.query_one("#character-profile", Static).update("\n".join(details))

    def _show_character_editor(self, opened: bool) -> None:
        editor = self.query_one("#character-editor", Vertical)
        editor.display = opened
        active = self.single_role.active()
        self.query_one("#character-profile", Static).display = bool(active) and not opened
        self.query_one("#edit-character", Button).display = bool(active) and self.controls.debug and not opened
        self.query_one("#cancel-character-edit", Button).display = opened and bool(active)
        self.query_one("#save-character", Button).label = "创建角色" if not self.store.characters() else "保存设定"

    def open_character_editor(self) -> None:
        if not self.controls.debug:
            raise PermissionError("请先开启 Debug 才能编辑角色设定")
        character = self.single_role.active()
        if character is None:
            raise ValueError("请先选择唯一主角色")
        self._populate_character_form(character)
        self._show_character_editor(True)

    def cancel_character_edit(self) -> None:
        active = self.single_role.active()
        if active:
            self._populate_character_form(active)
        self._show_character_editor(False)

    def save_character(self) -> None:
        active = self.single_role.active()
        existing = self.store.characters()
        cid = active["id"] if active else uuid.uuid4().hex[:12]
        old = self.store.character(cid) or {}
        name = self._value("#character-name") or old.get("name", "")
        fields = {
            "name": name, "gender": self._value("#character-gender"),
            "role": self._value("#character-role"), "age": self._value("#character-age"),
            "height": self._value("#character-height"), "weight": self._value("#character-weight"),
            "hobby": self._value("#character-hobby"),
            "personality": self._textarea("#character-personality"),
            "background": self._textarea("#character-background"),
        }
        profile = {key: (value if value else old.get(key, "")) for key, value in fields.items()}
        profile["system_prompt"] = profile["personality"]
        profile["status"] = old.get("status", "active")
        if not existing:
            self.single_role.save_initial(cid, profile)
            self.notify(f"角色已创建，自动生成 ID：{cid}", title="角色初始化")
        elif active is None:
            raise ValueError("检测到多个活动角色，请先选择唯一主角色并归档其余角色")
        else:
            self.store.save_character(cid, profile)
            self.notify("角色设定已保存", title="保存完成")
        self._populate_character_form(self.store.character(cid) or {**profile, "id": cid})
        self._show_character_editor(False)
        self._apply_debug_visibility()

    def archive_character(self) -> None:
        if len(self.store.characters()) <= 1:
            raise ValueError("必须保留唯一活动角色；有多个角色时请先选择主角色并归档其余角色")
        active = self.single_role.active()
        if active is None:
            raise ValueError("请先选择唯一主角色")
        self.store.archive_character(active["id"])
        self.store.write_json("/runtime/active-character.json", {})
        self._apply_debug_visibility()

    def _character_listing(self) -> str:
        return "\n\n".join(
            f"◈ {c['name']} [{c['id']}] · {c.get('status', 'active')}\n"
            f"{c.get('gender', '')} · {c.get('role', '')} · {c.get('age', '')}岁 · {c.get('height', '')} / {c.get('weight', '')}\n"
            f"性格：{c.get('personality', '')}\n爱好：{c.get('hobby', '')}\n背景：{c.get('background', '')}"
            for c in self.store.characters()
        ) or "暂无角色。"

    @staticmethod
    def _character_prompt(character: dict[str, Any]) -> str:
        # An explicit prompt is authoritative; profile metadata is not prompt text.
        explicit = character.get("system_prompt")
        if explicit:
            return str(explicit)
        return str(character.get("personality") or "")

    def _render_transcript(self, character: dict) -> str:
        turns = self.store.read_json(f"/runtime/conversations/{character['id']}.json", default=[])[-10:]
        lines = [f"{character['name']} · 最近对话"]
        for turn in turns: lines.extend((f"你：{turn['user']}", f"{character['name']}：{turn['assistant']}", ""))
        return "\n".join(lines)

    async def send_chat(self) -> None:
        text = self._textarea("#chat-input")
        if not text: return
        character = self.single_role.active()
        if not character:
            raise ValueError("请先完成角色初始化；若存在多个角色，请在“虚拟群友”中选择唯一主角色")
        self.query_one("#chat-input", TextArea).clear()
        log = self.query_one("#chat-log", Static)
        log.update(f"{character['name']} 正在思考…")
        try:
            runtime = AgentRuntime(self.store, plugin_registry=self.plugin_registry)
            response = await asyncio.to_thread(runtime.chat, text, conversation_id=character["id"], system_prompt=self._character_prompt(character))
            log.update(self._render_transcript(character))
        except Exception as exc:
            log.update(f"对话失败：{type(exc).__name__}: {exc}")
            raise

    def save_knowledge(self) -> None:
        self.store.save_document("knowledge", self._value("#knowledge-id"), {"title": self._value("#knowledge-title"), "content": self._textarea("#knowledge-content"), "source": "operator"})

    def search_knowledge(self) -> None:
        q = self._value("#knowledge-search").casefold()
        entries = self.store.list_documents("knowledge")
        base = self.store.list_documents("base_knowledge")
        if q:
            entries = [e for e in entries if q in (e.get("title", "") + e.get("content", "")).casefold()]
            base = [e for e in base if q in (e.get("entity_name", "") + e.get("content", "") + e.get("category", "")).casefold()]
        self._update("#knowledge-list", self._format_docs(entries) + "\n\n基础知识：\n" + self._format_docs([{"id": item["id"], "title": f"{item.get('entity_name', '')} · {item.get('category', '')} · 置信度 {item.get('confidence', 1)}", "content": item.get("content", "")} for item in base]))

    def save_base_knowledge(self) -> None:
        confidence = float(self._value("#base-knowledge-confidence") or 1)
        if not 0 <= confidence <= 1:
            raise ValueError("置信度必须介于 0 与 1")
        self.store.save_document("base_knowledge", self._value("#base-knowledge-id"), {
            "entity_name": self._value("#base-knowledge-entity"),
            "category": self._value("#base-knowledge-category"),
            "confidence": confidence, "content": self._textarea("#base-knowledge-content"),
        })

    def delete_base_knowledge(self) -> None:
        if not self.store.delete_document("base_knowledge", self._value("#base-knowledge-id")):
            raise KeyError("找不到基础知识")

    def delete_knowledge(self) -> None:
        if not self.store.delete_document("knowledge", self._value("#knowledge-id")): raise KeyError("找不到知识条目")

    @staticmethod
    def _format_docs(entries: list[dict]) -> str:
        return "\n\n".join(f"{item['id']} · {item.get('title', '')}\n{item.get('content', '')}" for item in entries) or "暂无记录。"

    def record_relationship(self) -> None:
        from neo_agent.runtime import RelationshipService
        rid = self._value("#relationship-id")
        delta = float(self._value("#relationship-delta") or 0)
        confidence = float(self._value("#relationship-confidence") or 0)
        if not 0 <= confidence <= 1:
            raise ValueError("关系置信度必须介于 0 与 1")
        round_id = self._value("#relationship-round-id") or None
        RelationshipService(self.store).record_interaction(
            rid, note=f"{self._value('#relationship-peer')}: {self._value('#relationship-note')}",
            delta=delta, confidence=confidence, round_id=round_id,
        )

    def record_emotion(self) -> None:
        tone = self._value("#emotion-tone")
        if not tone:
            raise ValueError("情绪标签不能为空")
        score = float(self._value("#emotion-score") or 0)
        if not -1 <= score <= 1:
            raise ValueError("情绪分值必须介于 -1 与 1")
        relationship_id = self._value("#relationship-id") or "unassigned"
        self.store.add_emotion(relationship_id, tone, score, evidence=self._value("#emotion-evidence"))

    def analyze_emotion(self) -> None:
        relationship_id = self._value("#relationship-id")
        if not relationship_id:
            raise ValueError("请先填写关系 ID")
        conversation_id = self._value("#emotion-conversation-id") or "default"
        transcript = self.store.read_json(f"/runtime/conversations/{conversation_id}.json", default=[])
        messages = []
        for turn in transcript[-30:]:
            messages.extend(({"role": "user", "content": turn.get("user", "")},
                             {"role": "assistant", "content": turn.get("assistant", "")}))
        profile = self.store.character(conversation_id) or {}
        runtime = AgentRuntime(self.store, plugin_registry=self.plugin_registry)
        from neo_agent.runtime import EmotionService
        EmotionService(self.store, runtime.model).analyze(
            relationship_id, messages, character_name=profile.get("name", "Agent"),
            character_settings=self._character_prompt(profile) if profile else "",
        )

    def refresh_relationship_view(self) -> None:
        """Render a compact relationship radar and chronological topic timeline."""
        if not self.is_mounted:
            return
        relationship_id = self._value("#relationship-id")
        conversation_id = self._value("#emotion-conversation-id") or "default"
        emotions = sorted(
            self.store.emotion_history(relationship_id or None),
            key=lambda row: row.get("created_at", ""), reverse=True,
        )
        if emotions:
            latest = emotions[0]
            dimensions = latest.get("dimensions", {})
            labels = (("warmth", "温暖"), ("trust", "信任"), ("familiarity", "熟悉"), ("tension", "紧张"))
            bars = []
            for key, label in labels:
                try:
                    score = max(0, min(100, float(dimensions.get(key, 0))))
                except (TypeError, ValueError):
                    score = 0
                filled = round(score / 5)
                bars.append(f"{label:<4} {'█' * filled}{'·' * (20 - filled)} {score:>5.1f}/100")
            overall = float(latest.get("overall_score", latest.get("score", 0)))
            overall_fill = max(0, min(20, round(overall / 5)))
            radar = (
                f"{latest.get('relationship_id', '')} · {latest.get('relationship_type', latest.get('tone', '关系印象'))} · "
                f"{latest.get('sentiment', '未标注')} · {latest.get('emotional_tone', '')} · {latest.get('created_at', '')}\n"
                f"总体关系分  {'█' * overall_fill}{'·' * (20 - overall_fill)} {overall:.1f}/100\n"
                + "\n".join(bars)
                + f"\n印象：{latest.get('impression', '')}\n依据：{latest.get('analysis', '')}"
            )
        else:
            radar = "暂无该关系的情绪分析；选择会话并运行‘分析所选关系’后，将显示可解释的关系维度。"
        self._update("#emotion-radar", radar)

        summaries = sorted(
            self.store.long_term_summaries(conversation_id),
            key=lambda row: row.get("created_at", ""),
        )
        timeline_rows = []
        for index, row in enumerate(summaries):
            date = row.get("created_at", "")
            rounds = max(0, int(row.get("rounds", 0) or 0))
            messages = max(0, int(row.get("message_count", 0) or 0))
            topics = row.get("topics", row.get("key_topics", []))
            topic_text = "、".join(str(topic) for topic in topics) if isinstance(topics, list) else str(topics or "")
            timeline_rows.append(
                f"{'●' if index == len(summaries) - 1 else '○'} {date} · {row['id']} · {rounds} 轮 / {messages} 条"
                f"\n  {row.get('summary', '')}"
                f"{('\n  话题：' + topic_text) if topic_text else ''}"
            )
        self._update("#topic-timeline", "\n│\n".join(timeline_rows) if timeline_rows else f"会话 {conversation_id} 暂无长期摘要；生成摘要后将在此按时间顺序呈现主题演进。")

    def save_entity(self) -> None:
        self.store.save_document("entities", self._value("#entity-id"), {
            "name": self._value("#entity-name"), "entity_type": self._value("#entity-type"),
            "definition": self._textarea("#entity-definition"),
        })

    def delete_entity(self) -> None:
        if not self.store.delete_document("entities", self._value("#entity-id")):
            raise KeyError("找不到实体")

    def save_environment(self) -> None:
        kind = self._value("#environment-kind").casefold()
        namespace = "domains" if kind == "domain" else "environments"
        record = {"name": self._value("#environment-name"), "details": self._textarea("#environment-details")}
        if namespace == "domains":
            default_environment = self._value("#domain-default-environment")
            record["default_environment_id"] = default_environment or None
        self.store.save_document(namespace, self._value("#environment-id"), record)

    def link_environment_domain(self, linked: bool) -> None:
        environment_id = self._value("#environment-id")
        domain_id = self._value("#environment-domain-id")
        if linked:
            self.domain_registry.add_environment(domain_id, environment_id)
        elif not self.domain_registry.remove_environment(domain_id, environment_id):
            raise KeyError("该环境不是域成员")

    def switch_domain(self) -> None:
        domain_id = self._value("#switch-domain-id") or self._value("#environment-id")
        result = self.domain_registry.switch(domain_id)
        self.notify(
            f"已切换至 {result['domain'].get('name', result['domain']['id'])} · {result['environment'].get('name', result['environment']['id'])}",
            title="域切换完成",
        )

    def save_environment_object(self) -> None:
        object_id = self._value("#environment-object-id") or uuid.uuid4().hex[:20]
        import json
        properties = json.loads(self._value("#environment-object-properties") or "{}")
        if not isinstance(properties, dict):
            raise ValueError("属性必须是 JSON object")
        self.store.save_environment_object(object_id, {
            "environment_id": self._value("#environment-object-environment") or self._value("#environment-id"),
            "name": self._value("#environment-object-name"),
            "position": self._value("#environment-object-position"),
            "priority": int(self._value("#environment-object-priority") or "50"),
            "description": self._textarea("#environment-object-description"),
            "properties": properties,
        })

    def delete_environment_object(self) -> None:
        if not self.store.delete_document("environment_objects", self._value("#environment-object-id")):
            raise KeyError("找不到环境物体")

    def toggle_environment_object(self) -> None:
        object_id = self._value("#environment-object-id")
        item = self.store.get_document("environment_objects", object_id)
        if item is None:
            raise KeyError("找不到环境物体")
        self.environment_service.set_object_visibility(object_id, not item.get("visible", True))

    def delete_environment_connection(self) -> None:
        if not self.store.delete_document("environment_connections", self._value("#connection-id")):
            raise KeyError("找不到环境连接")

    def save_domain(self) -> None:
        domain_id = self._value("#domain-id") or uuid.uuid4().hex[:20]
        default_environment = self._value("#domain-default-environment-id") or None
        self.domain_registry.save_domain(domain_id, {
            "name": self._value("#domain-name"),
            "details": self._value("#domain-description"),
            "default_environment_id": default_environment,
        })

    def add_domain_environment(self) -> None:
        self.domain_registry.add_environment(self._value("#domain-id"), self._value("#domain-member-environment"))

    def remove_domain_environment(self) -> None:
        if not self.domain_registry.remove_environment(self._value("#domain-id"), self._value("#domain-member-environment")):
            raise KeyError("该环境不是域成员")

    def create_environment_connection(self) -> None:
        direction = self.query_one("#connection-direction", Select).value
        self.store.create_environment_connection(
            self._value("#connection-from"), self._value("#connection-to"),
            connection_type=self._value("#connection-type"), direction=str(direction),
            description=self._value("#connection-description"),
        )

    def check_environment_move(self) -> None:
        source = self._value("#connection-from") or self._value("#environment-id")
        target = self._value("#connection-check-to") or self._value("#connection-to")
        reachable = self.store.can_move_to_environment(source, target)
        self.notify("可达：存在允许的直接连接" if reachable else "不可达：未找到允许的直接连接", title="环境连通性")

    def log_vision_usage(self) -> None:
        objects = [value.strip() for value in self._value("#vision-objects").split(",") if value.strip()]
        self.store.log_vision_usage(
            self._value("#vision-query"), environment_id=self._value("#environment-id") or None,
            objects_viewed=objects, context=self._textarea("#vision-context"),
            triggered_by=self._value("#vision-trigger") or "manual",
        )

    def save_expression(self) -> None:
        import json
        raw = self._textarea("#expression-examples")
        examples = json.loads(raw) if raw else []
        if not isinstance(examples, list) or any(not isinstance(item, str) for item in examples):
            raise ValueError("表达样例必须是字符串 JSON 数组")
        # Preserve the newer structured expression record while accepting the
        # existing TUI form's descriptive fields as readable operator metadata.
        self.expression_service.save_expression(
            self._value("#expression-id"), expression=self._value("#expression-name"),
            meaning=self._value("#expression-description") or "；".join(examples),
            category=self._value("#expression-category") or "通用",
        )

    def delete_expression(self) -> None:
        if not self.expression_service.delete_expression(self._value("#expression-id")):
            raise KeyError("找不到表达风格")

    def learn_user_expressions(self) -> None:
        conversation_id = self._value("#expression-conversation-id") or "default"
        transcript = self.store.read_json(f"/runtime/conversations/{conversation_id}.json", default=[])
        messages = [{"role": "user", "content": turn.get("user", "")} for turn in transcript]
        runtime = AgentRuntime(self.store, plugin_registry=self.plugin_registry)
        self.expression_service.learner = langchain_expression_learner(runtime.model)
        learned = self.expression_service.learn(messages, current_round=len(transcript))
        self.notify(f"新增或更新 {len(learned)} 条用户表达习惯", title="学习完成")

    def clear_user_expressions(self) -> None:
        if self._value("#clear-user-expressions-confirm") != "CLEAR USER HABITS":
            raise ValueError("请输入 CLEAR USER HABITS 以确认清空用户表达习惯")
        count = self.expression_service.clear_habits()
        self.notify(f"已清除 {count} 条用户表达习惯", title="操作完成")

    def delete_environment(self) -> None:
        kind = self._value("#environment-kind").casefold()
        namespace = "domains" if kind == "domain" else "environments"
        if namespace == "environments":
            if not self.environment_service.delete_environment(self._value("#environment-id")): raise KeyError("找不到环境")
        elif not self.store.delete_document(namespace, self._value("#environment-id")):
            raise KeyError("找不到记录")

    def toggle_plugin(self, enabled: bool) -> None:
        plugin_id = self._value("#plugin-id")
        if self.nps.get(plugin_id): self.nps.set_enabled(plugin_id, enabled)
        else: self.plugin_registry.set_enabled(plugin_id, enabled)

    def _nps_form_bundle(self) -> dict[str, Any]:
        plugin_id = self._value("#nps-id")
        capabilities = json.loads(self._value("#nps-capabilities") or "[]")
        if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
            raise ValueError("NPS capabilities 必须是字符串 JSON 数组")
        parameters_text = self._textarea("#nps-parameters")
        parameters = json.loads(parameters_text) if parameters_text else {"type": "object", "properties": {}}
        if not isinstance(parameters, dict):
            raise ValueError("NPS parameters 必须是 JSON Schema object")
        return {"format": "neo.nps/v1", "manifest": {
            "id": plugin_id, "name": self._value("#nps-name"), "version": "1.0.0",
            "description": self._value("#nps-description"), "entrypoint": self._value("#nps-entrypoint") or "main",
            "python_entrypoint": self._value("#nps-python-entrypoint") or "main",
            "capabilities": capabilities, "parameters": parameters,
        }, "vscript": self._textarea("#nps-vscript"), "python": self._textarea("#nps-python")}

    def save_nps(self) -> None:
        bundle = self._nps_form_bundle()
        self.nps.save(bundle, enabled=False)
        self._update("#plugin-list", "NPS 已验证并保存，当前停用。\n\n" + self._plugin_listing())

    def test_nps(self) -> None:
        bundle = self._nps_form_bundle()
        self.nps.validate_bundle(bundle)
        args = json.loads(self._value("#nps-args") or "{}")
        if not isinstance(args, dict): raise ValueError("测试参数必须是 JSON object")
        # A one-shot test runs in the same sandbox, but does not install or
        # change the enabled state of the persisted NPS bundle.
        result = self.nps.test_bundle(bundle, args)
        self._update("#plugin-list", f"NPS 测试通过\n结果：{result}\n\n" + self._plugin_listing())

    def import_nps(self) -> None:
        self.nps.import_json(self._textarea("#nps-import-export"), enabled=False)

    def export_nps(self) -> None:
        self.query_one("#nps-import-export", TextArea).text = self.nps.export_json(self._value("#plugin-id"))

    def delete_nps(self) -> None:
        self.nps.delete(self._value("#plugin-id"))

    def _plugin_listing(self) -> str:
        rows = [f"{'●' if p['enabled'] else '○'} {p['name']} v{p['version']} [{p['plugin_id']}]\n  {p['description']}\n  权限：{', '.join(p['capabilities'])}" for p in self.plugin_registry.manifests()]
        rows.extend(f"{'●' if p['enabled'] else '○'} NPS {p['name']} v{p['version']} [{p['id']}] · VScript={p['has_vscript']} Python={p['has_python']}" for p in self.nps.list())
        return "\n\n".join(rows) or "暂无插件。"

    def save_memory(self) -> None:
        text = self._value("#memory-text")
        cid = self._value("#memory-character") or "default"
        self.store.save_memory(uuid.uuid4().hex[:20], text, character_id=cid, metadata={"source": "operator"})

    def search_memory(self) -> None:
        result = self.store.search_memories(self._value("#memory-query"), character_id=self._value("#memory-character") or None)
        self._update("#memory-results", self._format_docs([{**item, "title": f"distance={item['distance']:.3f}", "content": item.get("text", "")} for item in result]))

    @staticmethod
    def _contains_secret_key(value: Any) -> bool:
        return ConfigurationService.contains_secret_key(value)

    @staticmethod
    def _without_secret_keys(value: Any) -> Any:
        return ConfigurationService.without_secret_keys(value)

    def save_summary(self) -> None:
        conversation_id = self._value("#memory-conversation-id") or "default"
        summary = self._textarea("#long-term-summary")
        if not summary:
            raise ValueError("长期摘要不能为空")
        summary_id = self._value("#long-term-summary-id")
        if summary_id:
            self.store.save_long_term_summary(summary_id, summary, conversation_id=conversation_id)
        else:
            saved = self.store.add_long_term_summary(summary, conversation_id=conversation_id)
            self.query_one("#long-term-summary-id", Input).value = saved["id"]
        self.refresh_memory_layers()

    def delete_summary(self) -> None:
        summary_id = self._value("#long-term-summary-id")
        if not self.store.delete_long_term_summary(summary_id):
            raise KeyError("找不到长期摘要")
        self.query_one("#long-term-summary", TextArea).clear()
        self.refresh_memory_layers()

    def refresh_memory_layers(self) -> None:
        if not self.is_mounted:
            return
        conversation_id = self._value("#memory-conversation-id") or "default"
        short = self.store.short_term_messages(conversation_id, limit=30)
        summaries = self.store.long_term_summaries(conversation_id)
        parts = ["短期对话："]
        parts.extend(f"{row['role']}: {row['content']}" for row in short)
        parts.append("\n长期摘要：")
        parts.extend(f"{row['id']} · {row.get('created_at', '')} · {row['summary']}" for row in summaries)
        self._update("#memory-layers", "\n".join(parts) if short or summaries else "该会话暂无短期消息或长期摘要。")

    def clear_short_term(self) -> None:
        conversation_id = self._value("#memory-conversation-id") or "default"
        self.store.clear_short_term(conversation_id)
        self.refresh_memory_layers()

    def clear_all_short_term(self) -> None:
        if self._value("#clear-short-confirm") != "CLEAR SHORT TERM":
            raise ValueError("请输入 CLEAR SHORT TERM 以确认清理全部短期记忆")
        count = self.store.clear_all_short_term()
        self.query_one("#clear-short-confirm", Input).clear()
        self.refresh_memory_layers()
        self.notify(f"已清除 {count} 个短期记忆窗口", title="存储管理")

    def clear_all_long_term(self) -> None:
        if self._value("#clear-long-confirm") != "CLEAR LONG TERM":
            raise ValueError("请输入 CLEAR LONG TERM 以确认清理全部长期摘要")
        count = self.store.clear_all_long_term_summaries()
        self.query_one("#clear-long-confirm", Input).clear()
        self.refresh_memory_layers()
        self.notify(f"已清除 {count} 条长期摘要；语义长期记忆保留", title="存储管理")

    def refresh_storage_statistics(self) -> None:
        overview = self.store.runtime_overview()
        lines = [
            f"DataDisk：{overview['disk_image']}",
            f"角色 {overview['characters']} · 知识 {overview['knowledge']} · 实体 {len(self.store.list_documents('entities'))}",
            f"短期窗口 {len(self.store.list_documents('short_term'))} · 长期摘要 {len(self.store.long_term_summaries())} · 向量记忆 {overview['memories']}",
            f"关系 {overview['relationships']} · 情绪 {overview['emotions']} · 日程 {overview['schedules']} · 事件 {overview['events']}",
            f"审计链：{'完整' if overview['audit'].get('ok') else '异常'} · {overview['audit'].get('length', 0)} 条",
        ]
        self._update("#database-statistics", "\n".join(lines))

    def refresh_conversations(self) -> None:
        rows = self.store.conversation_transcripts()
        rendered = []
        for row in rows:
            turns = row["turns"]
            tail = "\n".join(
                f"你：{turn.get('user', '')}\nAgent：{turn.get('assistant', '')}"
                for turn in turns[-3:]
            )
            rendered.append(f"{row['id']} · {len(turns)} 轮\n{tail}")
        self._update("#conversation-history", "\n\n".join(rendered) or "暂无持久化会话。")

    def delete_conversation(self) -> None:
        conversation_id = self._value("#memory-conversation-id")
        if not self.store.delete_conversation(conversation_id):
            raise KeyError("找不到该会话")
        self.refresh_memory_layers()
        self.refresh_conversations()

    def save_channel(self) -> None:
        cfg = json.loads(self._value("#channel-config") or "{}")
        if not isinstance(cfg, dict): raise ValueError("频道配置必须是 JSON object")
        if self._contains_secret_key(cfg): raise ValueError("频道配置禁止保存密钥；请使用环境变量或受管凭据服务")
        self.store.save_document("channels", self._value("#channel-id"), {"name": self._value("#channel-name"), "platform": self._value("#channel-platform"), "config": cfg, "state": "configured"})

    def _selected_config_categories(self) -> list[str]:
        return list(self.query_one("#config-categories", SelectionList).selected)

    def export_config(self) -> None:
        config = self.configuration_service.export(categories=self._selected_config_categories())
        self.query_one("#config-json", TextArea).text = json.dumps(config, ensure_ascii=False, indent=2)
        self._update("#config-preview", "配置已导出为 neo-agent/config/v1。")

    def preview_config(self) -> None:
        config = json.loads(self._textarea("#config-json"))
        preview = self.configuration_service.preview(config, categories=self._selected_config_categories())
        counts = "\n".join(f"{name}: {count} 条" for name, count in preview["counts"].items()) or "没有可导入记录。"
        self._update("#config-preview", f"格式：{preview['format']}\n总计：{preview['total']} 条\n{counts}")

    def import_config(self) -> None:
        config = json.loads(self._textarea("#config-json"))
        counts = self.configuration_service.import_config(config, categories=self._selected_config_categories())
        self._update("#config-preview", "已导入：" + ("、".join(f"{name} {count} 条" for name, count in counts.items()) or "配置为空"))
        self.refresh_memory_layers()
        self.refresh_conversations()
        self.refresh_storage_statistics()

    def _history_text(self) -> str:
        audit = self.store.sandbox.verify_audit()
        rows = self.store.runtime_logs()
        return (f"PyVDisk 审计链：{'完整' if audit.get('ok') else '异常'} · {audit.get('length', 0)} 条\n"
                f"当前可见运行记录：{len(rows)} 条（仅最近 500 条）\n\n" + self._format_runtime_logs(rows))

    @staticmethod
    def _format_runtime_logs(rows: list[dict[str, Any]]) -> str:
        if not rows:
            return "当前日志视图没有匹配的记录。"
        return "\n\n".join(
            f"#{row.get('sequence', '-')} · {row.get('timestamp_ns', '')} · {row.get('level', '')} · {row.get('message', '')}\n"
            f"logger: {row.get('logger', '')}\n{json.dumps(row.get('fields', {}), ensure_ascii=False, indent=2)}"
            for row in reversed(rows))

    def refresh_runtime_logs(self) -> None:
        filter_value = self.query_one("#runtime-log-filter", Select).value
        category = str(filter_value) if filter_value is not Select.NULL else "all"
        rows = self.store.runtime_logs(event_type=category, search=self._value("#runtime-log-search"), limit=500)
        self._update("#records-view", self._format_runtime_logs(rows))

    def clear_runtime_logs(self) -> None:
        if self._value("#clear-runtime-logs-confirm") != "CLEAR LOG VIEW":
            raise ValueError("请输入 CLEAR LOG VIEW 以确认清除当前日志视图")
        cutoff = self.store.clear_runtime_log_view()
        self.notify(f"已隐藏序号不大于 {cutoff} 的日志；原始审计事件仍保留。", title="运行记录")
        self.query_one("#clear-runtime-logs-confirm", Input).value = ""
        self.query_one("#runtime-log-filter", Select).value = "all"
        self.query_one("#runtime-log-search", Input).value = ""
        self.refresh_runtime_logs()

    def refresh_view(self) -> None:
        mapping = {"总览": "content", "虚拟群友": "characters", "对话": "chat", "事件流": "events", "日程": "schedules", "知识库": "knowledge", "关系": "relationships", "环境与域": "environment", "能力与 NPS": "plugins", "运行记录": "records", "存储与记忆": "storage", "频道连接": "channels", "系统设置": "settings", "实体管理": "entities", "表达风格": "expressions", "人机协作": "human-questions", "任务编排": "collaboration", "认知与回放": "cognition"}
        for name in mapping.values():
            self.query_one(f"#{name}").display = False
        view = mapping[self.active_view]
        self.query_one(f"#{view}").display = True
        self.query_one("#service-status", Static).update(self._status_text())
        if self.active_view == "总览":
            overview = self.store.runtime_overview()
            text = (f"[b]NEO · 全局运行总览[/b]\n\n群友  {overview['characters']}    工具  {len(self.plugin_registry.tools())}    事件  {overview['events']}    日程  {overview['schedules']}\n"
                    f"审计链  {'正常' if overview['audit'].get('ok') else '待检查'} · {overview['audit'].get('length', 0)} 条\n\n"
                    "TUI → Domain Services → LangChain Agent / Plugin Registry → PyVDisk AgentSandbox\n"
                    "PyVDisk：VFS 文档 + VectorDisk 记忆 + LogDisk 事件 + PyVDisk 文档：行程、地点、区域与场景审计\n\n"
                    "快捷键：1-9 导航 · E 事件 · S 日程 · R 刷新 · Q 退出")
            self._update("#content", text)
        elif self.active_view == "虚拟群友":
            rows = self.store.characters()
            active = self.single_role.active()
            if active:
                if not self.query_one("#character-editor", Vertical).display:
                    self._populate_character_form(active)
                self.query_one("#archive-character", Button).display = len(rows) > 1 and self.controls.debug
            else:
                self.query_one("#character-profile", Static).update("请选择唯一主角色；其余活动角色会被归档。" if rows else "首次启动：林依示范设定已填入编辑器，可直接修改后创建。")
                self.query_one("#character-profile", Static).display = bool(rows) and not self.query_one("#character-editor", Vertical).display
                self.query_one("#archive-character", Button).display = False
            selector = self.query_one("#primary-character", Select)
            selector.set_options([(row["name"], row["id"]) for row in rows])
            selector.display = len(rows) > 1
            self.query_one("#select-primary-character", Button).display = len(rows) > 1
            self._apply_debug_visibility()
        elif self.active_view == "对话":
            character = self.single_role.active()
            if character:
                self._update("#chat-character", f"当前角色  ·  {character.get('name', '未命名')}  ·  ID {character['id']}")
                self.query_one("#chat-log", Static).update(self._render_transcript(character))
            else:
                message = "请先创建虚拟群友。" if not self.store.characters() else "请先在「虚拟群友」中确定唯一主角色。"
                self._update("#chat-character", "尚未确定活动角色")
                self.query_one("#chat-log", Static).update(message)
        elif self.active_view == "认知与回放": self.refresh_cognition_status()
        elif self.active_view == "系统设置":
            active = self.single_role.active()
            self._update("#settings-view", f"Debug：{'开启' if self.controls.debug else '关闭'}\n活动角色：{active.get('name', active['id']) if active else '未初始化 / 待选择主角色'}\n手动创作入口：{'开放' if self.controls.debug or not self.store.characters() else '隐藏'}\n模型密钥仅从环境变量读取。")
        elif self.active_view == "事件流": self.refresh_events()
        elif self.active_view == "日程": self._update("#schedule-list", self._schedule_listing())
        elif self.active_view == "人机协作": self.refresh_questions()
        elif self.active_view == "任务编排": self.refresh_collaboration()
        elif self.active_view == "知识库": self.search_knowledge()
        elif self.active_view == "关系":
            relationships = self.store.list_documents("relationships")
            relation_rows = []
            for item in relationships:
                score = float(item.get("score", 0.0))
                bar = "█" * min(20, max(0, int(abs(score) / 5)))
                relation_rows.append(f"{item['id']} · {item.get('peer', item.get('name', '未命名'))} · 关系分 {score:+.1f} {bar}\n" + "\n".join(f"  · {row.get('note', '')} ({row.get('delta', 0):+.1f})" for row in item.get("interactions", [])[-5:]))
            self._update("#relationship-list", "\n\n".join(relation_rows) or "暂无关系记录。")
            relationship_id = self._value("#relationship-id") if self.is_mounted else ""
            emotions = sorted(self.store.emotion_history(relationship_id or None), key=lambda row: row.get("created_at", ""), reverse=True)
            self._update("#emotion-list", "\n\n".join(
                f"{row.get('created_at', '')} · {row.get('relationship_id', '')} · "
                f"{row.get('relationship_type', row.get('tone', '情绪'))} · "
                f"关系分 {float(row.get('overall_score', row.get('score', 0))):.1f} "
                f"({float(row.get('score_change', 0)):+.1f}) · {row.get('sentiment', '')} / {row.get('emotional_tone', '')}\n"
                f"印象：{row.get('impression', '')}\n话题：{', '.join(row.get('key_topics', []))}\n"
                f"维度：{row.get('dimensions', {})}\n分析：{row.get('analysis', '')}\n证据：{row.get('evidence', '')}"
                for row in emotions[:100]) or "暂无情绪轨迹。")
            self.refresh_relationship_view()
        elif self.active_view == "环境与域":
            rows = [("环境", x) for x in self.store.list_documents("environments")] + [("域", x) for x in self.store.list_documents("domains")]
            self._update("#environment-list", "\n\n".join(f"{kind} · {item['id']} · {item.get('name', '')}{' · 当前' if kind == '环境' and item.get('active') else ''}\n{item.get('details', '')}\n关联环境：{', '.join(item.get('environment_ids', []))}" for kind, item in rows) or "暂无环境或域。")
            objects = [obj for environment in self.store.list_documents("environments") for obj in self.environment_service.objects(environment["id"], visible_only=False)]
            connections = self.environment_service.connections()
            env_names = {row["id"]: row.get("name", row["id"]) for row in self.store.list_documents("environments")}
            graph_rows = [f"{env_names.get(edge['from_environment_id'], edge['from_environment_id'])} {'↔' if edge.get('direction') == 'bidirectional' else '→'} {env_names.get(edge['to_environment_id'], edge['to_environment_id'])} · {edge.get('connection_type', 'normal')} · {edge.get('description', '')}" for edge in connections]
            object_rows = [f"{row.get('name')} · {row['id']} · {env_names.get(row.get('environment_id'), row.get('environment_id'))} · {'可见' if row.get('visible', True) else '隐藏'} · 优先级 {row.get('priority', 50)} · {row.get('position', '')}\n  {row.get('description', '')}" for row in objects]
            graph_text = "环境物体\n" + ("\n".join(object_rows) or "  暂无") + "\n\n关系图（→ 单向，↔ 双向）\n" + ("\n".join(graph_rows) or "暂无连接")
            self._update("#environment-graph", graph_text)
            logs = self.environment_service.vision_history(50)
            self._update("#vision-log-list", "\n\n".join(f"{row.get('created_at', '')} · {row.get('triggered_by', '')} · {row.get('environment_id') or '未指定环境'}\n查询：{row.get('query', '')}\n物体：{', '.join(row.get('objects_viewed', []))}\n上下文：{row.get('context', '')}" for row in logs) or "暂无视觉审计记录。")
            current_scene = self.scene_service.current() or {}
            places = self.scene_service.places()
            areas = self.scene_service.areas()
            place_by_id = {row.get("id"): row for row in places}
            area_by_id = {row.get("id"): row for row in areas}
            current_place = place_by_id.get(current_scene.get("place_id"), {})
            current_area = area_by_id.get(current_scene.get("area_id"), {})
            pool_rows = [
                "当前场景：" + self.scene_service.current_context(),
                "\n场景池（首次进入后固化地点设定与布局；物体状态仍可变化）",
            ]
            for place in sorted(places, key=lambda row: (not bool(row.get("visited")), row.get("name", ""))):
                place_areas = [row for row in areas if row.get("place_id") == place.get("id")]
                marker = " ← 当前地点" if place.get("id") == current_place.get("id") else ""
                pool_rows.append(
                    f"\n{place.get('name', '未命名地点')} · {place.get('id')}{marker}\n"
                    f"  {place.get('description', '')}\n"
                    f"  状态：{'已访问 / 已固化' if place.get('visited') else '待用场景'} · "
                    f"fixed={bool(place.get('fixed'))} · layout_frozen={bool(place.get('layout_frozen'))}\n"
                    f"  目的：{', '.join(place.get('purpose_tags', [])) or place.get('generated_for', '未标记')} · "
                    f"标签：{', '.join(place.get('tags', [])) or '无'}"
                )
                for area in place_areas:
                    area_marker = " ← 当前区域" if area.get("id") == current_area.get("id") else ""
                    pool_rows.append(
                        f"    └─ {area.get('name', '未命名区域')} · {area.get('id')}{area_marker}\n"
                        f"       {area.get('description', '')} · "
                        f"{'已固化' if area.get('visited') else '待首次访问'}"
                    )
                objects_for_place = [row for row in self.store.list_documents("environment_objects") if row.get("place_id") == place.get("id")]
                for obj in objects_for_place:
                    area = area_by_id.get(obj.get("area_id"), {})
                    pool_rows.append(f"       ◦ {obj.get('name', obj.get('id'))} [{area.get('name', '未分区')}] · {obj.get('state', '正常')} · {'可见' if obj.get('visible', True) else '隐藏'}")
            itineraries = self.store.list_documents("itineraries")
            failed = [row for row in itineraries if row.get("status") == "failed"]
            if failed:
                pool_rows.append("\n行程生成失败 / 重试状态")
                pool_rows.extend(f"  {row.get('local_date', row.get('id'))} · {row.get('error', '未知错误')} · 重试：{row.get('retry_at', '未安排')} · 次数：{row.get('attempts', 0)}" for row in failed)
            audits = self.store.list_documents("scene_audits")[-30:]
            pool_rows.append("\n最近场景生成 / 切换审计")
            pool_rows.extend(f"  {row.get('occurred_at', '') or row.get('action', '')} · {row.get('action', 'scene.audit')} · {row.get('purpose', row.get('schedule_id', ''))} · 地点 {row.get('place_id', row.get('to_place_id', ''))} · 区域 {row.get('area_id', row.get('to_area_id', ''))}" for row in reversed(audits))
            self._update("#scene-pool", "\n".join(pool_rows))
            domains = self.store.list_documents("domains")
            current_domain = self.domain_registry.current()
            domain_rows = []
            for domain in domains:
                members = self.domain_registry.members(domain["id"])
                names = ", ".join(item.get("name", item["id"]) for item in members) or "无成员环境"
                default = domain.get("default_environment_id") or "未设定"
                active_marker = " · 当前域" if current_domain and current_domain["id"] == domain["id"] else ""
                domain_rows.append(f"{domain.get('name', domain['id'])} · {domain['id']}{active_marker}\n{domain.get('details', '')}\n成员：{names}\n默认环境：{default}")
            self._update("#domain-list", "\n\n".join(domain_rows) or "暂无域；保存域后可添加环境并切换。")
        elif self.active_view == "能力与 NPS": self._update("#plugin-list", self._plugin_listing())
        elif self.active_view == "运行记录": self.refresh_runtime_logs()
        elif self.active_view == "存储与记忆":
            overview = self.store.runtime_overview()
            collections = self.store.sandbox.disk.vectors.list_collections()
            self._update("#storage-view", f"DataDisk 镜像：{overview['disk_image']}\n\n角色：/characters/<id>/profile.json\n事件：LogDisk / neo-agent-events\n向量记忆集合：{collections}\n日程与场景：PyVDisk 文档；SceneScheduler 负责启动恢复和到时切换\n\n配置导入导出采用 neo-agent/config/v2，不包含密钥与会话对话。")
            self.refresh_memory_layers()
            self.refresh_conversations()
            self.refresh_storage_statistics()
        elif self.active_view == "表达风格":
            expressions = self.expression_service.expressions()
            self._update("#expression-list", "\n\n".join(
                f"{item['id']} · {item.get('expression', item.get('name', ''))} [{item.get('category', '通用')}]\n"
                f"{item.get('meaning', item.get('description', ''))} · 使用 {item.get('usage_count', 0)} 次" for item in expressions) or "暂无表达风格配置。")
            habits = self.expression_service.habits()
            self._update("#user-expression-list", "\n\n".join(
                f"{item.get('expression_pattern')} · 置信度 {float(item.get('confidence', 0)):.2f} · 观察 {item.get('frequency', 1)} 次\n"
                f"{item.get('meaning')} · 来源轮次 {item.get('learned_from_rounds', '未知')}" for item in habits) or "暂无已学习的用户表达习惯。")
        elif self.active_view == "频道连接":
            channels = self.store.list_documents("channels")
            self._update("#channel-list", "\n\n".join(
                f"{row['id']} · {row.get('name', '')} · {row.get('platform', '')} · {row.get('state', 'configured')}\n"
                f"配置：{json.dumps(row.get('config', {}), ensure_ascii=False, indent=2)}" for row in channels) or "暂无频道连接。")
        elif self.active_view == "实体管理":
            entities = self.store.list_documents("entities")
            self._update("#entity-list", "\n\n".join(
                f"{row['id']} · {row.get('name', '')} · {row.get('entity_type', '')}\n{row.get('definition', '')}"
                for row in entities) or "暂无实体记录。")
        elif self.active_view == "系统设置": self._update("#settings-view", f"模型配置状态：{'已配置' if os.getenv('OPENAI_API_KEY') or os.getenv('SILICONFLOW_API_KEY') else '缺少密钥'}\n数据镜像：{self.store.runtime_overview()['disk_image']}\n默认频道：由「频道连接」管理\n插件执行：VScript 受限策略；Python 扩展要求 bubblewrap 隔离。")


def run() -> None:
    from dotenv import load_dotenv
    load_dotenv()
    image = os.environ.get("NEO_VDISK_PATH", str(Path.home() / ".neo-agent" / "runtime.vdisk"))
    Path(image).parent.mkdir(parents=True, exist_ok=True)
    store = DiskStore.open(image)
    try:
        NeoConsole(store).run()
    finally:
        store.close()
