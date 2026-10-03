"""Core plugin exposing PyVDisk's governed capabilities to LangChain."""
from __future__ import annotations

from neo_agent.plugins.base import PluginContext, PluginManifest
from neo_agent.tools import make_langchain_tools


class PyVDiskCapabilityPlugin:
    manifest = PluginManifest(
        plugin_id="core.pyvdisk-capabilities",
        name="PyVDisk Capabilities",
        version="1.0.0",
        description="受 PyVDisk AgentSandbox 授权与审计的文件和 VScript 工具。",
        capabilities=("sandbox.fs.read", "sandbox.fs.write", "sandbox.audit"),
    )

    def load_tools(self, context: PluginContext):
        return make_langchain_tools(context.sandbox)
