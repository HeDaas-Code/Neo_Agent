"""Neo Agent TUI 琥珀主题"""

FULL_THEME = """
/* ============ 全局变量 ============ */
$surface-0: #050302;
$surface-1: #0A0805;
$surface-2: #12100D;
$surface-3: #1C1812;
$surface-4: #2B231C;

$accent-primary: #E9A568;
$accent-secondary: #D4863C;
$accent-muted: #8A6B4F;

$text-primary: #F5E6D3;
$text-secondary: #C9B89A;
$text-dim: #8A7A66;

$status-active: #E9A568;
$status-idle: #8A6B4F;
$status-error: #D97757;
$status-success: #A8C079;

/* ============ 全局样式 ============ */
Screen {
    background: $surface-0;
    color: $text-primary;
}

/* ============ 状态栏 ============ */
#status-bar {
    dock: top;
    height: 1;
    background: $surface-1;
    color: $accent-primary;
    content-align: center middle;
    text-style: bold;
}

.status-bar {
    width: 100%;
    background: $surface-1;
    color: $accent-primary;
    text-align: center;
}

/* ============ 底栏 ============ */
#footer {
    dock: bottom;
    height: 1;
    background: $surface-1;
    color: $text-secondary;
    content-align: center middle;
}

.footer {
    background: $surface-1;
    color: $text-secondary;
    text-align: center;
}

/* ============ 主布局 ============ */
#main-layout {
    width: 100%;
    height: 100%;
}

/* ============ 侧边栏 ============ */
.sidebar {
    width: 20;
    background: $surface-1;
    border-right: solid $surface-3;
    padding: 1;
}

.nav-section-header {
    background: $surface-1;
    color: $text-dim;
    height: 1;
    margin-bottom: 1;
    text-align: center;
}

/* 导航项 - NavigationItem (Static) */
NavigationItem {
    height: 3;
    padding: 1;
    background: $surface-1;
    color: $text-secondary;
    width: 100%;
    margin-bottom: 1;
}

NavigationItem:hover {
    background: $surface-2;
    color: $text-primary;
}

NavigationItem.active {
    background: $surface-3;
    color: $accent-primary;
    border-left: thick $accent-primary;
    text-style: bold;
}

.nav-hint {
    background: $surface-1;
    color: $text-dim;
    height: 1;
    margin-bottom: 1;
}

/* ============ 主内容区 ============ */
.main-content {
    width: 100%;
    height: 100%;
    background: $surface-0;
    padding: 1 2;
}

/* ============ 视图容器 ============ */
.view-container {
    width: 100%;
    height: 100%;
    background: $surface-0;
}

.view-title {
    height: 3;
    content-align: left middle;
    text-style: bold;
    color: $accent-primary;
    margin-bottom: 1;
}

.view-subtitle {
    height: 2;
    color: $text-secondary;
    margin-bottom: 1;
}

.placeholder-view {
    width: 100%;
    height: 100%;
    content-align: center middle;
    background: $surface-1;
    color: $text-dim;
}

/* ============ 对话视图 ============ */
.chat-log {
    height: 1fr;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
    margin-bottom: 1;
}

.chat-input-container {
    height: 3;
    width: 100%;
}

.chat-input {
    width: 1fr;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    margin-right: 1;
}

#send-button {
    width: 10;
    background: $accent-primary;
    color: $surface-0;
}

#send-button:hover {
    background: $accent-secondary;
}

/* ============ 行程视图 ============ */
.itinerary-container {
    height: 1fr;
    overflow-y: scroll;
}

.itinerary-log {
    height: auto;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}

.refresh-button {
    width: 15;
    height: 3;
    background: $accent-muted;
    color: $text-primary;
    margin-top: 1;
}

.refresh-button:hover {
    background: $accent-primary;
}

/* ============ 场景池视图 ============ */
.scene-container {
    height: 1fr;
    overflow-y: scroll;
}

.scene-log {
    height: auto;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}

/* ============ 记忆视图 ============ */
.search-bar {
    height: 3;
    width: 100%;
    margin-bottom: 1;
}

.search-input {
    width: 1fr;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    margin-right: 1;
}

.search-button {
    width: 10;
    background: $accent-primary;
    color: $surface-0;
}

.search-button:hover {
    background: $accent-secondary;
}

.memory-container {
    height: 1fr;
    overflow-y: scroll;
}

.memory-log {
    height: auto;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}

/* ============ 关系视图 ============ */
.relationship-container {
    height: 1fr;
    overflow-y: scroll;
}

.relationship-log {
    height: auto;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}

/* ============ 审计视图 ============ */
.audit-container {
    height: 1fr;
    overflow-y: scroll;
}

.audit-log {
    height: auto;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}

/* ============ 数据表格 ============ */
.data-table {
    height: 1fr;
    background: $surface-1;
    border: solid $surface-3;
    margin-bottom: 1;
}

DataTable > .datatable--header {
    background: $surface-2;
    color: $accent-primary;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: $surface-3;
    color: $text-primary;
}

/* ============ 详情面板 ============ */
.detail-panel {
    height: 15;
    background: $surface-1;
    border: solid $surface-3;
    padding: 1;
    margin-top: 1;
}

.detail-title {
    height: 1;
    color: $accent-primary;
    text-style: bold;
    margin-bottom: 1;
}

.detail-content {
    height: 1fr;
    color: $text-secondary;
}

/* ============ 过滤栏 ============ */
.filter-bar {
    height: 3;
    width: 100%;
    margin-bottom: 1;
}

.filter-bar Button {
    margin-right: 1;
}

/* ============ 输入框通用 ============ */
Input {
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
}

Input:focus {
    border: solid $accent-primary;
}

/* ============ 按钮通用 ============ */
Button {
    background: $surface-2;
    color: $text-primary;
}

Button:hover {
    background: $surface-3;
    color: $accent-primary;
}

Button.-primary {
    background: $accent-primary;
    color: $surface-0;
    text-style: bold;
}

Button.-primary:hover {
    background: $accent-secondary;
}
"""

"""

/* Navigation item styles - clickable */
.nav-item {
    height: 3;
    padding: 1;
    background: $surface-1;
    color: $text-secondary;
    width: 100%;
    margin-bottom: 1;
}

.nav-item:hover {
    background: $surface-2;
    color: $text-primary;
}

.nav-item.active {
    background: $surface-3;
    color: $accent-primary;
    border-left: thick $accent-primary;
    text-style: bold;
}

/* Search styles */
.search-container {
    height: 3;
    width: 100%;
    margin-bottom: 1;
}

.search-input {
    width: 80%;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    margin-right: 1;
}

.search-button {
    width: 10;
    background: $accent-muted;
    color: $text-primary;
}

.search-button:hover {
    background: $accent-secondary;
}

/* View logs */
.memory-log,
.relationships-log,
.scenes-log,
.audit-log {
    height: 1fr;
    background: $surface-1;
    color: $text-primary;
    border: solid $surface-3;
    padding: 1;
}
"""
