"""
run_v4_mvp.py - 启动 Neo Agent v4.0 MVP 服务。

用法：
    python run_v4_mvp.py

默认监听：http://localhost:8400
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# 确保从项目根目录导入
_PROJECT_ROOT = Path(__file__).resolve().parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import uvicorn

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

if __name__ == "__main__":
    uvicorn.run(
        "src.nervous_system.app:app",
        host="0.0.0.0",
        port=8400,
        reload=False,
        log_level="info",
    )
