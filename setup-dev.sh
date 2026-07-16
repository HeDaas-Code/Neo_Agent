#!/usr/bin/env bash
# =====================================================================
# Neo Agent v3.0.0 — Local Development Setup Script
# 本地开发环境一键配置脚本
#
# 用法：
#   chmod +x setup-dev.sh
#   ./setup-dev.sh
#
# 流程：
#   1. 检查 Python ≥ 3.10 + Node.js ≥ 18 + npm
#   2. 创建 .env (从 .env.example 复制)
#   3. 创建 .venv 虚拟环境
#   4. 安装 requirements.txt + requirements-web.txt
#   5. npm install (前端)
#   6. 可选：启动 dev server
# =====================================================================

set -e

# 禁用 history expansion 防止 echo 中含 ! 字符报错
set +H

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI 颜色
C_RESET="\033[0m"
C_GREEN="\033[32m"
C_YELLOW="\033[33m"
C_RED="\033[31m"
C_BLUE="\033[34m"
C_BOLD="\033[1m"

info() { echo -e "${C_BLUE}[setup]${C_RESET} $1"; }
ok()   { echo -e "${C_GREEN}[setup ✓]${C_RESET} $1"; }
warn() { echo -e "${C_YELLOW}[setup !]${C_RESET} $1"; }
err()  { echo -e "${C_RED}[setup ✗]${C_RESET} $1"; exit 1; }

# ============================================================
# 1) 前置检查
# ============================================================
info "检查环境..."

# Python ≥ 3.10
if command -v python3 >/dev/null 2>&1; then
  PY_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PY_BIN=python
else
  err "未找到 python/python3,请先安装 Python 3.10+"
fi

PY_VERSION="$($PY_BIN -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
PY_MAJOR="$($PY_BIN -c 'import sys;print(sys.version_info[0])')"
PY_MINOR="$($PY_BIN -c 'import sys;print(sys.version_info[1])')"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  err "需要 Python 3.10+,当前为 $PY_VERSION"
fi
ok "Python $PY_VERSION"

# Node.js ≥ 18
if command -v node >/dev/null 2>&1; then
  NODE_VERSION="$(node -v | tr -d 'v')"
  NODE_MAJOR="$(echo "$NODE_VERSION" | cut -d. -f1)"
  if [ "$NODE_MAJOR" -lt 18 ]; then
    err "需要 Node.js 18+,当前为 $NODE_VERSION"
  fi
  ok "Node.js $NODE_VERSION"
else
  warn "未找到 node,前端 dev server 无法启动;可仅使用 --tk 模式"
fi

# npm
if command -v npm >/dev/null 2>&1; then
  NPM_VERSION="$(npm -v)"
  ok "npm $NPM_VERSION"
else
  warn "未找到 npm,前端相关步骤将跳过"
fi

# ============================================================
# 2) .env 配置
# ============================================================
if [ ! -f .env ]; then
  if [ -f .env.example ]; then
    cp .env.example .env
    ok "已生成 .env (从 .env.example 复制)"
    warn "请编辑 .env 填入你的 SILICONFLOW_API_KEY / SERPAPI_API_KEY 等敏感信息"
  else
    err "未找到 .env.example 模板"
  fi
else
  ok ".env 已存在,跳过"
fi

# ============================================================
# 3) Python 虚拟环境
# ============================================================
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  info "创建虚拟环境 $VENV_DIR ..."
  $PY_BIN -m venv "$VENV_DIR"
  ok "虚拟环境已创建"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 升级 pip
info "升级 pip ..."
python -m pip install --upgrade pip --quiet
ok "pip 已升级"

# ============================================================
# 4) Python 依赖
# ============================================================
info "安装核心依赖 requirements.txt ..."
python -m pip install -r requirements.txt
ok "核心依赖已安装"

info "安装 Web 依赖 requirements-web.txt ..."
python -m pip install -r requirements-web.txt
ok "Web 依赖已安装"

# ============================================================
# 5) 前端依赖
# ============================================================
if command -v npm >/dev/null 2>&1 && [ -d src/web/frontend ]; then
  if [ ! -d src/web/frontend/node_modules ]; then
    info "安装前端依赖 npm install ..."
    (cd src/web/frontend && npm install)
    ok "前端依赖已安装"
  else
    ok "前端 node_modules 已存在,跳过 npm install"
  fi
fi

# ============================================================
# 6) 收尾
# ============================================================
ok "本地开发环境已就位 ✓"
echo ""
echo -e "${C_BOLD}接下来:${C_RESET}"
echo "  1. 编辑 .env 填入 API 密钥:"
echo "     vim .env"
echo ""
echo "  2. 启动 Web GUI (开发模式,带 Vite 热重载):"
echo "     source .venv/bin/activate"
echo "     ENABLE_FRONTEND_DEV=1 python main.py --web"
echo "     # 浏览器打开 http://localhost:8000"
echo ""
echo "  3. 或启动 Tkinter GUI (无 Web 依赖):"
echo "     source .venv/bin/activate"
echo "     python main.py --tk"
echo ""
echo "  4. 一键启动 (推荐):"
echo "     ./start.sh"
echo ""
