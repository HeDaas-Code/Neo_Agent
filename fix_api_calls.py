"""修复所有 client.call 的参数格式"""
import re

with open("neo_agent/ui/v2/app.py", "r", encoding="utf-8") as f:
    content = f.read()

# 将 await self.client.call("method", key=value) 替换为 await self.client.call("method", {"key": value})
replacements = [
    # session.get_history
    (r'await self\.client\.call\("session\.get_history", limit=(\d+)\)',
     r'await self.client.call("session.get_history", {"limit": \1})'),
    
    # session.send_message
    (r'await self\.client\.call\("session\.send_message", text=(\w+)\)',
     r'await self.client.call("session.send_message", {"text": \1})'),
    
    # schedule.get_today_itinerary
    (r'await self\.client\.call\("schedule\.get_today_itinerary"\)',
     r'await self.client.call("schedule.get_today_itinerary", {})'),
    
    # scene.list_pool
    (r'await self\.client\.call\("scene\.list_pool"\)',
     r'await self.client.call("scene.list_pool", {})'),
    
    # scene.get_current
    (r'await self\.client\.call\("scene\.get_current"\)',
     r'await self.client.call("scene.get_current", {})'),
    
    # memory.search with query
    (r'await self\.client\.call\("memory\.search", query=([^,\)]+), limit=(\d+)\)',
     r'await self.client.call("memory.search", {"query": \1, "limit": \2})'),
    
    # memory.search with only query
    (r'await self\.client\.call\("memory\.search", query=([^,\)]+)\)',
     r'await self.client.call("memory.search", {"query": \1})'),
    
    # relationship.list_all
    (r'await self\.client\.call\("relationship\.list_all"\)',
     r'await self.client.call("relationship.list_all", {})'),
    
    # system.get_audit_logs
    (r'await self\.client\.call\("system\.get_audit_logs", filter=([^,\)]+), limit=(\d+)\)',
     r'await self.client.call("system.get_audit_logs", {"filter": \1, "limit": \2})'),
    
    # character.get_profile
    (r'await self\.client\.call\("character\.get_profile"\)',
     r'await self.client.call("character.get_profile", {})'),
    
    # session.get_context
    (r'await self\.client\.call\("session\.get_context"\)',
     r'await self.client.call("session.get_context", {})'),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open("neo_agent/ui/v2/app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("已修复所有 API 调用")
