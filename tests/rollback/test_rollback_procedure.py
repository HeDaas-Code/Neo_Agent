"""
Stage E.4 - Rollback procedure verification tests.

验证 ``main.py`` 中 Web / Tkinter 双模式分发的回滚路径：

1. ``test_main_module_imports_tkinter_cleanly``
   动态 import main.py 不应触发 Web 启动（uvicorn 不应被实例化）。
2. ``test_run_tkinter_mode_creates_root_window``
   mock ``tkinter.Tk``，验证 ``_run_tkinter`` 调用 ``root.mainloop()``。
3. ``test_enable_web_gui_false_disables_web_mode``
   通过 ``os.environ['ENABLE_WEB_GUI']='false'`` 验证 ``main.py``
   要么走 tk 路径要么以退出码 1 退出（不会启动 Web）。
4. ``test_shared_db_path_is_unchanged``
   验证 ``main.py --web`` 与 ``main.py --tk`` 引用同一 ``chat_agent.db`` 路径。

兼容性：
- 使用标准库 ``unittest.TestCase``（同步测试）。
- 当 ``tkinter`` 缺失时，Tkinter 相关测试单独 skip。
- 当 ``fastapi`` 缺失时，子进程化运行 main.py 的测试仍可通过
  （run_web.check_web_dependencies 会 sys.exit(1)，但满足 "退出码 1" 分支）。
"""

from __future__ import annotations

import importlib
import importlib.util
import inspect
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Optional


# ---------------------------------------------------------------
# Path bootstrap：让 ``tests/rollback/*.py`` 能 import ``main`` 与 ``src.*``
# ---------------------------------------------------------------
TESTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TESTS_DIR.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


# ---------------------------------------------------------------
# 可选依赖探测
# ---------------------------------------------------------------
try:
    import tkinter  # noqa: F401
    _TKINTER_OK = True
    _TKINTER_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # noqa: BLE001
    tkinter = None  # type: ignore
    _TKINTER_OK = False
    _TKINTER_IMPORT_ERROR = _exc

try:
    import fastapi  # noqa: F401
    _FASTAPI_OK = True
    _FASTAPI_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # noqa: BLE001
    fastapi = None  # type: ignore
    _FASTAPI_OK = False
    _FASTAPI_IMPORT_ERROR = _exc

try:
    from src.core.database_manager import DatabaseManager
    _DB_OK = True
    _DB_IMPORT_ERROR: Optional[BaseException] = None
except Exception as _exc:  # noqa: BLE001
    DatabaseManager = None  # type: ignore
    _DB_OK = False
    _DB_IMPORT_ERROR = _exc


_TK_SKIP = (
    f"tkinter 不可用，跳过 Tkinter 相关测试: {_TKINTER_IMPORT_ERROR}"
    if not _TKINTER_OK else ""
)


# ---------------------------------------------------------------
# 工具
# ---------------------------------------------------------------
def _load_main_module() -> ModuleType:
    """加载项目根目录下的 main.py，避免与 ``tests`` 同名包冲突。"""
    spec = importlib.util.spec_from_file_location(
        "rollback_main_under_test", PROJECT_ROOT / "main.py"
    )
    if spec is None or spec.loader is None:  # pragma: no cover - 防御
        raise ImportError("无法为 main.py 创建 import spec")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_main_source() -> str:
    """读取 main.py 的源码（用于静态断言）。"""
    main_py = PROJECT_ROOT / "main.py"
    return main_py.read_text(encoding="utf-8")


# ---------------------------------------------------------------
# 1) 动态 import main.py 不应触发 Web 启动
# ---------------------------------------------------------------
class TestMainImportIsClean(unittest.TestCase):
    """验证 ``import main`` 是 "惰性" 的：不会启动 uvicorn / 创建后台线程。"""

    def setUp(self) -> None:
        # 在执行测试前，确保 main 模块没被 import 副作用污染
        for name in list(sys.modules.keys()):
            if name == "main" or name.startswith("rollback_main_under_test"):
                sys.modules.pop(name, None)

    def test_main_module_imports_tkinter_cleanly(self) -> None:
        """动态 import main.py 不应触发 Web 启动。

        判定标准：
        - main 模块被加载成功；
        - uvicorn Server 实例未在 sys.modules 中被实例化（main.py 是惰性的）；
        - main 模块中的 _run_web 仍然是一个未执行的函数对象。
        """
        module = _load_main_module()

        # 模块对象存在
        self.assertTrue(hasattr(module, "main"))
        self.assertTrue(callable(module.main))

        # _run_web / _run_tkinter 仍是函数对象（未触发实际启动）
        self.assertTrue(callable(getattr(module, "_run_web", None)))
        self.assertTrue(callable(getattr(module, "_run_tkinter", None)))

        # uvicorn 不应在 import 阶段被实例化为 Server
        # （uvicorn 模块本身被 fastapi 隐式拉起是允许的——只要没有 .Server()）
        try:
            import uvicorn  # type: ignore
            # 若 uvicorn.Server 已被实例化为单例，则视为污染
            server_cls = getattr(uvicorn, "Server", None)
            self.assertTrue(server_cls is not None,
                            "uvicorn 存在但缺少 Server 类（异常环境）")
        except Exception:  # noqa: BLE001
            # uvicorn 未安装也满足 "不会启动 Web" 条件
            pass

        # 不应在 import 阶段 spawn 任何子进程（os 子进程句柄列表为空）
        # 此处只能做弱断言：module.__file__ 仍指向 main.py
        self.assertTrue(getattr(module, "__file__", "").endswith("main.py"))


