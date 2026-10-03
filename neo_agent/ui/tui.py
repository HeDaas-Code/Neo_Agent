"""Global Textual control plane for the Neo Agent runtime."""
from __future__ import annotations

import asyncio
import json
import os
import uuid
from pathlib import Path
from typing import Any

from rich.text import Text
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, ListItem, ListView, Select, SelectionList, Static, TextArea

from neo_agent.plugins import PluginRegistry
from neo_agent.runtime import (AgentRuntime, DomainRegistry, EnvironmentService, ScheduleWorker,
                               ExpressionService, langchain_expression_learner, ConfigurationService)
from neo_agent.services import SchedulePlanningService
from neo_agent.storage import DiskStore
from neo_agent.services import InterruptQuestionService


class NeoConsole(App[None]):
    TITLE = "NEO / AGENT OPERATIONS"
    SUB_TITLE = "VIRTUAL GROUP MEMBER · CONTROL PLANE"
    NAV_ITEMS = ("总览", "虚拟群友", "对话", "事件流", "日程", "知识库", "关系", "环境与域", "能力与 NPS", "运行记录", "存储与记忆", "频道连接", "系统设置", "实体管理", "表达风格", "人机协作", "任务编排")
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
    #content { height: 1fr; border: round #334155; background: #111a2d; padding: 1 2; }
    .page { height: 1fr; display: none; }
    .listing { height: 1fr; border: round #334155; background: #111a2d; padding: 1; overflow-y: auto; }
    .actions { height: 3; align-horizontal: right; }
    #character-list { height: 6; }
    #config-categories { height: 10; border: round #334155; margin: 1 0; }
    #characters .character-fields { height: 3; }
    #characters .profile-editor { height: 4; margin: 0; }
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
        self.worker = ScheduleWorker(store)
        self.environment_service = EnvironmentService(store)
        self.domain_registry = DomainRegistry(store)
        self.expression_service = ExpressionService(store)
        self.configuration_service = ConfigurationService(store)
        self.question_service = InterruptQuestionService(store)
        self.active_view = "总览"
        self._busy = False

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
                    yield Static(id="character-list", classes="listing")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="角色 ID", id="character-id", classes="form-row")
                        yield Input(placeholder="显示名称", id="character-name", classes="form-row")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="性别", id="character-gender", classes="form-row")
                        yield Input(placeholder="身份 / 职业", id="character-role", classes="form-row")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="年龄", id="character-age", classes="form-row")
                        yield Input(placeholder="身高", id="character-height", classes="form-row")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="体重", id="character-weight", classes="form-row")
                        yield Input(placeholder="爱好", id="character-hobby", classes="form-row")
                    yield Label("性格与背景", classes="eyebrow")
                    yield TextArea(id="character-personality", soft_wrap=True, classes="editor profile-editor")
                    yield TextArea(id="character-background", soft_wrap=True, classes="editor profile-editor")
                    with Horizontal(classes="actions"):
                        yield Button("载入角色", id="load-character")
                        yield Button("创建 / 保存角色", id="save-character", variant="primary")
                        yield Button("归档角色", id="archive-character", variant="error")
                with Vertical(id="chat", classes="page"):
                    yield Select([], prompt="选择虚拟群友", id="chat-character", classes="form-row")
                    yield Static(id="chat-log")
                    yield TextArea(id="chat-input", soft_wrap=True)
                    with Horizontal(classes="actions"):
                        yield Button("发送消息", id="send-chat", variant="primary")
                with VerticalScroll(id="events", classes="page"):
                    yield Static(id="events-list", classes="listing")
                    yield Input(placeholder="过滤事件类型（可选）", id="event-filter")
                    yield Button("过滤 / 刷新日志", id="filter-events")
                    yield Input(placeholder="事件类型，如 group.message", id="event-type")
                    yield Input(placeholder="事件摘要", id="event-summary")
                    yield Button("写入不可变事件日志", id="append-event", variant="primary")
                    yield Label("事件管理记录（可更新生命周期；所有操作另写审计日志）", classes="eyebrow")
                    yield Static(id="event-record-list", classes="listing")
                    yield Input(placeholder="事件记录 ID", id="event-record-id")
                    yield Input(placeholder="事件标题", id="event-record-title")
                    yield Input(placeholder="事件类型", id="event-record-type")
                    yield Input(placeholder="事件详情", id="event-record-details")
                    yield Input(placeholder="状态：pending / triggered / awaiting_user / needs_review / completed / failed / cancelled", id="event-record-status", value="pending")
                    with Horizontal(classes="actions"):
                        yield Button("创建事件", id="create-event-record", variant="primary")
                        yield Button("更新状态", id="update-event-record")
                        yield Button("触发事件", id="trigger-event-record")
                        yield Button("删除记录", id="delete-event-record", variant="error")
                with VerticalScroll(id="human-questions", classes="page"):
                    yield Label("Agent 中断提问 · 待回答请求会持久化，回答后可由会话恢复", classes="eyebrow")
                    yield Static(id="question-list", classes="listing")
                    yield Input(placeholder="待回答 question_id", id="question-id")
                    yield Input(placeholder="给 Agent 的回答", id="question-answer")
                    with Horizontal(classes="actions"):
                        yield Button("刷新待回答", id="refresh-questions")
                        yield Button("提交回答", id="resolve-question", variant="primary")
                with VerticalScroll(id="collaboration", classes="page"):
                    yield Label("任务型事件 · LangChain 多角色分析 / 规划 / 执行 / 验收", classes="eyebrow")
                    yield Input(placeholder="任务标题", id="collaboration-title")
                    yield TextArea(id="collaboration-description", soft_wrap=True, classes="editor", placeholder="任务描述")
                    yield Input(placeholder="要求（可选）", id="collaboration-requirements")
                    yield Input(placeholder="完成标准（可选）", id="collaboration-criteria")
                    with Horizontal(classes="actions"):
                        yield Button("发起协作任务", id="start-collaboration", variant="primary")
                    yield Input(placeholder="恢复等待用户回答的 run_id", id="collaboration-run-id")
                    with Horizontal(classes="actions"):
                        yield Button("恢复任务", id="resume-collaboration")
                    yield Static(id="collaboration-runs", classes="listing")
                with VerticalScroll(id="schedules", classes="page"):
                    yield Static(id="schedule-list", classes="listing")
                    yield Input(placeholder="schedule_id", id="schedule-id")
                    yield Input(placeholder="标题", id="schedule-title")
                    yield Input(placeholder="ISO-8601 时间，例如 2026-10-03T18:00:00+08:00", id="schedule-due")
                    yield Input(placeholder="描述（可选）", id="schedule-description")
                    yield Input(placeholder="结束时间 ISO-8601（可选）", id="schedule-end")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="类型 appointment / recurring / temporary", id="schedule-type", value="appointment")
                        yield Input(placeholder="优先级 low / medium / high / critical（按类型默认）", id="schedule-priority")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="周期星期：周一 0 … 周日 6", id="schedule-weekday")
                        yield Input(placeholder="周期说明，如 every-week", id="schedule-recurrence")
                    with Horizontal(classes="character-fields"):
                        yield Select([("全部日期", "all"), ("今天", "today"), ("明天", "tomorrow"), ("本周", "week")], value="all", id="schedule-date-filter")
                        yield Select([("全部状态", "all"), ("待处理", "pending"), ("待发送", "awaiting_delivery"), ("已通知", "notified"), ("周期冲突", "recurrence_blocked"), ("已取消", "cancelled")], value="all", id="schedule-status-filter")
                        yield Button("应用筛选", id="filter-schedules")
                    with Horizontal(classes="actions"):
                        yield Button("创建提醒", id="create-schedule", variant="primary")
                        yield Button("复核后仍然创建", id="confirm-create-similar-schedule", variant="warning", disabled=True)
                        yield Input(placeholder="要编辑 / 删除的 schedule_id", id="schedule-delete-id")
                        yield Button("删除日程", id="delete-schedule", variant="error")
                    yield Label("编辑：填写目标 ID、标题、时间与描述后提交；改时间会重建持久队列任务。", classes="eyebrow")
                    yield Input(placeholder="编辑目标 schedule_id", id="schedule-edit-id")
                    yield Input(placeholder="新标题", id="schedule-edit-title")
                    yield Input(placeholder="新 ISO-8601 时间（含时区）", id="schedule-edit-due")
                    yield Input(placeholder="新描述", id="schedule-edit-description")
                    yield Input(placeholder="新结束时间 ISO-8601（可选）", id="schedule-edit-end")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="新类型 appointment / recurring / temporary", id="schedule-edit-type")
                        yield Input(placeholder="新优先级 low / medium / high / critical", id="schedule-edit-priority")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="周期星期 0–6", id="schedule-edit-weekday")
                        yield Input(placeholder="周期规则", id="schedule-edit-recurrence")
                    yield Button("更新日程", id="update-schedule", variant="primary")
                    yield Label("时间范围 / 空闲时段 / 统计", classes="eyebrow")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="范围开始 ISO-8601（含时区）", id="schedule-range-start")
                        yield Input(placeholder="范围结束 ISO-8601（含时区）", id="schedule-range-end")
                        yield Input(placeholder="最短空闲分钟数", id="schedule-free-minutes", value="30")
                    with Horizontal(classes="actions"):
                        yield Button("查询范围", id="query-schedule-range")
                        yield Button("查找空闲时段", id="find-free-slots")
                        yield Button("日程统计", id="schedule-statistics")
                        yield Input(placeholder="详情 schedule_id", id="schedule-detail-id")
                        yield Button("查看详情", id="schedule-details")
                    yield Static(id="schedule-analysis", classes="listing")
                    yield Label("临时活动建议 · 仅生成建议；选中并采用后才会写入日程", classes="eyebrow")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="角色名称", id="schedule-character-name", value="智能体")
                        yield Input(placeholder="角色兴趣", id="schedule-character-hobbies", value="阅读、学习")
                        yield Input(placeholder="建议时长下限（分钟）", id="schedule-suggestion-minutes", value="60")
                    yield Input(placeholder="对话上下文（可选）", id="schedule-suggestion-context")
                    with Horizontal(classes="actions"):
                        yield Button("生成活动建议", id="generate-schedule-suggestions")
                        yield Input(placeholder="采用建议编号（从 1 开始）", id="schedule-suggestion-index", value="1")
                        yield Button("采用所选建议", id="apply-schedule-suggestion", variant="primary")
                    yield Static(id="schedule-suggestions", classes="listing")
                    yield Label("协作确认：选择待处理的日程 ID 后确认或拒绝。拒绝会取消提醒。", classes="eyebrow")
                    with Horizontal(classes="actions"):
                        yield Button("确认协作", id="confirm-schedule", variant="primary")
                        yield Button("拒绝协作", id="reject-schedule", variant="error")
                with VerticalScroll(id="knowledge", classes="page"):
                    yield Static(id="knowledge-list", classes="listing")
                    yield Input(placeholder="知识 ID", id="knowledge-id")
                    yield Input(placeholder="标题", id="knowledge-title")
                    yield Input(placeholder="搜索关键词", id="knowledge-search")
                    yield TextArea(id="knowledge-content", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("保存知识", id="save-knowledge", variant="primary")
                        yield Button("搜索", id="search-knowledge")
                        yield Button("删除知识", id="delete-knowledge", variant="error")
                    yield Label("基础知识事实（实体 / 分类 / 置信度）", classes="eyebrow")
                    yield Input(placeholder="事实 ID", id="base-knowledge-id")
                    yield Input(placeholder="实体名称", id="base-knowledge-entity")
                    yield Input(placeholder="分类", id="base-knowledge-category")
                    yield Input(placeholder="置信度 0–1", id="base-knowledge-confidence", value="1")
                    yield TextArea(id="base-knowledge-content", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("保存基础知识", id="save-base-knowledge", variant="primary")
                        yield Button("删除基础知识", id="delete-base-knowledge", variant="error")
                with VerticalScroll(id="relationships", classes="page"):
                    yield Static(id="relationship-list", classes="listing")
                    yield Input(placeholder="关系 ID（角色-用户）", id="relationship-id")
                    yield Input(placeholder="对方名称 / 群组", id="relationship-peer")
                    yield Input(placeholder="互动备注", id="relationship-note")
                    yield Input(placeholder="本次关系分值变化，例如 1 或 -1", id="relationship-delta", value="0")
                    yield Button("记录互动", id="record-relationship", variant="primary")
                    yield Label("情绪轨迹（人工标注，可由后续分析器自动生成）", classes="eyebrow")
                    yield Input(placeholder="情绪标签", id="emotion-tone")
                    yield Input(placeholder="情绪分值 -1 至 1", id="emotion-score", value="0")
                    yield Input(placeholder="证据 / 上下文", id="emotion-evidence")
                    yield Button("记录情绪", id="record-emotion")
                    yield Input(placeholder="分析来源 conversation_id", id="emotion-conversation-id", value="default")
                    with Horizontal(classes="actions"):
                        yield Button("分析所选关系", id="analyze-emotion", variant="primary")
                        yield Button("刷新关系 / 主题视图", id="refresh-relationships")
                    yield Label("最近一次关系印象 · 维度可视化", classes="eyebrow")
                    yield Static(id="emotion-radar", classes="listing")
                    yield Label("对话主题时间线 · 来自该会话的长期摘要", classes="eyebrow")
                    yield Static(id="topic-timeline", classes="listing")
                    yield Label("可审计情绪 / 关系历史", classes="eyebrow")
                    yield Static(id="emotion-list", classes="listing")
                with VerticalScroll(id="environment", classes="page"):
                    yield Static(id="environment-list", classes="listing")
                    yield Input(placeholder="类型：environment 或 domain", id="environment-kind", value="environment")
                    yield Input(placeholder="ID", id="environment-id")
                    yield Input(placeholder="名称", id="environment-name")
                    yield TextArea(id="environment-details", soft_wrap=True, classes="editor")
                    yield Input(placeholder="关联域 ID / 成员环境 ID", id="environment-domain-id")
                    yield Input(placeholder="域默认环境 ID（创建/编辑域时）", id="domain-default-environment")
                    with Horizontal(classes="actions"):
                        yield Button("保存", id="save-environment", variant="primary")
                        yield Button("设为当前环境", id="activate-environment")
                        yield Button("关联域", id="link-environment-domain")
                        yield Button("从域移除环境", id="unlink-environment-domain")
                        yield Button("删除", id="delete-environment", variant="error")
                    yield Label("环境物体", classes="eyebrow")
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
                        yield Button("删除物体", id="delete-environment-object", variant="error")
                    yield Label("环境连接关系图 / 移动可达性", classes="eyebrow")
                    yield Static(id="environment-graph", classes="listing")
                    yield Input(placeholder="起始环境 ID", id="connection-from")
                    yield Input(placeholder="目标环境 ID", id="connection-to")
                    yield Input(placeholder="连接类型", id="connection-type", value="normal")
                    yield Select((("双向", "bidirectional"), ("单向", "one_way")), value="bidirectional", id="connection-direction")
                    yield Input(placeholder="连接描述", id="connection-description")
                    yield Input(placeholder="待验证目标环境 ID", id="connection-check-to")
                    yield Input(placeholder="连接 ID（删除时填写）", id="connection-id")
                    with Horizontal(classes="actions"):
                        yield Button("创建连接", id="create-environment-connection", variant="primary")
                        yield Button("检查当前环境可达", id="check-environment-move")
                        yield Button("删除连接", id="delete-environment-connection", variant="error")
                    yield Label("伪视觉工具审计记录", classes="eyebrow")
                    yield Input(placeholder="查询 / 用户问题", id="vision-query")
                    yield Input(placeholder="查看物体 ID，逗号分隔", id="vision-objects")
                    yield Input(placeholder="触发方式 auto / manual", id="vision-trigger", value="manual")
                    yield TextArea(placeholder="提供给 Agent 的视觉上下文", id="vision-context", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("记录视觉观察", id="log-vision-usage", variant="primary")
                        yield Button("刷新环境视图", id="refresh-environment")
                    yield Static(id="vision-log-list", classes="listing")
                    yield Label("域工作区 · 成员 / 默认位置 / 切换", classes="eyebrow")
                    yield Static(id="domain-list", classes="listing")
                    yield Input(placeholder="域 ID", id="domain-id")
                    yield Input(placeholder="域名称", id="domain-name")
                    yield Input(placeholder="域描述", id="domain-description")
                    yield Input(placeholder="成员环境 ID", id="domain-member-environment")
                    yield Input(placeholder="默认环境 ID（需先加入域）", id="domain-default-environment-id")
                    yield Input(placeholder="切换目标域 ID", id="switch-domain-id")
                    with Horizontal(classes="actions"):
                        yield Button("保存域", id="save-domain", variant="primary")
                        yield Button("添加成员环境", id="add-domain-environment")
                        yield Button("移除成员环境", id="remove-domain-environment")
                        yield Button("切换到域", id="switch-domain")
                with VerticalScroll(id="expressions", classes="page"):
                    yield Static(id="expression-list", classes="listing")
                    yield Input(placeholder="表达风格 ID", id="expression-id")
                    yield Input(placeholder="风格名称", id="expression-name")
                    yield Input(placeholder="分类，如感叹词 / 网络用语", id="expression-category", value="通用")
                    yield Input(placeholder="说明 / 特征", id="expression-description")
                    yield TextArea(id="expression-examples", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("保存表达风格", id="save-expression", variant="primary")
                        yield Button("删除表达风格", id="delete-expression", variant="error")
                    yield Label("用户表达习惯 · 基于所选对话的用户消息进行显式学习", classes="eyebrow")
                    yield Input(placeholder="学习来源 conversation_id", id="expression-conversation-id", value="default")
                    with Horizontal(classes="actions"):
                        yield Button("立即学习", id="learn-user-expressions", variant="primary")
                        yield Input(placeholder="输入 CLEAR USER HABITS 确认清空", id="clear-user-expressions-confirm")
                        yield Button("清空用户习惯", id="clear-user-expressions", variant="error")
                    yield Static(id="user-expression-list", classes="listing")
                with VerticalScroll(id="entities", classes="page"):
                    yield Static(id="entity-list", classes="listing")
                    yield Input(placeholder="实体 ID", id="entity-id")
                    yield Input(placeholder="实体名称", id="entity-name")
                    yield Input(placeholder="实体类型", id="entity-type")
                    yield TextArea(id="entity-definition", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("保存实体", id="save-entity", variant="primary")
                        yield Button("删除实体", id="delete-entity", variant="error")
                with VerticalScroll(id="plugins", classes="page"):
                    yield Static(id="plugin-list", classes="listing")
                    yield Input(placeholder="内置 plugin_id / NPS id", id="plugin-id")
                    with Horizontal(classes="actions"):
                        yield Button("启用", id="enable-plugin", variant="primary")
                        yield Button("停用", id="disable-plugin", variant="error")
                        yield Button("删除 NPS", id="delete-nps", variant="error")
                    yield Label("新版 NPS bundle JSON · VScript 主控，可选受限 Python 扩展", classes="eyebrow")
                    yield Input(placeholder="NPS id（例如 custom.hello）", id="nps-id")
                    yield Input(placeholder="名称", id="nps-name")
                    yield Input(placeholder="描述", id="nps-description")
                    yield Input(placeholder="VScript entrypoint（固定 main）", id="nps-entrypoint", value="main")
                    yield Input(placeholder="Python entrypoint（默认 main）", id="nps-python-entrypoint", value="main")
                    yield Input(placeholder='能力 JSON 数组，例如 ["python.call"]', id="nps-capabilities", value="[]")
                    yield Label("工具参数 JSON Schema（v1：object + string / integer / number / boolean）", classes="eyebrow")
                    yield TextArea(id="nps-parameters", soft_wrap=True, classes="editor")
                    yield TextArea(id="nps-vscript", soft_wrap=True, classes="editor")
                    yield TextArea(id="nps-python", soft_wrap=True, classes="editor")
                    yield Input(placeholder="测试参数 JSON", id="nps-args", value="{}")
                    with Horizontal(classes="actions"):
                        yield Button("校验并保存 NPS", id="save-nps", variant="primary")
                        yield Button("测试 NPS", id="test-nps")
                    yield TextArea(id="nps-import-export", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("导入新版 JSON", id="import-nps")
                        yield Button("导出选中 NPS", id="export-nps")
                with VerticalScroll(id="records", classes="page"):
                    with Horizontal(classes="character-fields"):
                        yield Select([("全部记录", "all"), ("错误 / 失败", "errors"), ("对话", "conversation"), ("插件", "plugin"), ("日程", "schedule"), ("关系", "relationship")], value="all", id="runtime-log-filter")
                        yield Input(placeholder="搜索事件 / payload", id="runtime-log-search")
                    with Horizontal(classes="actions"):
                        yield Button("筛选 / 刷新", id="refresh-runtime-logs")
                        yield Input(placeholder="输入 CLEAR LOG VIEW 确认隐藏旧记录", id="clear-runtime-logs-confirm")
                        yield Button("清除当前日志视图", id="clear-runtime-logs", variant="error")
                    yield Label("清除只设置可审计的显示水位，不删除 PyVDisk LogDisk 事件。", classes="eyebrow")
                    yield Static(id="records-view", classes="listing")
                with VerticalScroll(id="storage", classes="page"):
                    yield Static(id="storage-view", classes="listing")
                    yield Input(placeholder="记忆文本", id="memory-text")
                    yield Input(placeholder="记忆检索", id="memory-query")
                    yield Input(placeholder="角色 ID（可选）", id="memory-character")
                    with Horizontal(classes="actions"):
                        yield Button("保存长期记忆", id="save-memory", variant="primary")
                        yield Button("语义检索", id="search-memory")
                    yield Static(id="memory-results", classes="listing")
                    yield Label("短期对话记忆 / 人工长期摘要（Conversation ID 最多 22 个 ASCII 字符）", classes="eyebrow")
                    yield Input(placeholder="Conversation ID", id="memory-conversation-id")
                    yield Input(placeholder="摘要 ID（留空新建；填写可覆盖）", id="long-term-summary-id")
                    yield TextArea(id="long-term-summary", soft_wrap=True, classes="editor")
                    with Horizontal(classes="actions"):
                        yield Button("保存长期摘要", id="save-summary", variant="primary")
                        yield Button("删除长期摘要", id="delete-summary", variant="error")
                        yield Button("查看短期 / 长期记忆", id="refresh-memory-layers")
                        yield Button("清空该会话短期记忆", id="clear-short-term", variant="error")
                    yield Static(id="memory-layers", classes="listing")
                    yield Label("批量清理需要逐字输入确认口令；语义长期记忆不会被清除。", classes="eyebrow")
                    with Horizontal(classes="character-fields"):
                        yield Input(placeholder="输入 CLEAR SHORT TERM", id="clear-short-confirm")
                        yield Button("清空全部短期记忆", id="clear-all-short-term", variant="error")
                        yield Input(placeholder="输入 CLEAR LONG TERM", id="clear-long-confirm")
                        yield Button("清空全部长期摘要", id="clear-all-long-term", variant="error")
                    yield Static(id="database-statistics", classes="listing")
                    yield Button("刷新存储统计", id="refresh-storage-statistics")
                    yield Label("会话历史（删除会话会清除 transcript 与短期记忆；长期摘要保留）", classes="eyebrow")
                    yield Static(id="conversation-history", classes="listing")
                    with Horizontal(classes="actions"):
                        yield Button("刷新会话", id="refresh-conversations")
                        yield Button("删除会话", id="delete-conversation", variant="error")
                    yield Label("选择配置类别（导出与导入共用此选择）；不导出密钥", classes="eyebrow")
                    yield SelectionList(
                        ("角色档案", "characters", True),
                        *[(label, namespace, True) for label, namespace in self.configuration_service.category_labels()],
                        id="config-categories",
                    )
                    with Horizontal(classes="actions"):
                        yield Button("全选类别", id="select-all-config-categories")
                        yield Button("清空选择", id="clear-config-categories")
                    yield Label("新格式 neo-agent/config/v1；配置包可能包含记忆与关系数据。", classes="eyebrow")
                    yield TextArea(id="config-json", soft_wrap=True, classes="editor")
                    yield Static("导入前可先校验并查看将写入的记录数量。", id="config-preview", classes="listing")
                    with Horizontal(classes="actions"):
                        yield Button("导出配置", id="export-config")
                        yield Button("校验 / 预览导入", id="preview-config")
                        yield Button("导入新格式配置", id="import-config", variant="primary")
                with VerticalScroll(id="channels", classes="page"):
                    yield Static(id="channel-list", classes="listing")
                    yield Input(placeholder="连接器 ID", id="channel-id")
                    yield Input(placeholder="平台与频道名称", id="channel-name")
                    yield Input(placeholder="平台类型（adapter）", id="channel-platform")
                    yield Input(placeholder="公开配置 JSON（不得放密钥）", id="channel-config")
                    yield Button("保存频道连接配置", id="save-channel", variant="primary")
                with VerticalScroll(id="settings", classes="page"):
                    yield Static(id="settings-view", classes="listing")
                    yield Label("模型密钥由环境变量提供，不写入 PyVDisk 配置备份。", classes="eyebrow")
                yield Label("↑↓ 选择 · Enter 打开 · R 刷新 · Q 退出", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#nav", ListView).index = 0
        self.set_interval(5, self._run_schedule_worker)
        self.refresh_view()

    def _run_schedule_worker(self) -> None:
        try:
            self.worker.run_once(limit=8)
        except Exception as exc:
            self.store.append_event("schedule.worker.error", {"error": str(exc)})
        if self.active_view == "日程":
            self.query_one("#schedule-list", Static).update(self._schedule_listing())

    def _status_text(self) -> str:
        configured = bool(os.getenv("OPENAI_API_KEY") or os.getenv("SILICONFLOW_API_KEY"))
        return f"● Runtime 在线\n◉ PyVDisk 已连接\n◇ 模型 {'已配置' if configured else '未配置'}\n⌁ 定时 worker 活跃"

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
            if action == "send-chat": await self.send_chat()
            elif action == "save-character": self.save_character()
            elif action == "load-character": self.load_character()
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
            self.store.append_event("tui.operation.failed", {"action": action, "error": str(exc)})
        self.refresh_view()

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

        tasks = {(task.get("payload") or {}).get("schedule_id"): task for task in self.store.schedule_tasks()}
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
            due = datetime.fromisoformat(item["due_at"].replace("Z", "+00:00"))
            if start_date is not None and not (start_date <= due.astimezone().date() <= end_date):
                continue
            task = tasks.get(item["id"])
            queue_status = task.get("status", "未到期（待 worker 入列）") if task else ("待到期" if item.get("status") == "pending" else "无活动任务")
            if item.get("status") == "awaiting_delivery":
                queue_status = "已持久化待发送（当前未配置平台 adapter）"
            end = f" — {item['end_at']}" if item.get("end_at") else ""
            rows.append(f"◷ {item['due_at']}{end} · {item['title']} [{item['id']}]\n  {item.get('description', '')}\n  类型：{item.get('type', 'appointment')} · 优先级：{item.get('priority', 'medium')} · 可查询：{'是' if item.get('is_queryable', True) else '否'}\n  协作：{item.get('collaboration_status', 'not_required')} · 状态：{item.get('status', 'pending')} · 队列：{queue_status}")
        return "\n\n".join(rows) or "当前筛选条件下暂无日程。"

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
        self.notify(f"已创建提醒：{record['title']}", title="日程")

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
        self.notify("建议已填入日程表单；请检查后点击“创建提醒”写入。", title="待确认建议")

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

    def save_character(self) -> None:
        cid = self._value("#character-id")
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
        self.store.save_character(cid, profile)

    def load_character(self) -> None:
        cid = self._value("#character-id")
        character = self.store.character(cid)
        if character is None:
            raise KeyError(f"找不到角色：{cid}")
        for field in ("name", "gender", "role", "age", "height", "weight", "hobby"):
            self.query_one(f"#character-{field}", Input).value = str(character.get(field, ""))
        self.query_one("#character-personality", TextArea).text = str(character.get("personality", ""))
        self.query_one("#character-background", TextArea).text = str(character.get("background", ""))
        self.notify(f"已载入角色：{character.get('name', cid)}", title="角色")

    def archive_character(self) -> None:
        self.store.archive_character(self._value("#character-id"))

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
        selected = self.query_one("#chat-character", Select).value
        character = self.store.character(str(selected)) if selected not in (Select.NULL, None) else None
        if not character:
            characters = self.store.characters()
            character = characters[0] if characters else None
        if not character: raise ValueError("请先创建虚拟群友")
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
        RelationshipService(self.store).record_interaction(rid, note=f"{self._value('#relationship-peer')}: {self._value('#relationship-note')}", delta=delta)

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
        mapping = {"总览": "content", "虚拟群友": "characters", "对话": "chat", "事件流": "events", "日程": "schedules", "知识库": "knowledge", "关系": "relationships", "环境与域": "environment", "能力与 NPS": "plugins", "运行记录": "records", "存储与记忆": "storage", "频道连接": "channels", "系统设置": "settings", "实体管理": "entities", "表达风格": "expressions", "人机协作": "human-questions", "任务编排": "collaboration"}
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
                    "PyVDisk：VFS 文档 + VectorDisk 记忆 + LogDisk 事件 + CheckpointStore / DurableQueue\n\n"
                    "快捷键：1-9 导航 · E 事件 · S 日程 · R 刷新 · Q 退出")
            self._update("#content", text)
        elif self.active_view == "虚拟群友": self._update("#character-list", self._character_listing())
        elif self.active_view == "对话":
            chars = self.store.characters()
            selector = self.query_one("#chat-character", Select)
            selector.set_options([(c["name"], c["id"]) for c in chars])
            if chars: selector.value = chars[0]["id"]; self.query_one("#chat-log", Static).update(self._render_transcript(chars[0]))
            else: self.query_one("#chat-log", Static).update("暂无角色，请先创建虚拟群友。")
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
            self._update("#storage-view", f"DataDisk 镜像：{overview['disk_image']}\n\n角色：/characters/<id>/profile.json\n事件：LogDisk / neo-agent-events\n向量记忆集合：{collections}\n日程任务：CheckpointStore + DurableQueue（到期后入列）\n\n配置导入导出采用 neo-agent/config/v1，不包含密钥与会话对话。")
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
