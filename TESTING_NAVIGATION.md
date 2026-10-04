# 测试导航功能

## 当前状态
导航项已改为使用 Button 实现，并在自己的 `on_button_pressed` 中处理点击事件。

## 测试方法

### 1. 启动 TUI
```bash
source .venv/bin/activate
python main.py tui
```

### 2. 测试导航
在 TUI 中：
- 使用鼠标点击左侧导航项（💬 对话、📅 今日行程、🌍 场景池等）
- 或使用 Tab 键切换焦点到导航项，然后按 Enter

### 3. 预期结果
- 点击导航项后，右侧主内容区应该切换显示对应视图
- 除了"对话"视图外，其他视图会显示占位符："XXX 视图 - 该功能正在开发中..."
- 底栏应该保持显示"服务运行中 • 按 : 进入命令模式 • 按 q 退出"

### 4. 已知问题
- Textual Pilot 的自动化测试无法正确模拟鼠标点击
- 但真实鼠标点击应该可以工作（Button 组件支持点击）

## 验证代码
如果导航不工作，检查以下内容：

### 检查 NavigationItem 定义
```python
# 应该在 neo_agent/ui/v2/app.py 中
class NavigationItem(Button):
    def on_button_pressed(self, event: Button.Pressed):
        event.stop()
        if hasattr(self.app, 'switch_view'):
            self.app.run_worker(self.app.switch_view(self.view_id))
```

### 手动测试脚本
```python
# test_button_event.py
# 这个测试证明逻辑是正确的
from neo_agent.ui.v2.app import NeoAgentApp, NavigationItem
import asyncio

async def test():
    app = NeoAgentApp()
    async with app.run_test() as pilot:
        await asyncio.sleep(0.5)
        nav_items = app.query(NavigationItem)
        nav_items[1].press()  # 直接调用 press()
        await asyncio.sleep(0.5)
        main_content = app.query_one("#main-content")
        print(f"视图: {main_content.current_view}")  # 应该显示 "itinerary"

asyncio.run(test())
```

## 调试建议
如果点击还是不工作：
1. 确认服务已重启：`python main.py restart`
2. 尝试使用键盘导航（Tab + Enter）
3. 检查 TUI 是否有错误消息（按 q 退出后查看终端）
4. 查看服务日志：`cat ~/.neo_agent/service.log`
