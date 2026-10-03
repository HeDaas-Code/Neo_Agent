"""Expose PyVDisk AgentSandbox capabilities to LangChain without bypasses."""
from __future__ import annotations

from typing import Any

from pyvdisk import AgentSandbox


def make_langchain_tools(sandbox: AgentSandbox) -> list[Any]:
    """Build LangChain StructuredTools from the sandbox's governed tool schema."""
    try:
        from langchain_core.tools import StructuredTool
        from pydantic import create_model
    except ImportError as exc:  # useful diagnostic when the optional stack is absent
        raise RuntimeError("Install the LangChain runtime dependencies to load agent tools") from exc

    result = []
    for spec in sandbox.tools(style="openai"):
        fields = {}
        required = set(spec["parameters"].get("required", []))
        for name, schema in spec["parameters"].get("properties", {}).items():
            annotation = str if schema.get("type") == "string" else bool if schema.get("type") == "boolean" else Any
            default = ... if name in required else schema.get("default", None)
            fields[name] = (annotation, default)
        args_schema = create_model(f"{spec['name'].title().replace('_', '')}Args", **fields)

        def invoke(_tool_name: str = spec["name"], **kwargs: Any) -> str:
            return sandbox.dispatch(_tool_name, kwargs)

        result.append(StructuredTool.from_function(
            func=invoke,
            name=spec["name"],
            description=spec["description"],
            args_schema=args_schema,
        ))
    return result
