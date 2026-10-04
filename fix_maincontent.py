"""修复 MainContent 的 id 冲突"""
import re

with open("neo_agent/ui/v2/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 找到 MainContent.__init__ 并移除 self.id 和 self.classes 设置
pattern = r'(class MainContent\(Container\):.*?def __init__\(self, client: AgentClient, \*\*kwargs\):.*?super\(\).__init__\(\*\*kwargs\).*?self\.client = client)\s+self\.id = "main-content"\s+self\.classes = "main-content"'

replacement = r'\1'

content = re.sub(pattern, replacement, content, flags=re.DOTALL)

with open("neo_agent/ui/v2/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("已修复 MainContent id 冲突")
