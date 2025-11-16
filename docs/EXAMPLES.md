# 使用示例

本文档提供 Neo_Agent 的各种使用场景和代码示例。

## 目录

- [基础使用](#基础使用)
- [进阶功能](#进阶功能)
- [自定义配置](#自定义配置)
- [实际应用场景](#实际应用场景)
- [代码集成](#代码集成)

---

## 基础使用

### 示例1: 简单对话

最基本的使用方式：

```python
from chat_agent import ChatAgent

# 创建代理实例
agent = ChatAgent()

# 开始对话
print("AI助手已启动，输入'退出'结束对话\n")

while True:
    user_input = input("你: ")
    
    if user_input.lower() in ['退出', 'quit', 'exit']:
        print("再见！")
        break
    
    response = agent.chat(user_input)
    print(f"小可: {response}\n")
```

### 示例2: 查看记忆

查看对话记忆和统计信息：

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行几轮对话
agent.chat("你好")
agent.chat("我叫张三")
agent.chat("我喜欢历史")

# 查看短期记忆
memory = agent.get_memory()
print(f"当前记忆: {len(memory)} 条消息")

# 打印所有消息
for msg in memory:
    role = "你" if msg['role'] == 'user' else "小可"
    print(f"{role}: {msg['content']}")
    print(f"时间: {msg['timestamp']}\n")
```

### 示例3: 启动GUI

使用图形界面：

```bash
# 命令行启动
python gui_enhanced.py
```

或在代码中启动：

```python
from gui_enhanced import EnhancedChatGUI
import tkinter as tk

root = tk.Tk()
app = EnhancedChatGUI(root)
root.mainloop()
```

---

## 进阶功能

### 示例4: 知识提取

自动从对话中提取知识：

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行5轮对话，触发知识提取
conversations = [
    "你好，我是李明",
    "我今年25岁",
    "我是一名程序员",
    "我喜欢阅读科幻小说",
    "我最喜欢的作家是刘慈欣"
]

for conv in conversations:
    response = agent.chat(conv)
    print(f"你: {conv}")
    print(f"AI: {response}\n")

# 查看提取的知识
knowledge_items = agent.get_knowledge_items()
print(f"\n提取到 {len(knowledge_items)} 条知识：")

for item in knowledge_items:
    print(f"\n类型: {item['type']}")
    print(f"标题: {item['title']}")
    print(f"内容: {item['content']}")
    print(f"标签: {', '.join(item['tags'])}")
```

### 示例5: 情感分析

分析对话中的情感关系：

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行10轮对话，触发自动情感分析
for i in range(10):
    user_msg = f"这是第{i+1}次对话，我感觉很开心"
    response = agent.chat(user_msg)

# 手动触发情感分析
emotion_data = agent.analyze_emotion()

# 显示情感分析结果
print("\n=== 情感关系分析 ===")
print(f"关系类型: {emotion_data['relationship_type']}")
print(f"情感基调: {emotion_data['emotional_tone']}")
print(f"总体评分: {emotion_data['overall_score']}/100")
print("\n五维评分:")
print(f"  亲密度: {emotion_data['亲密度']}/100")
print(f"  信任度: {emotion_data['信任度']}/100")
print(f"  愉悦度: {emotion_data['愉悦度']}/100")
print(f"  共鸣度: {emotion_data['共鸣度']}/100")
print(f"  依赖度: {emotion_data['依赖度']}/100")
print(f"\n主要话题: {', '.join(emotion_data['key_topics'])}")
print(f"\n详细分析:\n{emotion_data['analysis']}")
```

### 示例6: 基础知识管理

添加和使用基础知识：

```python
from base_knowledge import BaseKnowledge
from chat_agent import ChatAgent

# 创建基础知识库实例
base_kb = BaseKnowledge()

# 添加基础知识
base_kb.add_base_fact(
    entity_name="公司A",
    fact_content="公司A是一家人工智能企业",
    category="机构定义",
    description="这是关于公司A的核心定义"
)

base_kb.add_base_fact(
    entity_name="产品X",
    fact_content="产品X是公司A的旗舰产品",
    category="产品定义"
)

# 查看所有基础知识
facts = base_kb.get_all_base_facts()
print(f"基础知识库共有 {len(facts)} 条记录\n")

# 使用基础知识进行对话
agent = ChatAgent()
response = agent.chat("你知道公司A吗？")
print(f"AI: {response}")
# AI会根据基础知识回答，优先级最高

# 查找特定实体的基础知识
fact = base_kb.get_base_fact("公司A")
if fact:
    print(f"\n找到基础知识:")
    print(f"实体: {fact['entity_name']}")
    print(f"内容: {fact['fact_content']}")
    print(f"分类: {fact['category']}")
```

### 示例7: 长期记忆查看

查看归档的长期记忆：

```python
from chat_agent import ChatAgent

agent = ChatAgent()

# 进行20轮对话，触发记忆归档
for i in range(20):
    agent.chat(f"对话 {i+1}")

# 查看长期记忆
summaries = agent.get_long_term_summaries()
print(f"长期记忆: {len(summaries)} 条概括\n")

for summary in summaries:
    print(f"UUID: {summary['uuid']}")
    print(f"创建时间: {summary['created_at']}")
    print(f"结束时间: {summary['ended_at']}")
    print(f"对话轮数: {summary['rounds']}")
    print(f"消息数量: {summary['message_count']}")
    print(f"概括: {summary['summary']}")
    print("-" * 50)
```

---

## 自定义配置

### 示例8: 自定义角色

创建不同的AI角色：

**配置1: 技术专家角色**

```env
# .env 文件
CHARACTER_NAME=小智
CHARACTER_GENDER=男
CHARACTER_ROLE=技术专家
CHARACTER_AGE=30
CHARACTER_PERSONALITY=严谨专业，逻辑清晰
CHARACTER_HOBBY=编程、技术研究、开源项目
CHARACTER_BACKGROUND=我是一名资深软件工程师，叫小智。我有10年的编程经验，精通多种编程语言。我喜欢钻研新技术，经常参与开源项目。我说话比较专业，但也会用通俗易懂的方式解释技术问题。
```

**配置2: 生活助手角色**

```env
CHARACTER_NAME=小美
CHARACTER_GENDER=女
CHARACTER_ROLE=生活助手
CHARACTER_AGE=25
CHARACTER_PERSONALITY=温柔体贴，善于倾听
CHARACTER_HOBBY=烹饪、园艺、阅读
CHARACTER_BACKGROUND=我叫小美，是一位生活助手。我喜欢帮助别人解决生活中的各种问题，从烹饪到家居布置，从健康养生到时间管理。我会耐心倾听你的需求，并给出实用的建议。
```

### 示例9: 调整记忆参数

修改记忆系统的行为：

```env
# 更频繁的归档（10轮一次）
MAX_SHORT_TERM_ROUNDS=10

# 保存更多短期消息
MAX_MEMORY_MESSAGES=100

# 使用更强大的模型以提高概括质量
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.7  # 降低温度以获得更稳定的输出
```

### 示例10: 多语言配置

切换到不同的LLM模型：

```env
# 使用 Qwen 模型（速度快）
MODEL_NAME=Qwen/Qwen2.5-7B-Instruct
TEMPERATURE=0.8

# 使用 DeepSeek V3（性能好）
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.7

# 调整响应长度
MAX_TOKENS=3000  # 允许更长的回复
```

---

## 实际应用场景

### 场景1: 客户服务助手

```python
from chat_agent import ChatAgent
from base_knowledge import BaseKnowledge

# 初始化
agent = ChatAgent()
base_kb = BaseKnowledge()

# 添加公司产品知识
base_kb.add_base_fact(
    entity_name="产品售后",
    fact_content="产品提供1年免费保修，7天无理由退换",
    category="服务政策"
)

base_kb.add_base_fact(
    entity_name="工作时间",
    fact_content="客服工作时间：周一至周五 9:00-18:00",
    category="营业信息"
)

# 客户对话
def customer_service():
    print("客服助手已启动\n")
    while True:
        question = input("客户: ")
        if question.lower() in ['结束', '退出']:
            break
        
        response = agent.chat(question)
        print(f"客服: {response}\n")

customer_service()
```

### 场景2: 学习伴侣

```python
from chat_agent import ChatAgent
import json

agent = ChatAgent()

# 学习进度追踪
study_sessions = []

def study_session(subject: str):
    print(f"\n开始学习 {subject}")
    
    start_time = datetime.now()
    questions = []
    
    while True:
        question = input("你: ")
        if question.lower() == '结束学习':
            break
        
        response = agent.chat(f"关于{subject}：{question}")
        print(f"AI: {response}\n")
        questions.append(question)
    
    end_time = datetime.now()
    duration = (end_time - start_time).seconds // 60
    
    # 记录学习会话
    study_sessions.append({
        "subject": subject,
        "duration_minutes": duration,
        "questions_count": len(questions),
        "date": start_time.strftime("%Y-%m-%d %H:%M")
    })
    
    print(f"\n本次学习时长: {duration} 分钟")
    print(f"提问数量: {len(questions)}")

# 使用
study_session("Python编程")
study_session("数据结构")

# 查看学习统计
print("\n=== 学习统计 ===")
for session in study_sessions:
    print(f"{session['date']} - {session['subject']}: {session['duration_minutes']}分钟, {session['questions_count']}个问题")
```

### 场景3: 日记助手

```python
from chat_agent import ChatAgent
from datetime import datetime
import json

agent = ChatAgent()

class DiaryAssistant:
    def __init__(self):
        self.agent = ChatAgent()
        self.diary_file = "my_diary.json"
        self.diaries = self.load_diaries()
    
    def load_diaries(self):
        try:
            with open(self.diary_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_diaries(self):
        with open(self.diary_file, 'w', encoding='utf-8') as f:
            json.dump(self.diaries, f, ensure_ascii=False, indent=2)
    
    def write_diary(self):
        print("\n今天想记录些什么呢？（输入'完成'结束）")
        
        entries = []
        while True:
            entry = input("你: ")
            if entry.lower() == '完成':
                break
            
            # AI帮助整理和反思
            response = self.agent.chat(f"我今天: {entry}")
            print(f"AI: {response}\n")
            entries.append(entry)
        
        # 保存日记
        diary = {
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "entries": entries,
            "mood": self.get_mood_analysis()
        }
        self.diaries.append(diary)
        self.save_diaries()
        
        print(f"\n日记已保存！")
    
    def get_mood_analysis(self):
        # 获取情感分析
        emotion = self.agent.analyze_emotion()
        return emotion['emotional_tone']
    
    def view_diaries(self):
        print(f"\n=== 我的日记 ({len(self.diaries)} 篇) ===")
        for diary in self.diaries:
            print(f"\n日期: {diary['date']}")
            print(f"心情: {diary['mood']}")
            print("内容:")
            for entry in diary['entries']:
                print(f"  - {entry}")

# 使用
assistant = DiaryAssistant()
assistant.write_diary()
assistant.view_diaries()
```

### 场景4: 知识问答系统

```python
from chat_agent import ChatAgent
from base_knowledge import BaseKnowledge

class KnowledgeQA:
    def __init__(self):
        self.agent = ChatAgent()
        self.base_kb = BaseKnowledge()
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """加载专业知识库"""
        knowledge_data = [
            {
                "entity": "Python",
                "fact": "Python是一种高级编程语言",
                "category": "编程语言"
            },
            {
                "entity": "机器学习",
                "fact": "机器学习是人工智能的一个分支",
                "category": "技术概念"
            },
            # 添加更多知识...
        ]
        
        for item in knowledge_data:
            self.base_kb.add_base_fact(
                entity_name=item["entity"],
                fact_content=item["fact"],
                category=item["category"]
            )
    
    def ask_question(self, question: str):
        """提问并获取答案"""
        response = self.agent.chat(question)
        return response
    
    def batch_questions(self, questions: list):
        """批量提问"""
        results = []
        for q in questions:
            answer = self.ask_question(q)
            results.append({
                "question": q,
                "answer": answer
            })
        return results

# 使用
qa_system = KnowledgeQA()

questions = [
    "什么是Python？",
    "机器学习的应用有哪些？",
    "如何学习编程？"
]

results = qa_system.batch_questions(questions)

for result in results:
    print(f"\nQ: {result['question']}")
    print(f"A: {result['answer']}")
```

---

## 代码集成

### 示例11: 集成到Web应用

使用 Flask 创建 Web API：

```python
from flask import Flask, request, jsonify
from chat_agent import ChatAgent
import threading

app = Flask(__name__)

# 为每个用户创建独立的agent实例
user_agents = {}
lock = threading.Lock()

def get_agent(user_id: str):
    """获取或创建用户的agent实例"""
    with lock:
        if user_id not in user_agents:
            user_agents[user_id] = ChatAgent()
        return user_agents[user_id]

@app.route('/api/chat', methods=['POST'])
def chat():
    """聊天接口"""
    data = request.json
    user_id = data.get('user_id')
    message = data.get('message')
    
    if not user_id or not message:
        return jsonify({"error": "缺少必要参数"}), 400
    
    agent = get_agent(user_id)
    response = agent.chat(message)
    
    return jsonify({
        "response": response,
        "user_id": user_id
    })

@app.route('/api/memory/<user_id>', methods=['GET'])
def get_memory(user_id):
    """获取用户记忆"""
    agent = get_agent(user_id)
    memory = agent.get_memory()
    
    return jsonify({
        "user_id": user_id,
        "memory": memory
    })

@app.route('/api/emotion/<user_id>', methods=['GET'])
def get_emotion(user_id):
    """获取情感分析"""
    agent = get_agent(user_id)
    emotion = agent.analyze_emotion()
    
    return jsonify({
        "user_id": user_id,
        "emotion": emotion
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 示例12: 命令行工具

创建命令行交互工具：

```python
import argparse
from chat_agent import ChatAgent
from base_knowledge import BaseKnowledge
import json

def main():
    parser = argparse.ArgumentParser(description='Neo_Agent CLI')
    parser.add_argument('--chat', action='store_true', help='启动对话模式')
    parser.add_argument('--memory', action='store_true', help='查看记忆')
    parser.add_argument('--knowledge', action='store_true', help='查看知识库')
    parser.add_argument('--emotion', action='store_true', help='情感分析')
    parser.add_argument('--add-fact', nargs=3, metavar=('NAME', 'FACT', 'CATEGORY'),
                       help='添加基础知识')
    parser.add_argument('--export', type=str, help='导出数据到文件')
    
    args = parser.parse_args()
    agent = ChatAgent()
    
    if args.chat:
        # 对话模式
        print("进入对话模式（输入'退出'结束）")
        while True:
            user_input = input("你: ")
            if user_input.lower() in ['退出', 'exit']:
                break
            response = agent.chat(user_input)
            print(f"AI: {response}")
    
    elif args.memory:
        # 查看记忆
        memory = agent.get_memory()
        print(json.dumps(memory, ensure_ascii=False, indent=2))
    
    elif args.knowledge:
        # 查看知识库
        knowledge = agent.get_knowledge_items()
        print(json.dumps(knowledge, ensure_ascii=False, indent=2))
    
    elif args.emotion:
        # 情感分析
        emotion = agent.analyze_emotion()
        print(json.dumps(emotion, ensure_ascii=False, indent=2))
    
    elif args.add_fact:
        # 添加基础知识
        name, fact, category = args.add_fact
        base_kb = BaseKnowledge()
        base_kb.add_base_fact(name, fact, category)
        print(f"已添加基础知识: {name}")
    
    elif args.export:
        # 导出数据
        data = {
            "memory": agent.get_memory(),
            "knowledge": agent.get_knowledge_items(),
            "summaries": agent.get_long_term_summaries()
        }
        with open(args.export, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"数据已导出到: {args.export}")
    
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

使用方法：

```bash
# 对话模式
python cli_tool.py --chat

# 查看记忆
python cli_tool.py --memory

# 添加基础知识
python cli_tool.py --add-fact "实体名" "事实内容" "分类"

# 导出数据
python cli_tool.py --export data.json
```

---

## 更多示例

完整的示例代码可以在项目的 `examples/` 目录中找到（计划添加）。

如有其他使用场景的需求，欢迎在 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues) 中提出！
