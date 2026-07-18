#!/usr/bin/env bash
# Neo Agent Web GUI 一键启动脚本
# Neo Agent Web GUI One-Click Launcher
#
# Stage A.5: 启动入口
#
# 流程：
#   1. 检查 Python ≥ 3.10
#   2. 创建/激活 .venv（若不存在）
#   3. pip install -r requirements.txt -r requirements-web.txt
#   4. （可选）cd src/web/frontend && npm install
#   5. ENABLE_FRONTEND_DEV=1 python run.py web

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 加载 .env（若存在）
if [ -f .env ]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

# ============================================================
# 1) Python 版本检查（≥ 3.10）
# ============================================================
echo "[start] 检查 Python 版本..."

# 优先使用 python3；如不可用再退回 python
if command -v python3 >/dev/null 2>&1; then
  PY_BIN=python3
elif command -v python >/dev/null 2>&1; then
  PY_BIN=python
else
  echo "[start] 错误: 未找到 python 或 python3，请先安装 Python 3.10+"
  exit 1
fi

PY_VERSION="$($PY_BIN -c 'import sys;print("%d.%d"%sys.version_info[:2])')"
PY_MAJOR="$($PY_BIN -c 'import sys;print(sys.version_info[0])')"
PY_MINOR="$($PY_BIN -c 'import sys;print(sys.version_info[1])')"

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
  echo "[start] 错误: 需要 Python 3.10+，当前为 $PY_VERSION"
  exit 1
fi
echo "[start] Python 版本 OK: $PY_VERSION"

# ============================================================
# 2) 创建/激活 .venv
# ============================================================
VENV_DIR="$SCRIPT_DIR/.venv"
if [ ! -d "$VENV_DIR" ]; then
  echo "[start] 创建虚拟环境 $VENV_DIR ..."
  $PY_BIN -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"

# 升级 pip 一次（idempotent）
python -m pip install --upgrade pip --quiet

# ============================================================
# 3) 安装 Python 依赖
# ============================================================
echo "[start] 安装核心依赖 (requirements.txt) ..."
python -m pip install -r requirements.txt

echo "[start] 安装 Web 依赖 (requirements-web.txt) ..."
python -m pip install -r requirements-web.txt

# ============================================================
# 4) 前端依赖（dev 模式默认开启）
# ============================================================
ENABLE_FRONTEND_DEV="${ENABLE_FRONTEND_DEV:-1}"
if [ "$ENABLE_FRONTEND_DEV" = "1" ] && [ -d src/web/frontend ]; then
  if [ ! -d src/web/frontend/node_modules ]; then
    echo "[start] 安装前端依赖 (npm install) ..."
    (cd src/web/frontend && npm install)
  else
    echo "[start] 前端 node_modules 已存在，跳过 npm install"
  fi
fi

# ============================================================
# 5) 启动 Web GUI
# ============================================================
echo "[start] 启动 Neo Agent Web GUI..."
exec env ENABLE_FRONTEND_DEV="$ENABLE_FRONTEND_DEV" python run.py web "$@"
