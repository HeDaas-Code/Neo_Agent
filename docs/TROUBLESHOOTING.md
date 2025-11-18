# 故障排查指南

**中文** | [English](TROUBLESHOOTING_EN.md)

本文档帮助您快速诊断和解决使用 Neo_Agent 时遇到的常见问题。

## 目录

- [安装和启动问题](#安装和启动问题)
- [API相关问题](#api相关问题)
- [记忆系统问题](#记忆系统问题)
- [知识库问题](#知识库问题)
- [情感分析问题](#情感分析问题)
- [GUI问题](#gui问题)
- [性能问题](#性能问题)
- [数据问题](#数据问题)

---

## 安装和启动问题

### 问题1: Python版本不兼容

**症状**：
```
SyntaxError: invalid syntax
```

**原因**：Python版本过低（低于3.8）

**解决方案**：
```bash
# 检查Python版本
python --version

# 升级Python（Ubuntu/Debian）
sudo apt update
sudo apt install python3.12

# macOS（使用Homebrew）
brew install python@3.12

# Windows：从官网下载安装
```

### 问题2: 依赖包安装失败

**症状**：
```
ERROR: Could not find a version that satisfies the requirement
```

**解决方案**：

```bash
# 方案1：升级pip
pip install --upgrade pip

# 方案2：使用国内镜像
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 方案3：逐个安装依赖
pip install langchain
pip install langchain-community
pip install langchain-core
pip install python-dotenv
pip install requests
```

### 问题3: 启动时报错 "No module named 'xxx'"

**症状**：
```
ModuleNotFoundError: No module named 'langchain'
```

**原因**：虚拟环境未激活或依赖未安装

**解决方案**：
```bash
# 激活虚拟环境
# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate

# 确认激活后重新安装
pip install -r requirements.txt

# 验证安装
pip list | grep langchain
```

### 问题4: .env文件未找到

**症状**：
```
FileNotFoundError: .env file not found
或 API密钥为None
```

**解决方案**：
```bash
# 检查是否存在.env文件
ls -la | grep .env

# 如果不存在，复制示例文件
cp example.env .env

# 编辑.env文件
nano .env  # 或使用其他编辑器

# 确保填写了必要的配置
SILICONFLOW_API_KEY=your_actual_key_here
```

---

## API相关问题

### 问题5: API密钥无效

**症状**：
```
HTTP 401 Unauthorized
或 "Invalid API key"
```

**诊断步骤**：
```python
# 检查环境变量加载
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('SILICONFLOW_API_KEY')
print(f"API Key: {api_key[:10]}..." if api_key else "None")
```

**解决方案**：
1. 确认API密钥正确复制（无多余空格）
2. 访问 [SiliconFlow](https://siliconflow.cn/) 验证密钥有效性
3. 检查.env文件格式：
   ```env
   SILICONFLOW_API_KEY=sk-xxxxx  # 不要有引号
   ```

### 问题6: API调用超时

**症状**：
```
requests.exceptions.Timeout
或 "Request timed out"
```

**诊断**：
```bash
# 测试网络连接
ping api.siliconflow.cn

# 测试API连接
curl -X POST https://api.siliconflow.cn/v1/chat/completions \
  -H "Authorization: Bearer your_api_key" \
  -H "Content-Type: application/json" \
  -d '{"model": "deepseek-ai/DeepSeek-V3", "messages": [{"role": "user", "content": "test"}]}'
```

**解决方案**：
1. 检查网络连接
2. 尝试使用代理（如果在受限网络环境）
3. 增加超时时间（修改代码）：
   ```python
   requests.post(url, json=data, timeout=60)  # 增加到60秒
   ```

### 问题7: API额度不足

**症状**：
```
HTTP 429 Too Many Requests
或 "Quota exceeded"
```

**解决方案**：
1. 登录SiliconFlow查看剩余额度
2. 充值或等待额度重置
3. 临时解决：减少调用频率
   ```env
   # 调整触发频率
   # 知识提取改为每10轮（默认5轮）
   # 情感分析改为每20轮（默认10轮）
   ```

### 问题8: 模型不可用

**症状**：
```
"Model not found"
或 "Model is not available"
```

**解决方案**：
```env
# 尝试其他可用模型
MODEL_NAME=deepseek-ai/DeepSeek-V3
# 或
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct

# 查看SiliconFlow文档获取完整模型列表
```

---

## 记忆系统问题

### 问题9: 记忆不保存

**症状**：重启后对话历史丢失

**诊断**：
```python
from database_manager import DatabaseManager

db = DatabaseManager()
memory = db.load_data("memory_data")
print(f"Memory data: {memory}")
```

**解决方案**：
1. 检查文件写入权限
   ```bash
   ls -l chat_agent.db
   chmod 644 chat_agent.db
   ```

2. 检查磁盘空间
   ```bash
   df -h
   ```

3. 手动保存测试
   ```python
   agent = ChatAgent()
   agent.chat("测试")
   agent.memory_manager.save_memory()
   ```

### 问题10: 长期记忆未生成

**症状**：对话超过20轮但没有生成长期记忆

**诊断**：
```python
# 启用DEBUG模式
# .env 中设置 DEBUG_MODE=True

# 查看debug日志
tail -f debug.log | grep "archive"
```

**解决方案**：
1. 确认对话轮数正确计算：
   ```python
   agent = ChatAgent()
   for i in range(21):
       agent.chat(f"测试{i}")
   
   summaries = agent.get_long_term_summaries()
   print(f"长期记忆数量: {len(summaries)}")
   ```

2. 检查LLM是否正常响应
3. 查看错误日志

### 问题11: 记忆文件损坏

**症状**：
```
json.decoder.JSONDecodeError
```

**解决方案**：

方案1：恢复备份
```bash
# 如果有备份
cp chat_agent.db.backup chat_agent.db
```

方案2：删除损坏文件（丢失数据）
```bash
# 备份损坏文件
mv chat_agent.db chat_agent.db.corrupted

# 重新启动程序会创建新文件
python gui_enhanced.py
```

方案3：手动修复
```python
import sqlite3

# 尝试读取部分数据
conn = sqlite3.connect('chat_agent.db')
cursor = conn.cursor()
cursor.execute("SELECT key, value FROM kv_store")
rows = cursor.fetchall()

# 重建数据库
# ...
```

---

## 知识库问题

### 问题12: 知识未提取

**症状**：5轮对话后没有提取知识

**诊断步骤**：

1. 启用DEBUG模式查看日志
2. 检查触发条件：
   ```python
   agent = ChatAgent()
   
   # 确保刚好5轮
   for i in range(5):
       response = agent.chat(f"我叫张三，我喜欢编程")
   
   # 检查知识
   knowledge = agent.get_knowledge_items()
   print(f"知识数量: {len(knowledge)}")
   ```

3. 查看API调用是否成功

**解决方案**：
- 确保对话内容包含可提取的信息
- 提供更明确的个人信息
- 检查API额度

### 问题13: 基础知识不生效

**症状**：AI回答不使用基础知识

**诊断**：
```python
from base_knowledge import BaseKnowledge

base_kb = BaseKnowledge()

# 添加测试知识
base_kb.add_base_fact("测试实体", "这是测试内容", "测试")

# 验证是否保存
fact = base_kb.get_base_fact("测试实体")
print(fact)

# 查看所有基础知识
all_facts = base_kb.get_all_base_facts()
print(f"基础知识数量: {len(all_facts)}")
```

**解决方案**：

1. 确认实体名称匹配（不区分大小写）
2. 检查debug日志中的实体识别：
   ```bash
   grep "实体提取" debug.log
   grep "基础知识" debug.log
   ```

3. 手动测试实体识别：
   ```python
   from chat_agent import ChatAgent
   
   agent = ChatAgent()
   # 在提问中明确使用实体名
   response = agent.chat("你知道测试实体吗？")
   ```

### 问题14: 知识搜索无结果

**症状**：搜索知识库返回空列表

**解决方案**：
```python
from knowledge_base import KnowledgeBase
from database_manager import DatabaseManager

kb = KnowledgeBase(DatabaseManager(), None)

# 查看所有知识
all_knowledge = kb.get_all_knowledge()
print(f"总知识数: {len(all_knowledge)}")

# 测试搜索
results = kb.search_knowledge("关键词")
print(f"搜索结果: {len(results)}")

# 尝试不同的搜索词
```

---

## 情感分析问题

### 问题15: 情感分析未触发

**症状**：10轮对话后没有自动情感分析

**诊断**：
```python
agent = ChatAgent()

# 精确10轮对话
for i in range(10):
    agent.chat(f"对话 {i+1}")

# 检查情感数据
emotion_history = agent.get_emotion_history()
print(f"情感分析次数: {len(emotion_history)}")
```

**解决方案**：
1. 检查轮数计数是否正确
2. 查看debug日志：
   ```bash
   grep "情感分析" debug.log
   ```
3. 手动触发测试：
   ```python
   emotion = agent.analyze_emotion()
   print(emotion)
   ```

### 问题16: 情感雷达图不显示

**症状**：GUI中情感标签页为空

**解决方案**：

1. 确认已进行过至少一次情感分析
2. 切换到"💖 情感关系"标签页
3. 点击"🔍 分析情感关系"按钮
4. 检查数据库中是否有情感数据：
   ```python
   from database_manager import DatabaseManager
   
   db = DatabaseManager()
   emotion_data = db.load_data("emotion_data", [])
   print(f"情感记录数: {len(emotion_data)}")
   ```

### 问题17: 情感评分异常

**症状**：所有维度评分都是0或100

**原因**：LLM响应格式错误或解析失败

**解决方案**：
1. 查看完整的API响应日志
2. 尝试使用不同的模型
3. 调整temperature参数：
   ```env
   TEMPERATURE=0.7  # 降低温度以获得更稳定的输出
   ```

---

## GUI问题

### 问题18: GUI无法启动

**症状**：
```
_tkinter.TclError: no display name and no $DISPLAY environment variable
```

**原因**：无图形界面环境（远程服务器）

**解决方案**：

方案1：使用命令行版本
```bash
python chat_agent.py
```

方案2：使用X11转发（Linux）
```bash
# 启用X11转发
ssh -X user@server

# 或使用VNC
```

方案3：安装虚拟显示
```bash
# Ubuntu
sudo apt install xvfb
xvfb-run python gui_enhanced.py
```

### 问题19: GUI窗口过小或布局错乱

**解决方案**：
1. 调整窗口大小（最小1000x700）
2. 检查显示器分辨率
3. 修改代码中的窗口大小：
   ```python
   # gui_enhanced.py
   self.root.geometry("1200x800")  # 调整为合适的大小
   ```

### 问题20: GUI卡顿或无响应

**原因**：LLM调用阻塞主线程

**诊断**：查看是否在主线程中直接调用API

**解决方案**：确保使用异步调用
```python
# 正确的方式（已在代码中实现）
def send_message(self):
    threading.Thread(target=self._send_message_thread).start()
```

---

## 性能问题

### 问题21: 响应速度慢

**诊断**：
```python
import time

start = time.time()
response = agent.chat("测试")
end = time.time()

print(f"响应时间: {end - start:.2f}秒")
```

**解决方案**：

1. 使用更快的模型：
   ```env
   MODEL_NAME=Qwen/Qwen2.5-7B-Instruct  # 通常更快
   ```

2. 减少MAX_TOKENS：
   ```env
   MAX_TOKENS=1000  # 从2000降低到1000
   ```

3. 关闭DEBUG模式（生产环境）：
   ```env
   DEBUG_MODE=False
   ```

4. 优化网络连接

### 问题22: 内存占用过高

**诊断**：
```python
import psutil
import os

process = psutil.Process(os.getpid())
memory_mb = process.memory_info().rss / 1024 / 1024
print(f"内存占用: {memory_mb:.2f} MB")
```

**解决方案**：

1. 定期清理日志：
   ```bash
   # 清空debug日志
   > debug.log
   ```

2. 减少保留的消息数：
   ```env
   MAX_MEMORY_MESSAGES=30  # 从50降低
   ```

3. 定期重启程序

### 问题23: 数据库文件过大

**诊断**：
```bash
ls -lh chat_agent.db
du -h chat_agent.db
```

**解决方案**：

1. 清理旧数据：
   ```python
   from database_manager import DatabaseManager
   
   db = DatabaseManager()
   
   # 删除旧的情感数据（保留最近10条）
   emotion_data = db.load_data("emotion_data", [])
   db.save_data("emotion_data", emotion_data[-10:])
   ```

2. 导出后重建：
   ```python
   # 导出重要数据
   # 删除数据库文件
   # 重新启动程序
   ```

3. 定期归档：
   ```bash
   # 创建归档脚本
   DATE=$(date +%Y%m%d)
   cp chat_agent.db archive/chat_agent_$DATE.db
   ```

---

## 数据问题

### 问题24: 数据丢失

**预防措施**：

1. 定期备份：
   ```bash
   #!/bin/bash
   # backup.sh
   cp chat_agent.db backup/chat_agent_$(date +%Y%m%d_%H%M%S).db
   ```

2. 使用版本控制（排除敏感数据）
3. 云端同步备份

**恢复方法**：
```bash
# 从备份恢复
cp backup/chat_agent_20250115.db chat_agent.db
```

### 问题25: 数据迁移

**迁移到新电脑**：

```bash
# 旧电脑：打包数据
tar -czf neo_agent_data.tar.gz chat_agent.db .env

# 传输文件
scp neo_agent_data.tar.gz user@new-computer:~/

# 新电脑：解压
cd ~/neo_agent/Neo_Agent
tar -xzf ~/neo_agent_data.tar.gz

# 启动验证
python gui_enhanced.py
```

---

## 调试技巧

### 启用详细日志

```env
DEBUG_MODE=True
DEBUG_LOG_FILE=debug.log
```

### 查看特定类型的日志

```bash
# 查看错误
grep "error" debug.log

# 查看API调用
grep "request\|response" debug.log

# 实时监控
tail -f debug.log | grep "error"
```

### Python交互式调试

```python
# 在代码中添加断点
import pdb; pdb.set_trace()

# 或使用ipdb（需要安装）
import ipdb; ipdb.set_trace()
```

### 使用Debug GUI

1. 启用DEBUG_MODE
2. 打开GUI
3. 切换到"🔧 Debug日志"标签页
4. 使用类型筛选功能
5. 查看实时日志流

---

## 获取帮助

如果以上方法都无法解决您的问题：

1. **查看文档**：
   - [README.md](../README.md)
   - [API文档](API.md)
   - [开发指南](DEVELOPMENT.md)

2. **搜索已知问题**：
   - [GitHub Issues](https://github.com/HeDaas-Code/Neo_Agent/issues)

3. **提交新Issue**：
   - 详细描述问题
   - 提供错误日志
   - 说明环境信息（Python版本、操作系统等）
   - 提供重现步骤

4. **联系维护者**：
   - 在Issue中 @维护者
   - 查看README中的联系方式

---

## 常用诊断命令

```bash
# 系统信息
python --version
pip --version
pip list | grep langchain

# 检查文件
ls -lh chat_agent.db
file chat_agent.db

# 检查进程
ps aux | grep python

# 检查网络
ping api.siliconflow.cn
curl -I https://api.siliconflow.cn

# 检查日志
tail -100 debug.log
grep -i error debug.log

# 测试Python环境
python -c "import langchain; print(langchain.__version__)"
python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('SILICONFLOW_API_KEY')[:10])"
```

---

祝您使用顺利！如有任何问题，欢迎反馈。
