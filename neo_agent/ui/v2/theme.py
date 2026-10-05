"""
Neo Agent TUI 琥珀主题
配色系统：温暖琥珀色调
"""

AMBER_THEME = """
/* ===== 基础布局 ===== */
Screen {
    background: #050302;
}

#main-layout {
    height: 1fr;
    background: #050302;
}

/* ===== 顶栏 ===== */
.topbar {
    dock: top;
    height: 1;
    background: #0A0805;
    color: #C9B89A;
    content-align: center middle;
    text-style: bold;
}

/* ===== 侧边栏 ===== */
.sidebar {
    width: 20;
    background: #0A0805;
    border-right: solid #2B231C;
}

.nav-section-header {
    height: 1;
    background: #0A0805;
    color: #8A7A66;
    content-align: center middle;
    text-style: bold;
    padding: 0 1;
}

.nav-item {
    height: 3;
    background: #0A0805;
    color: #C9B89A;
    padding: 1 2;
}

.nav-item:hover {
    background: #12100D;
    color: #F5E6D3;
}

.nav-item.active {
    background: #1C1812;
    color: #E9A568;
    border-left: solid #E9A568;
    text-style: bold;
}

.nav-hint {
    height: 1;
    background: #0A0805;
    color: #8A7A66;
    padding: 0 2;
}

/* ===== 主内容区 ===== */
.main-content {
    width: 1fr;
    background: #050302;
    padding: 0 1;
}

.view-container {
    width: 1fr;
    height: 1fr;
    background: #050302;
}

.view-title {
    dock: top;
    height: 2;
    background: #0A0805;
    color: #E9A568;
    content-align: left middle;
    text-style: bold;
    padding: 0 2;
}

.section-header {
    height: 2;
    background: #12100D;
    color: #C9B89A;
    content-align: left middle;
    text-style: bold;
    padding: 0 1;
}

/* ===== 对话视图 ===== */
.chat-log {
    height: 1fr;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
}

.chat-input-container {
    dock: bottom;
    height: 3;
    background: #0A0805;
    padding: 0 1;
}

.chat-input {
    width: 1fr;
    background: #1C1812;
    color: #F5E6D3;
    border: none;
}

.chat-input:focus {
    border: solid #E9A568;
}

/* ===== 行程视图 ===== */
.action-bar {
    dock: top;
    height: 3;
    background: #0A0805;
    padding: 0 1;
}

.itinerary-table {
    height: 12;
    background: #0A0805;
    border: solid #2B231C;
}

DataTable {
    background: #0A0805;
    color: #F5E6D3;
}

DataTable > .datatable--header {
    background: #12100D;
    color: #D4863C;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1C1812;
    color: #E9A568;
}

DataTable:focus > .datatable--cursor {
    background: #2B231C;
}

.detail-log {
    height: 1fr;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
    margin-top: 1;
}

/* ===== 场景池视图 ===== */
.split-view {
    height: 1fr;
}

.scene-list {
    width: 40%;
    background: #050302;
}

.scene-detail {
    width: 1fr;
    background: #050302;
    margin-left: 1;
}

.scenes-table {
    height: 1fr;
    background: #0A0805;
    border: solid #2B231C;
}

/* ===== 记忆视图 ===== */
.search-container {
    dock: top;
    height: 3;
    background: #0A0805;
    padding: 0 1;
}

.search-input {
    width: 1fr;
    background: #1C1812;
    color: #F5E6D3;
    border: none;
}

.search-input:focus {
    border: solid #E9A568;
}

.search-button {
    margin-left: 1;
}

.memory-log {
    height: 1fr;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
    margin-top: 1;
}

/* ===== 关系视图 ===== */
.relationship-container {
    height: 1fr;
}

.status-log {
    height: 40%;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
    margin-top: 1;
}

.history-log {
    height: 1fr;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
    margin-top: 1;
}

/* ===== 审计日志视图 ===== */
.audit-log {
    height: 1fr;
    background: #050302;
    border: solid #2B231C;
    padding: 1;
    margin-top: 1;
}

/* ===== 按钮样式 ===== */
Button {
    height: 3;
    min-width: 10;
    background: #12100D;
    color: #F5E6D3;
    border: none;
    text-style: bold;
}

Button:hover {
    background: #1C1812;
    color: #E9A568;
}

Button:focus {
    background: #1C1812;
    border: solid #E9A568;
}

Button.-primary {
    background: #8A6B4F;
    color: #F5E6D3;
}

Button.-primary:hover {
    background: #D4863C;
}

.refresh-button {
    dock: top;
    margin: 1;
}

/* ===== 底栏 ===== */
.statusbar {
    dock: bottom;
    height: 1;
    background: #0A0805;
    color: #C9B89A;
    content-align: center middle;
}

/* ===== 输入框通用样式 ===== */
Input {
    background: #1C1812;
    color: #F5E6D3;
    border: none;
}

Input:focus {
    border: solid #E9A568;
}

Input > .input--placeholder {
    color: #8A7A66;
}

/* ===== RichLog 通用样式 ===== */
RichLog {
    background: #050302;
    color: #F5E6D3;
    scrollbar-background: #0A0805;
    scrollbar-color: #8A6B4F;
}

/* ===== 命令面板 ===== */
#command-palette {
    align: center middle;
    background: #12100D 80%;
}

#command-input {
    width: 60;
    background: #0A0805;
    color: #F5E6D3;
    border: solid #E9A568;
}

#command-suggestions {
    width: 60;
    height: 10;
    background: #0A0805;
    border: solid #2B231C;
    margin-top: 1;
}

/* ===== 滚动条 ===== */
ScrollView > .scrollbar--vertical {
    background: #0A0805;
}

ScrollView > .scrollbar--vertical > .scrollbar--handle {
    background: #8A6B4F;
}

ScrollView > .scrollbar--vertical:hover > .scrollbar--handle {
    background: #D4863C;
}
"""
