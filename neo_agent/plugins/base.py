"""Trusted in-process plugin contract for atomic runtime capabilities."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class PluginManifest:
    plugin_id: str
    name: str
    version: str
    description: str
    capabilities: tuple[str, ...] = ()


@dataclass(frozen=True)
class PluginContext:
    store: Any
    sandbox: Any
    model: Any | None = None


class AgentPlugin(Protocol):
    manifest: PluginManifest

    def load_tools(self, context: PluginContext) -> Sequence[Any]:
        """Return framework tools granted by this plugin."""