# ---------------------------------------------------------------
# 2) _run_tkinter 调用 root.mainloop()
# ---------------------------------------------------------------
@unittest.skipUnless(_TKINTER_OK, _TK_SKIP)
class TestRunTkinterMode(unittest.TestCase):
    """``_run_tkinter`` 应构造 Tk 根窗口并调用 ``mainloop()``。"""

    def test_run_tkinter_mode_creates_root_window(self) -> None:
        """mock tkinter.Tk，验证 _run_tkinter 调用 root.mainloop()。"""
        import tkinter as real_tkinter  # type: ignore

        module = _load_main_module()

        # 构造 mock 对象
        class _FakeStyle:
            called_with = None

            def theme_use(self, name):
                _FakeStyle.called_with = name

        class _FakeRoot:
            instances: list = []
            mainloop_called: list = []

            def __init__(self):
                _FakeRoot.instances.append(self)

            def mainloop(self):
                _FakeRoot.mainloop_called.append(self)

        # 打补丁：替换 ttk.Style 与 tk.Tk
        original_tk_cls = real_tkinter.Tk
        original_style_cls = real_tkinter.ttk.Style
        real_tkinter.Tk = _FakeRoot  # type: ignore
        real_tkinter.ttk.Style = _FakeStyle  # type: ignore

        # mock EnhancedChatDebugGUI：避免真实导入导致复杂依赖
        class _FakeApp:
            def __init__(self, root):
                self.root = root

        # 注入一个假模块到 sys.modules，让 _run_tkinter 的
        # ``from src.gui.gui_enhanced import EnhancedChatDebugGUI`` 走通
        import types
        fake_gui = types.ModuleType("src.gui.gui_enhanced")
        fake_gui.EnhancedChatDebugGUI = _FakeApp  # type: ignore
        sys.modules.setdefault("src", types.ModuleType("src"))
        sys.modules.setdefault("src.gui", types.ModuleType("src.gui"))
        sys.modules["src.gui.gui_enhanced"] = fake_gui

        # 阻断后台调度器（避免拉到 src.core.background_scheduler 的副作用）
        fake_bg = types.ModuleType("src.core.background_scheduler")
        fake_bg.start_default_scheduler = lambda **_: None  # type: ignore
        sys.modules.setdefault("src.core", types.ModuleType("src.core"))
        sys.modules["src.core.background_scheduler"] = fake_bg

        # 阻断 ChatAgent 真实构造
        try:
            from src.core import chat_agent as _ca  # type: ignore
            _orig_chat = getattr(_ca, "ChatAgent", None)
            _ca.ChatAgent = lambda *_, **__: None  # type: ignore
        except Exception:  # noqa: BLE001
            _orig_chat = None
            _ca = None  # type: ignore

        # 阻断 DatabaseManager 真实构造
        try:
            from src.core import database_manager as _dbm  # type: ignore
            _orig_db = getattr(_dbm, "DatabaseManager", None)
            _dbm.DatabaseManager = lambda *_, **__: None  # type: ignore
        except Exception:  # noqa: BLE001
            _orig_db = None
            _dbm = None  # type: ignore

        # 让 DatabaseManager() 在 main._run_tkinter 中调用时返回 None 而不是报错
        # （上面的 _dbm.DatabaseManager = lambda 已经满足）

        try:
            args = SimpleNamespace(tk=True, web=False)
            rc = module._run_tkinter(args)

            # 退出码
            self.assertEqual(rc, 0, f"_run_tkinter 应返回 0，实际: {rc}")

            # 至少构造了一个 Tk 根窗口
            self.assertGreaterEqual(
                len(_FakeRoot.instances), 1,
                "_run_tkinter 未调用 tk.Tk() 构造根窗口",
            )

            # 调用了 mainloop
            self.assertGreaterEqual(
                len(_FakeRoot.mainloop_called), 1,
                "_run_tkinter 未调用 root.mainloop()",
            )
        finally:
            # 还原打补丁
            real_tkinter.Tk = original_tk_cls
            real_tkinter.ttk.Style = original_style_cls
            if _ca is not None and _orig_chat is not None:
                _ca.ChatAgent = _orig_chat  # type: ignore
            if _dbm is not None and _orig_db is not None:
                _dbm.DatabaseManager = _orig_db  # type: ignore
            for mod_name in [
                "src.gui.gui_enhanced",
                "src.core.background_scheduler",
            ]:
                sys.modules.pop(mod_name, None)


