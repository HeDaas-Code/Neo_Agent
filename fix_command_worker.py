"""修复命令面板的 worker 问题"""

with open("neo_agent/ui/v2/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 将 action_command_mode 改为使用 run_worker
old_action = '''    async def action_command_mode(self):
        """打开命令面板"""
        result = await self.push_screen_wait(CommandPalette())
        if result:
            await self.handle_command(result)'''

new_action = '''    def action_command_mode(self):
        """打开命令面板"""
        self.run_worker(self._open_command_palette())
    
    async def _open_command_palette(self):
        """打开命令面板（worker）"""
        result = await self.push_screen_wait(CommandPalette())
        if result:
            await self.handle_command(result)'''

content = content.replace(old_action, new_action)

with open("neo_agent/ui/v2/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("✓ 修复了命令面板的 worker 问题")
