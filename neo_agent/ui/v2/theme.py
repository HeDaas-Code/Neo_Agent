"""
Neo Agent TUI 琥珀主题
配色系统：温暖琥珀色调，五级深度表面 + 琥珀金强调色
"""

AMBER_THEME = """
/* ===== 全局样式 ===== */
Screen {
    background: #050302;
}

/* ===== 按钮通用样式 ===== */
Button {
    height: auto;
    min-width: 8;
    background: #12100D;
    color: #F5E6D3;
    border: none;
    padding: 1 2;
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
    color: #F5E6D3;
}

Button.-default {
    background: #12100D;
    color: #C9B89A;
}

/* ===== 输入框通用样式 ===== */
Input {
    background: #12100D;
    color: #F5E6D3;
    border: solid #1C1812;
}

Input:focus {
    border: solid #E9A568;
}

Input > .input--placeholder {
    color: #8A7A66;
}

/* ===== DataTable 样式 ===== */
DataTable {
    background: #0A0805;
    color: #F5E6D3;
}

DataTable > .datatable--header {
    background: #12100D;
    color: #E9A568;
    text-style: bold;
}

DataTable > .datatable--cursor {
    background: #1C1812;
    color: #E9A568;
}

DataTable:focus > .datatable--cursor {
    background: #2B231C;
}

/* ===== RichLog 样式 ===== */
RichLog {
    background: #050302;
    color: #F5E6D3;
    scrollbar-background: #0A0805;
    scrollbar-color: #8A6B4F;
}

/* ===== Label 样式 ===== */
Label {
    color: #F5E6D3;
}

/* ===== Static 样式 ===== */
Static {
    color: #C9B89A;
}

/* ===== 滚动条样式 ===== */
ScrollView > .scrollbar--vertical {
    background: #0A0805;
}

ScrollView > .scrollbar--vertical > .scrollbar--handle {
    background: #8A6B4F;
}

ScrollView > .scrollbar--vertical:hover > .scrollbar--handle {
    background: #D4863C;
}

VerticalScroll > .scrollbar--vertical {
    background: #0A0805;
}

VerticalScroll > .scrollbar--vertical > .scrollbar--handle {
    background: #8A6B4F;
}

/* ===== Container 样式 ===== */
Container {
    background: #050302;
}
"""