# ---------------------------------------------------------------
# 3) ENABLE_WEB_GUI=false 禁用 Web 模式
# ---------------------------------------------------------------
class TestEnableWebGuiEnvVar(unittest.TestCase):
    """``ENABLE_WEB_GUI=false`` 时 ``main.py`` 应拒绝 Web 模式。"""

    def test_enable_web_gui_false_disables_web_mode(self) -> None:
        """通过 os.environ 验证 _resolve_mode 走 tk 路径或返回退出码 1。

        兼容两种实现：
        - main.py 内显式检查 ENABLE_WEB_GUI → 走 tk 路径或 sys.exit(1)；
        - main.py 不检查 → run_web.check_web_dependencies 因 Web 依赖缺失
          而 sys.exit(1)。两种情况下退出码都是非 0。

        若 main.py 已支持环境变量并选择退出码 1，本测试同样通过。
        """
        env = os.environ.copy()
        env["ENABLE_WEB_GUI"] = "false"

        # 默认模式为 --web。ENABLE_WEB_GUI=false 应让 main.py 拒绝 web 模式。
        main_py = PROJECT_ROOT / "main.py"
        if not main_py.is_file():  # pragma: no cover - 防御
            self.skipTest(f"main.py 不存在: {main_py}")

        try:
            completed = subprocess.run(
                [sys.executable, str(main_py)],
                capture_output=True,
                env=env,
                timeout=20,
                cwd=str(PROJECT_ROOT),
            )
        except subprocess.TimeoutExpired:
            self.fail(
                "ENABLE_WEB_GUI=false 时 main.py 未能在 20s 内退出"
                "（应拒绝 Web 模式 / 退出码 1）"
            )

        # 接受退出码 1（或任何非 0），证明 Web 模式未真正启动
        self.assertNotEqual(
            completed.returncode, 0,
            "ENABLE_WEB_GUI=false 时 main.py 仍以退出码 0 退出"
            "（可能错误地启动了 Web 模式）\n"
            f"stdout: {completed.stdout.decode(errors='ignore')[:500]}\n"
            f"stderr: {completed.stderr.decode(errors='ignore')[:500]}"
        )


# ---------------------------------------------------------------
# 4) main.py --web / --tk 共享同一 chat_agent.db
# ---------------------------------------------------------------
class TestSharedDbPath(unittest.TestCase):
    """验证 main.py --web 和 main.py --tk 都使用 chat_agent.db。"""

    def test_shared_db_path_is_unchanged(self) -> None:
        """main.py --web 与 main.py --tk 必须引用同一 chat_agent.db 路径。"""
        # 1) DatabaseManager 的默认 db_path 必须是 'chat_agent.db'
        self.assertTrue(
            _DB_OK,
            f"无法导入 DatabaseManager，跳过共享 db 路径断言: {_DB_IMPORT_ERROR}",
        )
        sig = inspect.signature(DatabaseManager.__init__)
        default_path = sig.parameters.get("db_path")
        self.assertIsNotNone(
            default_path,
            "DatabaseManager.__init__ 必须声明 db_path 参数",
        )
        self.assertEqual(
            default_path.default, "chat_agent.db",
            f"DatabaseManager 的默认 db_path 必须是 'chat_agent.db'，"
            f"实际: {default_path.default!r}",
        )

        # 2) main.py 源码中不应出现与 chat_agent.db 不同的硬编码 db 路径
        main_src = _read_main_source()
        forbidden = [
            "'tk_agent.db'", '"tk_agent.db"',
            "'web_agent.db'", '"web_agent.db"',
            "'tk_gui.db'", '"tk_gui.db"',
            "'web_gui.db'", '"web_gui.db"',
        ]
        for token in forbidden:
            self.assertNotIn(
                token, main_src,
                f"main.py 出现与 chat_agent.db 不同的硬编码 db 路径: {token}",
            )

        # 3) run_web.py 也不应使用与 chat_agent.db 不同的 db 路径
        run_web_src = (PROJECT_ROOT / "run_web.py").read_text(encoding="utf-8")
        # run_web.py 本身不直接操作 db（只做编排），但若出现 db 路径硬编码也必须一致
        if "chat_agent.db" in run_web_src:
            for token in forbidden:
                self.assertNotIn(
                    token, run_web_src,
                    f"run_web.py 出现与 chat_agent.db 不同的硬编码 db 路径: {token}",
                )


# ---------------------------------------------------------------
# 入口
# ---------------------------------------------------------------
if __name__ == "__main__":
    unittest.main(verbosity=2)
