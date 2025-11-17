# 部署指南

本文档详细说明如何在不同环境中部署 Neo_Agent 智能对话系统。

## 目录

- [系统要求](#系统要求)
- [本地开发部署](#本地开发部署)
- [生产环境部署](#生产环境部署)
- [Docker部署](#docker部署)
- [云平台部署](#云平台部署)
- [常见问题](#常见问题)

---

## 系统要求

### 最低要求

- **操作系统**: Windows 10/11, macOS 10.14+, Linux (Ubuntu 18.04+)
- **Python**: 3.8 或更高版本（推荐 3.12+）
- **内存**: 4GB RAM
- **磁盘空间**: 500MB（包括依赖和数据）
- **网络**: 稳定的互联网连接（访问 SiliconFlow API）

### 推荐配置

- **操作系统**: Windows 11, macOS 13+, Ubuntu 22.04+
- **Python**: 3.12+
- **内存**: 8GB RAM 或更多
- **磁盘空间**: 2GB
- **显示器**: 1920x1080 或更高分辨率

---

## 本地开发部署

适用于开发和测试环境。

### 1. 安装 Python

#### Windows

1. 访问 [Python官网](https://www.python.org/downloads/)
2. 下载 Python 3.12 安装程序
3. 运行安装程序，**勾选 "Add Python to PATH"**
4. 验证安装：
   ```bash
   python --version
   pip --version
   ```

#### macOS

使用 Homebrew 安装：
```bash
brew install python@3.12
python3 --version
pip3 --version
```

#### Linux (Ubuntu/Debian)

```bash
sudo apt update
sudo apt install python3.12 python3.12-venv python3-pip
python3 --version
pip3 --version
```

### 2. 克隆项目

```bash
# 使用 HTTPS
git clone https://github.com/HeDaas-Code/Neo_Agent.git

# 或使用 SSH
git clone git@github.com:HeDaas-Code/Neo_Agent.git

# 进入项目目录
cd Neo_Agent
```

### 3. 创建虚拟环境（推荐）

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```

#### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

如果安装速度慢，可以使用国内镜像：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 5. 配置环境变量

```bash
# 复制示例配置文件
cp example.env .env

# 编辑 .env 文件
# Windows: notepad .env
# macOS/Linux: nano .env 或 vim .env
```

必须配置的项：

```env
# 必填：从 SiliconFlow 获取 API 密钥
SILICONFLOW_API_KEY=your_actual_api_key_here

# 可选：选择模型
MODEL_NAME=deepseek-ai/DeepSeek-V3

# 可选：调试模式（开发环境建议开启）
DEBUG_MODE=True
```

### 6. 获取 API 密钥

1. 访问 [SiliconFlow官网](https://siliconflow.cn/)
2. 注册账号并登录
3. 进入 API 管理页面
4. 创建新的 API 密钥
5. 复制密钥并填入 `.env` 文件

### 7. 运行程序

```bash
# 启动GUI版本（推荐）
python gui_enhanced.py

# 或命令行版本
python chat_agent.py
```

### 8. 验证安装

程序启动后，尝试发送消息：
```
用户: 你好
AI: 你好呀！我是小可...
```

如果能正常对话，说明部署成功！

---

## 生产环境部署

适用于实际使用和团队部署。

### 1. 环境准备

```bash
# 创建专用用户（Linux）
sudo useradd -m -s /bin/bash neoagent
sudo su - neoagent

# 创建应用目录
mkdir -p ~/neo_agent
cd ~/neo_agent
```

### 2. 安装项目

```bash
# 克隆项目
git clone https://github.com/HeDaas-Code/Neo_Agent.git
cd Neo_Agent

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3. 生产环境配置

创建生产环境配置文件 `.env.production`：

```env
# API配置
SILICONFLOW_API_KEY=production_api_key
SILICONFLOW_API_URL=https://api.siliconflow.cn/v1/chat/completions
MODEL_NAME=deepseek-ai/DeepSeek-V3
TEMPERATURE=0.8
MAX_TOKENS=2000

# 角色设定
CHARACTER_NAME=小可
CHARACTER_GENDER=女
CHARACTER_ROLE=学生
CHARACTER_AGE=18
CHARACTER_PERSONALITY=活泼开朗
CHARACTER_HOBBY=文科，尤其对历史充满热情
CHARACTER_BACKGROUND=我是一名高中生，叫小可...

# 记忆设置
MAX_SHORT_TERM_ROUNDS=20
MAX_MEMORY_MESSAGES=50

# 生产环境：关闭Debug模式
DEBUG_MODE=False
DEBUG_LOG_FILE=debug.log

# 数据文件路径
MEMORY_FILE=memory_data.json
LONG_MEMORY_FILE=longmemory_data.json
```

### 4. 文件权限设置

```bash
# 设置配置文件权限（保护API密钥）
chmod 600 .env.production

# 设置应用目录权限
chmod 755 ~/neo_agent/Neo_Agent
```

### 5. 数据备份策略

创建备份脚本 `backup.sh`：

```bash
#!/bin/bash
# Neo_Agent 数据备份脚本

BACKUP_DIR=~/neo_agent_backups
DATE=$(date +%Y%m%d_%H%M%S)
APP_DIR=~/neo_agent/Neo_Agent

# 创建备份目录
mkdir -p $BACKUP_DIR

# 备份数据库
cp $APP_DIR/chat_agent.db $BACKUP_DIR/chat_agent_$DATE.db

# 备份JSON文件（如果存在）
if [ -f "$APP_DIR/memory_data.json" ]; then
    cp $APP_DIR/memory_data.json $BACKUP_DIR/memory_data_$DATE.json
fi

if [ -f "$APP_DIR/longmemory_data.json" ]; then
    cp $APP_DIR/longmemory_data.json $BACKUP_DIR/longmemory_data_$DATE.json
fi

# 删除7天前的备份
find $BACKUP_DIR -name "*.db" -mtime +7 -delete
find $BACKUP_DIR -name "*.json" -mtime +7 -delete

echo "备份完成: $DATE"
```

设置定时备份（Linux）：

```bash
# 添加执行权限
chmod +x backup.sh

# 添加到crontab（每天凌晨2点备份）
crontab -e
# 添加以下行：
0 2 * * * /home/neoagent/neo_agent/Neo_Agent/backup.sh >> /home/neoagent/backup.log 2>&1
```

### 6. 监控和日志

创建日志轮转配置 `/etc/logrotate.d/neoagent`：

```
/home/neoagent/neo_agent/Neo_Agent/debug.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 neoagent neoagent
}
```

### 7. 启动脚本

创建启动脚本 `start.sh`：

```bash
#!/bin/bash
# Neo_Agent 启动脚本

APP_DIR=~/neo_agent/Neo_Agent
cd $APP_DIR

# 激活虚拟环境
source venv/bin/activate

# 使用生产环境配置
cp .env.production .env

# 启动应用
python gui_enhanced.py

# 或者使用 nohup 后台运行（无GUI环境）
# nohup python chat_agent.py > app.log 2>&1 &
```

---

## Docker部署

使用Docker容器化部署（适用于无GUI环境）。

### 1. 创建 Dockerfile

```dockerfile
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY . /app

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建数据目录
RUN mkdir -p /app/data

# 环境变量
ENV PYTHONUNBUFFERED=1
ENV DEBUG_MODE=False

# 暴露端口（如果需要Web界面）
# EXPOSE 8000

# 启动命令
CMD ["python", "chat_agent.py"]
```

### 2. 创建 docker-compose.yml

```yaml
version: '3.8'

services:
  neoagent:
    build: .
    container_name: neo_agent
    restart: unless-stopped
    environment:
      - SILICONFLOW_API_KEY=${SILICONFLOW_API_KEY}
      - MODEL_NAME=deepseek-ai/DeepSeek-V3
      - DEBUG_MODE=False
    volumes:
      - ./data:/app/data
      - ./chat_agent.db:/app/chat_agent.db
    # ports:
    #   - "8000:8000"  # 如果需要Web界面
```

### 3. 构建和运行

```bash
# 构建镜像
docker-compose build

# 启动容器
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止容器
docker-compose down
```

---

## 云平台部署

### AWS部署

1. **创建EC2实例**
   - 选择 Ubuntu 22.04 LTS
   - 实例类型：t3.medium 或更高
   - 配置安全组（开放必要端口）

2. **连接到实例**
   ```bash
   ssh -i your-key.pem ubuntu@your-ec2-ip
   ```

3. **按照生产环境部署步骤安装**

4. **配置持久化存储**
   - 使用 EBS 卷存储数据
   - 配置自动快照备份

### Azure部署

1. **创建虚拟机**
   - Ubuntu 22.04 LTS
   - 标准 B2s 或更高配置

2. **安装和配置**
   - 参考生产环境部署步骤

3. **使用Azure Blob存储备份**
   ```bash
   # 安装Azure CLI
   curl -sL https://aka.ms/InstallAzureCLIDeb | sudo bash
   
   # 配置备份到Blob
   az storage blob upload \
       --account-name youraccount \
       --container-name backups \
       --name chat_agent_$(date +%Y%m%d).db \
       --file chat_agent.db
   ```

### 阿里云部署

1. **创建ECS实例**
   - Ubuntu 22.04
   - ecs.t6-c1m2.large 或更高

2. **配置安全组**
   - 允许SSH访问（22端口）

3. **安装部署**
   - 参考生产环境部署

---

## 常见问题

### Q: 程序无法启动？

**A**: 检查以下几点：
1. Python版本是否正确（3.8+）
2. 是否安装了所有依赖
3. `.env` 文件是否配置正确
4. API密钥是否有效
5. 查看错误日志：`debug.log`

### Q: GUI无法显示？

**A**: 
- **Linux**: 需要安装图形界面支持
  ```bash
  sudo apt install python3-tk
  ```
- **macOS**: 确保安装了完整的Python（带Tkinter）
- **远程服务器**: 使用命令行版本 `python chat_agent.py`

### Q: API调用失败？

**A**: 
1. 检查网络连接
2. 验证API密钥是否正确
3. 确认API额度是否充足
4. 查看 `debug.log` 获取详细错误

### Q: 如何迁移数据？

**A**: 
1. 备份以下文件：
   - `chat_agent.db`
   - `.env`（注意保护API密钥）
2. 在新环境中：
   - 安装应用
   - 复制备份文件到应用目录
   - 启动应用

### Q: 如何升级版本？

**A**: 
```bash
# 备份数据
./backup.sh

# 拉取最新代码
git pull origin main

# 更新依赖
pip install -r requirements.txt --upgrade

# 重启应用
./start.sh
```

### Q: 性能优化建议？

**A**: 
1. 关闭DEBUG模式（生产环境）
2. 使用SSD存储数据库文件
3. 定期清理过期数据和日志
4. 选择合适的模型（更快的模型）
5. 配置足够的系统资源

---

## 安全建议

1. **保护API密钥**
   - 不要将 `.env` 文件提交到Git
   - 使用环境变量或密钥管理服务
   - 定期轮换API密钥

2. **数据安全**
   - 定期备份重要数据
   - 加密敏感对话记录
   - 设置合适的文件权限

3. **网络安全**
   - 使用HTTPS连接API
   - 配置防火墙规则
   - 限制SSH访问IP

4. **更新维护**
   - 定期更新依赖包
   - 关注安全公告
   - 及时打补丁

---

## 支持

如遇到部署问题：

1. 查看 [故障排查文档](TROUBLESHOOTING.md)
2. 搜索 [Issues](https://github.com/HeDaas-Code/Neo_Agent/issues)
3. 提交新的Issue并提供：
   - 操作系统和Python版本
   - 完整错误信息
   - 相关日志内容
   - 配置文件（隐藏敏感信息）

---

祝部署顺利！🎉
