"""创建统一的视图文件，整合 app.py 和 views.py 中的视图"""
import sys

# 从 views.py 读取完整的视图实现
with open('neo_agent/ui/v2/views.py', 'r') as f:
    views_content = f.read()

# 从 app.py 读取当前的代码
with open('neo_agent/ui/v2/app.py', 'r') as f:
    app_lines = f.readlines()

# 找到 ChatView 开始的位置
chat_view_start = None
for i, line in enumerate(app_lines):
    if 'class ChatView(Vertical):' in line:
        chat_view_start = i
        break

# 找到 MainContent 开始的位置（视图定义结束）
main_content_start = None
for i, line in enumerate(app_lines):
    if 'class MainContent(Container):' in line:
        main_content_start = i
        break

if chat_view_start and main_content_start:
    print(f"找到视图定义区域：行 {chat_view_start+1} - {main_content_start}")
    print(f"当前 app.py 中定义了 {main_content_start - chat_view_start} 行的视图代码")
    print("\nviews.py 已经包含完整的视图实现，建议：")
    print("1. 从 app.py 中移除简化的视图定义")
    print("2. 从 views.py 导入完整视图")
    print("3. 保持 app.py 只负责应用结构和事件路由")
else:
    print("未找到视图定义")
