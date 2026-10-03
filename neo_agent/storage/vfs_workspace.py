"""Per-event and per-task workspaces confined to the PyVDisk VFS."""
from __future__ import annotations

import json
import re
from pathlib import PurePosixPath
from typing import Any

from pyvdisk import AgentSandbox


class VFSWorkspace:
    """A least-authority view rooted at one event/task directory in DataDisk.

    Callers pass only relative paths. Absolute paths, parent traversal, Windows
    separators, empty components, and attempts to operate on the workspace root
    as a file are rejected before the PyVDisk API is called.
    """

    KINDS = frozenset({"events", "tasks"})
    _ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,22}\Z")

    def __init__(self, sandbox: AgentSandbox, kind: str, workspace_id: str):
        if kind not in self.KINDS:
            raise ValueError("workspace kind must be 'events' or 'tasks'")
        if not isinstance(workspace_id, str) or not self._ID_PATTERN.fullmatch(workspace_id):
            raise ValueError("workspace_id may contain only letters, digits, '_' and '-' (max 22)")
        self._sandbox = sandbox
        self.kind = kind
        self.id = workspace_id
        self.root = f"/workspaces/{kind}/{workspace_id}"
        self._sandbox.make_directory(self.root)

    @staticmethod
    def _validate_relative_path(path: str, *, allow_root: bool = False) -> str:
        if (
            not isinstance(path, str)
            or "\x00" in path
            or "\\" in path
            or re.match(r"^[A-Za-z]:($|/)", path)
        ):
            raise ValueError("workspace path must be a relative POSIX path")
        if allow_root and path == "":
            return ""
        if not path or path.startswith("/"):
            raise ValueError("workspace path must be a non-empty relative path")
        parts = path.split("/")
        if any(part in {"", ".", ".."} for part in parts):
            raise ValueError("workspace path cannot contain empty, '.' or '..' components")
        # Keep path interpretation explicit and POSIX-only; never resolve it on
        # the host filesystem.
        return str(PurePosixPath(*parts))

    def _target(self, relative_path: str) -> str:
        return f"{self.root}/{self._validate_relative_path(relative_path)}"

    def ensure_directory(self, relative_path: str = "") -> str:
        """Create a directory beneath this workspace and return its VFS path."""
        relative = self._validate_relative_path(relative_path, allow_root=True)
        target = self.root if not relative else f"{self.root}/{relative}"
        self._sandbox.make_directory(target)
        return target

    def exists(self, relative_path: str) -> bool:
        return self._sandbox.exists(self._target(relative_path))

    def read_text(self, relative_path: str, *, encoding: str = "utf-8") -> str:
        target = self._target(relative_path)
        if not self._sandbox.exists(target):
            raise FileNotFoundError(relative_path)
        return self._sandbox.read_text(target, encoding=encoding)

    def write_text(self, relative_path: str, content: str, *, encoding: str = "utf-8") -> int:
        target = self._target(relative_path)
        return self._sandbox.write(target, content.encode(encoding))

    def read_json(self, relative_path: str, default: Any = None) -> Any:
        if not self.exists(relative_path):
            return default
        return json.loads(self.read_text(relative_path))

    def write_json(self, relative_path: str, value: Any) -> int:
        payload = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
        return self.write_text(relative_path, payload)

    def list_files(self, relative_directory: str = "") -> list[dict[str, Any]]:
        """List only entries beneath this workspace; returned paths are relative."""
        relative = self._validate_relative_path(relative_directory, allow_root=True)
        target = self.root if not relative else f"{self.root}/{relative}"
        if not self._sandbox.exists(target):
            raise FileNotFoundError(relative_directory or self.root)
        entries = self._sandbox.list(target, recursive=True)
        prefix = self.root + "/"
        return [
            {"path": entry["path"][len(prefix):], "type": entry["type"], "size": entry["size"]}
            for entry in entries
            if entry["path"].startswith(prefix) and entry["type"] == "file"
        ]

    def delete(self, relative_path: str, *, recursive: bool = False) -> bool:
        """Delete one contained file/directory; deleting the workspace root is impossible."""
        target = self._target(relative_path)
        if not self._sandbox.exists(target):
            return False
        self._sandbox.delete(target, recursive=recursive)
        return True
