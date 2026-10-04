"""Explicit plugin registry; no unsafe runtime filesystem code discovery."""
from __future__ import annotations

from typing import Any

from neo_agent.plugins.base import AgentPlugin, PluginContext
from neo_agent.plugins.pyvdisk import PyVDiskCapabilityPlugin
from neo_agent.plugins.schedule import ScheduleEventPlugin
from neo_agent.plugins.authoring import AgentAuthoringPlugin
from neo_agent.storage import DiskStore
from neo_agent.nps import NPSManager


class PluginRegistry:
    def __init__(self, store: DiskStore, plugins: tuple[AgentPlugin, ...] | None = None,
                 *, model: Any | None = None):
        self.store = store
        self.model = model
        self.nps = NPSManager(store)
        self._plugins: dict[str, AgentPlugin] = {}
        self._enabled = set(store.read_json("/runtime/plugins/enabled.json", default=[]))
        for plugin in plugins or (PyVDiskCapabilityPlugin(), ScheduleEventPlugin(), AgentAuthoringPlugin()):
            self.register(plugin)
            # Built-ins are enabled on first run; explicit later choices persist.
            if not self.store.sandbox.exists("/runtime/plugins/enabled.json"):
                self._enabled.add(plugin.manifest.plugin_id)

    def register(self, plugin: AgentPlugin) -> None:
        plugin_id = plugin.manifest.plugin_id
        if plugin_id in self._plugins:
            raise ValueError(f"plugin already registered: {plugin_id}")
        self._plugins[plugin_id] = plugin

    def set_enabled(self, plugin_id: str, enabled: bool) -> None:
        if plugin_id not in self._plugins:
            raise KeyError(f"unknown plugin: {plugin_id}")
        if enabled:
            self._enabled.add(plugin_id)
        else:
            self._enabled.discard(plugin_id)
        self.store.write_json("/runtime/plugins/enabled.json", sorted(self._enabled))

    def manifests(self) -> list[dict[str, Any]]:
        return [
            {**plugin.manifest.__dict__, "enabled": plugin_id in self._enabled}
            for plugin_id, plugin in sorted(self._plugins.items())
        ]

    def capabilities_for_tool(self, tool_name: str) -> tuple[str, ...]:
        """Resolve a tool to capabilities declared by its enabled manifest."""
        context = PluginContext(self.store, self.store.sandbox, self.model)
        for plugin_id, plugin in self._plugins.items():
            if plugin_id not in self._enabled:
                continue
            try:
                names = {tool.name for tool in plugin.load_tools(context)}
            except Exception:
                continue
            if tool_name in names:
                per_tool = getattr(plugin, "TOOL_CAPABILITIES", {})
                return tuple(per_tool.get(tool_name, plugin.manifest.capabilities))
        if tool_name.startswith("nps_"):
            import hashlib
            for descriptor in self.nps.list():
                generated = "nps_" + hashlib.sha256(descriptor["id"].encode()).hexdigest()[:20]
                if generated == tool_name and descriptor.get("enabled"):
                    bundle = self.nps.get(descriptor["id"])
                    return tuple(bundle.get("manifest", {}).get("capabilities", ()))
        return ()

    def tools(self) -> list[Any]:
        context = PluginContext(self.store, self.store.sandbox, self.model)
        builtin = [
            tool
            for plugin_id, plugin in self._plugins.items()
            if plugin_id in self._enabled
            for tool in plugin.load_tools(context)
        ]
        return builtin + self.nps.langchain_tools()
