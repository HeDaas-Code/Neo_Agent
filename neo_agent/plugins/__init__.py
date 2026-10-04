"""Atomic capability plugin contracts and registry."""
from .base import AgentPlugin, PluginContext, PluginManifest
from .registry import PluginRegistry
from .schedule import ScheduleEventPlugin
from .authoring import AgentAuthoringPlugin

__all__ = ["AgentPlugin", "PluginContext", "PluginManifest", "PluginRegistry", "ScheduleEventPlugin", "AgentAuthoringPlugin"]
