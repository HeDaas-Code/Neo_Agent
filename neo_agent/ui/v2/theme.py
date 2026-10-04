"""琥珀温暖主题：五级深度 + 精心设计的配色"""

# Textual CSS 主题
AMBER_THEME = """
/* ========== 琥珀温暖主题 ========== */

* {
    scrollbar-background: $surface-1;
    scrollbar-color: $accent-muted;
    scrollbar-color-hover: $accent-primary;
}

Screen {
    background: $surface-0;
}

/* ========== 顶栏状态栏 ========== */
.status-bar {
    background: $surface-1;
    color: $text-primary;
    height: 1;
    dock: top;
    padding: 0 1;
}

.status-item {
    color: $text-secondary;
}

.status-active {
    color: $status-active;
}

/* ========== 底栏 ========== */
.footer {
    background: $surface-1;
    color: $text-secondary;
    height: 1;
    dock: bottom;
    padding: 0 1;
}

/* ========== 左侧导航 ========== */
.sidebar {
    width: 25;
    background: $surface-1;
    border-right: solid $surface-3;
}

.nav-item {
    background: $surface-1;
    color: $text-primary;
    padding: 0 2;
    height: auto;
}

.nav-item:hover {
    background: $surface-2;
    color: $accent-primary;
}

.nav-item.--active {
    background: $surface-3;
    color: $accent-primary;
    border-left: solid $accent-primary;
}

.nav-section-header {
    color: $text-dim;
    background: $surface-1;
    padding: 1 2 0 2;
}

/* ========== 主内容区 ========== */
.main-content {
    background: $surface-0;
    padding: 1 2;
}

/* ========== 对话视图 ========== */
.chat-container {
    height: 1fr;
    background: $surface-0;
}

.chat-log {
    background: $surface-0;
    color: $text-primary;
    height: 1fr;
    border: solid $surface-3;
}

.chat-input-container {
    height: auto;
    background: $surface-1;
    padding: 1;
}

Input {
    background: $surface-2;
    color: $text-primary;
    border: solid $surface-4;
}

Input:focus {
    border: solid $accent-primary;
}

/* ========== 按钮 ========== */
Button {
    background: $surface-2;
    color: $text-primary;
    border: solid $surface-4;
    height: auto;
    min-width: 10;
}

Button:hover {
    background: $surface-3;
    color: $accent-primary;
    border: solid $accent-primary;
}

Button.-primary {
    background: $accent-primary;
    color: $surface-0;
    border: none;
}

Button.-primary:hover {
    background: $accent-secondary;
}

/* ========== 数据表格 ========== */
DataTable {
    background: $surface-0;
    color: $text-primary;
}

DataTable > .datatable--header {
    background: $surface-2;
    color: $accent-primary;
}

DataTable > .datatable--cursor {
    background: $surface-3;
}

/* ========== 加载指示器 ========== */
LoadingIndicator {
    background: $surface-1;
    color: $accent-primary;
}

/* ========== 模态面板 ========== */
.modal-overlay {
    background: rgba(5, 3, 2, 0.8);
}

.modal-panel {
    background: $surface-1;
    border: solid $accent-primary;
    padding: 2;
}

.modal-title {
    color: $accent-primary;
    text-style: bold;
}

/* ========== 命令面板 ========== */
.command-palette {
    background: $surface-1;
    border: solid $accent-primary;
    height: auto;
    max-height: 20;
}

.command-input {
    background: $surface-2;
    color: $text-primary;
}

.command-suggestions {
    background: $surface-1;
    color: $text-secondary;
}

/* ========== 标签与状态 ========== */
.tag {
    background: $surface-3;
    color: $text-primary;
    padding: 0 1;
}

.tag-active {
    background: $accent-primary;
    color: $surface-0;
}

.status-connected {
    color: $status-success;
}

.status-disconnected {
    color: $status-error;
}

.status-loading {
    color: $status-active;
}
"""

# CSS 变量定义
AMBER_VARIABLES = """
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
"""

# 完整主题
FULL_THEME = AMBER_VARIABLES + "\n" + AMBER_THEME
