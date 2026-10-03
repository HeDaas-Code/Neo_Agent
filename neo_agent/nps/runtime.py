"""Versioned NPS bundles: VScript orchestration and an isolated Python bridge."""
from __future__ import annotations

import json
import hashlib
import resource
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path
from typing import Any

from pyvdisk.vscript import Compiler, Policy, run as run_vscript

FORMAT = "neo.nps/v1"


class NPSRuntimeError(RuntimeError):
    pass


class PythonExtensionRunner:
    """Run Python extensions in bubblewrap; refuse to run without OS isolation."""

    def __init__(self, *, timeout: float = 5.0, memory_bytes: int = 128 << 20):
        self.timeout = timeout
        self.memory_bytes = memory_bytes
        self.bwrap = shutil.which("bwrap")

    def validate(self, source: str) -> None:
        compile(source, "<nps-extension>", "exec", dont_inherit=True)

    def call(self, source: str, function: str, args: dict[str, Any]) -> Any:
        self.validate(source)
        if not self.bwrap:
            raise NPSRuntimeError("Python NPS 扩展要求 bubblewrap；未检测到 bwrap，已拒绝不隔离执行")
        if not function.isidentifier() or function.startswith("_"):
            raise ValueError("extension function must be a public Python identifier")
        payload = json.dumps({"source": source, "function": function, "args": args}, ensure_ascii=False)
        if len(payload.encode("utf-8")) > 1 << 20:
            raise NPSRuntimeError("Python extension input exceeds 1 MiB")
        bootstrap = r'''import json,sys
p=json.load(sys.stdin); ns={"__name__":"nps_extension"}; exec(compile(p["source"],"<nps-extension>","exec",dont_inherit=True),ns,ns)
f=ns.get(p["function"])
if not callable(f): raise RuntimeError("declared extension entrypoint is not callable")
r=f(p["args"])
json.dump({"result":r},sys.stdout,ensure_ascii=False,default=str)
'''
        base_python = str(Path(sys.base_prefix) / "bin" / "python3")
        if not Path(base_python).exists():
            base_python = sys.executable
        def apply_resource_limits() -> None:
            resource.setrlimit(resource.RLIMIT_AS, (self.memory_bytes, self.memory_bytes))
            cpu_seconds = max(1, int(self.timeout) + 1)
            resource.setrlimit(resource.RLIMIT_CPU, (cpu_seconds, cpu_seconds))
            resource.setrlimit(resource.RLIMIT_FSIZE, (1 << 20, 1 << 20))
            resource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))

        with tempfile.TemporaryDirectory(prefix="neo-nps-") as work:
            # Start from an empty mount namespace and expose only system runtime
            # libraries; user homes, application data and credentials are never
            # mounted into the extension process.
            command = [self.bwrap, "--die-with-parent", "--new-session", "--unshare-all",
                       "--tmpfs", "/", "--dir", "/usr", "--ro-bind", "/usr", "/usr",
                       "--dir", "/bin", "--ro-bind", "/bin", "/bin",
                       "--dir", "/lib", "--ro-bind", "/lib", "/lib",
                       "--ro-bind-try", "/lib64", "/lib64",
                       "--dir", "/etc", "--ro-bind-try", "/etc/ld.so.cache", "/etc/ld.so.cache",
                       "--tmpfs", "/tmp", "--dev", "/dev", "--proc", "/proc",
                       "--bind", work, "/work", "--chdir", "/work", base_python, "-I", "-c", bootstrap]
            try:
                result = subprocess.run(command, input=payload, text=True, capture_output=True,
                                        timeout=self.timeout, check=False, env={"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8"},
                                        preexec_fn=apply_resource_limits)
            except subprocess.TimeoutExpired as exc:
                raise NPSRuntimeError("Python 扩展执行超时") from exc
        if result.returncode:
            raise NPSRuntimeError(result.stderr[-2000:] or f"Python worker exited {result.returncode}")
        try:
            return json.loads(result.stdout).get("result")
        except json.JSONDecodeError as exc:
            raise NPSRuntimeError("Python worker returned invalid JSON") from exc


class NPSManager:
    def __init__(self, store, python_runner: PythonExtensionRunner | None = None):
        self.store = store
        self.python_runner = python_runner or PythonExtensionRunner()
        self.store.ensure_directory("/runtime/nps")

    @staticmethod
    def validate_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(bundle, dict):
            raise ValueError("NPS bundle must be a JSON object")
        if bundle.get("format") != FORMAT:
            raise ValueError(f"unsupported NPS format; expected {FORMAT}")
        manifest = bundle.get("manifest")
        if not isinstance(manifest, dict):
            raise ValueError("NPS manifest is required")
        for key in ("id", "name", "version", "description", "entrypoint"):
            if not str(manifest.get(key, "")).strip():
                raise ValueError(f"manifest.{key} is required")
        if not all(part.isidentifier() for part in str(manifest["id"]).split(".")):
            raise ValueError("manifest.id must be a dotted identifier")
        vscript = str(bundle.get("vscript", ""))
        python_source = str(bundle.get("python", ""))
        if not vscript:
            raise ValueError("neo.nps/v1 requires a VScript controller; Python is an optional extension")
        if manifest["entrypoint"] != "main":
            raise ValueError("VScript controller entrypoint must be 'main'")
        capabilities = manifest.get("capabilities", [])
        if not isinstance(capabilities, list) or any(cap not in {"python.call"} for cap in capabilities):
            raise ValueError("unsupported NPS capability; allowed: python.call")
        if "python.call" in capabilities and not python_source:
            raise ValueError("python.call capability requires a Python extension")
        if python_source and "python.call" not in capabilities:
            raise ValueError("Python extension requires explicit python.call capability")
        python_entrypoint = str(manifest.get("python_entrypoint", "main"))
        if python_source and (not python_entrypoint.isidentifier() or python_entrypoint.startswith("_")):
            raise ValueError("manifest.python_entrypoint must be a public Python identifier")
        NPSManager._validate_parameter_schema(manifest.get("parameters", {"type": "object", "properties": {}}))
        Compiler().compile(vscript, f"{manifest['id']}.vds")
        if python_source:
            compile(python_source, f"{manifest['id']}.py", "exec", dont_inherit=True)
        return bundle

    @staticmethod
    def _validate_parameter_schema(schema: Any) -> dict[str, Any]:
        """Validate the intentionally bounded JSON Schema subset supported by NPS v1."""
        if not isinstance(schema, dict) or schema.get("type", "object") != "object":
            raise ValueError("NPS parameters must use a JSON Schema object")
        allowed_root = {"type", "properties", "required", "additionalProperties"}
        if set(schema) - allowed_root:
            raise ValueError(f"unsupported NPS parameter schema keys: {sorted(set(schema) - allowed_root)}")
        properties = schema.get("properties", {})
        required = schema.get("required", [])
        if not isinstance(properties, dict) or not isinstance(required, list) or any(not isinstance(k, str) for k in required):
            raise ValueError("NPS parameters.properties and required have invalid types")
        if not isinstance(schema.get("additionalProperties", False), bool):
            raise ValueError("NPS parameters.additionalProperties must be boolean")
        if not set(required).issubset(properties):
            raise ValueError("NPS required parameters must be declared in properties")
        property_keys = {"type", "enum", "default", "description", "minLength", "maxLength", "minimum", "maximum"}
        for name, spec in properties.items():
            if not isinstance(name, str) or not name.isidentifier() or not isinstance(spec, dict):
                raise ValueError(f"invalid NPS parameter definition: {name}")
            if set(spec) - property_keys:
                raise ValueError(f"unsupported NPS parameter keys for {name}: {sorted(set(spec) - property_keys)}")
            kind = spec.get("type", "string")
            if kind not in {"string", "integer", "number", "boolean"}:
                raise ValueError(f"unsupported NPS parameter type for {name}: {kind}")
            if "enum" in spec:
                choices = spec["enum"]
                if not isinstance(choices, list) or not choices:
                    raise ValueError(f"NPS parameter enum for {name} must be a non-empty array")
                for choice in choices:
                    NPSManager._validate_value_type(name, kind, choice)
            if "description" in spec and not isinstance(spec["description"], str):
                raise ValueError(f"NPS parameter description for {name} must be text")
            if kind == "string":
                for bound in ("minLength", "maxLength"):
                    if bound in spec and (not isinstance(spec[bound], int) or spec[bound] < 0):
                        raise ValueError(f"NPS {bound} for {name} must be a non-negative integer")
            else:
                for bound in ("minimum", "maximum"):
                    if bound in spec and (isinstance(spec[bound], bool) or not isinstance(spec[bound], (int, float))):
                        raise ValueError(f"NPS {bound} for {name} must be numeric")
            if "default" in spec:
                NPSManager._validate_value_type(name, kind, spec["default"])
        return schema

    @staticmethod
    def _validate_value_type(name: str, kind: str, value: Any) -> None:
        valid = {
            "string": lambda x: isinstance(x, str),
            "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
            "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
            "boolean": lambda x: isinstance(x, bool),
        }[kind](value)
        if not valid:
            raise ValueError(f"NPS parameter {name} must be {kind}")

    @classmethod
    def validate_arguments(cls, schema: dict[str, Any], args: Any) -> dict[str, Any]:
        schema = cls._validate_parameter_schema(schema)
        if not isinstance(args, dict):
            raise ValueError("NPS arguments must be a JSON object")
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        missing = required - set(args)
        if missing:
            raise ValueError(f"missing NPS arguments: {', '.join(sorted(missing))}")
        extra = set(args) - set(properties)
        if extra and not schema.get("additionalProperties", False):
            raise ValueError(f"unexpected NPS arguments: {', '.join(sorted(extra))}")
        for name, value in args.items():
            if name not in properties:
                continue
            spec = properties[name]
            kind = spec.get("type", "string")
            cls._validate_value_type(name, kind, value)
            if "enum" in spec and value not in spec["enum"]:
                raise ValueError(f"NPS argument {name} is not an allowed enum value")
            if kind == "string":
                if len(value) < spec.get("minLength", 0) or len(value) > spec.get("maxLength", float("inf")):
                    raise ValueError(f"NPS argument {name} violates string length bounds")
            elif "minimum" in spec and value < spec["minimum"] or "maximum" in spec and value > spec["maximum"]:
                raise ValueError(f"NPS argument {name} violates numeric bounds")
        return args

    @staticmethod
    def _bundle_path(plugin_id: str) -> str:
        stable_id = hashlib.sha256(plugin_id.encode("utf-8")).hexdigest()[:24]
        return f"/runtime/nps/{stable_id}/bundle.json"

    def list(self) -> list[dict[str, Any]]:
        result = []
        for entry in self.store.sandbox.list("/runtime/nps"):
            if entry["type"] == "dir":
                bundle = self.store.read_json(f"{entry['path']}/bundle.json")
                if bundle:
                    result.append({**bundle["manifest"], "enabled": bundle.get("enabled", False), "has_vscript": bool(bundle.get("vscript")), "has_python": bool(bundle.get("python"))})
        return sorted(result, key=lambda item: item["id"])

    def save(self, bundle: dict[str, Any], *, enabled: bool = False) -> dict[str, Any]:
        bundle = self.validate_bundle(bundle)
        bundle = {**bundle, "enabled": bool(enabled)}
        bundle["manifest"] = {**bundle["manifest"], "capabilities": bundle["manifest"].get("capabilities", [])}
        path = self._bundle_path(bundle["manifest"]["id"])
        self.store.write_json(path, bundle)
        self.store.append_event("nps.bundle.saved", {"id": bundle["manifest"]["id"], "enabled": enabled})
        return bundle

    def get(self, plugin_id: str) -> dict[str, Any] | None:
        return self.store.read_json(self._bundle_path(plugin_id))

    def set_enabled(self, plugin_id: str, enabled: bool) -> dict[str, Any]:
        bundle = self.get(plugin_id)
        if bundle is None:
            raise KeyError(plugin_id)
        bundle["enabled"] = bool(enabled)
        self.store.write_json(self._bundle_path(plugin_id), bundle)
        self.store.append_event("nps.bundle.state", {"id": plugin_id, "enabled": enabled})
        return bundle

    def delete(self, plugin_id: str) -> None:
        path = self._bundle_path(plugin_id).rsplit("/", 1)[0]
        if not self.store.sandbox.exists(path):
            raise KeyError(plugin_id)
        self.store.sandbox.delete(path, recursive=True)
        self.store.append_event("nps.bundle.deleted", {"id": plugin_id})

    def export_json(self, plugin_id: str) -> str:
        bundle = self.get(plugin_id)
        if not bundle:
            raise KeyError(plugin_id)
        return json.dumps({key: value for key, value in bundle.items() if key != "enabled"}, ensure_ascii=False, indent=2)

    def import_json(self, serialized: str, *, enabled: bool = False) -> dict[str, Any]:
        bundle = json.loads(serialized)
        return self.save(bundle, enabled=enabled)

    def invoke(self, plugin_id: str, args: dict[str, Any]) -> Any:
        bundle = self.get(plugin_id)
        if not bundle or not bundle.get("enabled"):
            raise NPSRuntimeError(f"NPS tool is missing or disabled: {plugin_id}")
        args = self.validate_arguments(bundle["manifest"].get("parameters", {"type": "object", "properties": {}}), args)
        return self._execute(plugin_id, bundle, args, test_mode=False)

    def test_bundle(self, bundle: dict[str, Any], args: dict[str, Any]) -> Any:
        """Validate and execute an editor bundle without installing or enabling it.

        A test run intentionally bypasses the enabled-state check because the
        operator explicitly requested a one-shot test. It never writes the
        bundle into the NPS catalog; execution and failure are still audited.
        """
        bundle = self.validate_bundle(bundle)
        args = self.validate_arguments(bundle["manifest"].get("parameters", {"type": "object", "properties": {}}), args)
        plugin_id = bundle["manifest"]["id"]
        return self._execute(plugin_id, bundle, args, test_mode=True)

    def _execute(self, plugin_id: str, bundle: dict[str, Any], args: dict[str, Any], *, test_mode: bool) -> Any:
        manifest = bundle["manifest"]
        python_source = bundle.get("python", "")
        capabilities = set(manifest.get("capabilities", []))
        def python_call(payload: Any) -> Any:
            if "python.call" not in capabilities or not python_source:
                raise NPSRuntimeError("NPS capability denied: python.call")
            extension_args = payload if isinstance(payload, dict) else json.loads(str(payload))
            if not isinstance(extension_args, dict):
                raise NPSRuntimeError("Python bridge payload must be a JSON object")
            return self.python_runner.call(python_source, manifest.get("python_entrypoint", "main"), extension_args)

        try:
            from pyvdisk.vscript.stdlib import NativeFunction
            bridge = NativeFunction("python_call", python_call)
            result = run_vscript(
                bundle["vscript"], filename=f"{plugin_id}.vds", args=args,
                bindings={"python_call": bridge}, policy=Policy(max_steps=100_000, max_wall_time=3.0,
                    max_call_depth=32, max_tasks=8, max_loop_iterations=100_000,
                    max_read_bytes=1 << 20, max_write_bytes=1 << 20, max_output_bytes=64 << 10),
                audit_callback=lambda record: self.store.append_event("nps.execution.trace", {
                    "id": plugin_id, "mode": "test" if test_mode else "invoke",
                    "audit": record.to_dict() if hasattr(record, "to_dict") else str(record),
                }),
            )
            self.store.append_event("nps.test.completed" if test_mode else "nps.execution.completed", {
                "id": plugin_id, "capabilities": sorted(capabilities),
                "mode": "test" if test_mode else "invoke",
            })
            return result
        except Exception as exc:
            self.store.append_event("nps.test.failed" if test_mode else "nps.execution.failed", {
                "id": plugin_id, "error_type": type(exc).__name__, "error": str(exc)[:1000],
                "mode": "test" if test_mode else "invoke",
            })
            raise

    def langchain_tools(self):
        from typing import Any, Literal
        from langchain_core.tools import StructuredTool
        from pydantic import Field, create_model
        tools = []
        for descriptor in self.list():
            if not descriptor["enabled"]:
                continue
            bundle = self.get(descriptor["id"])
            parameters = bundle["manifest"].get("parameters", {"type": "object", "properties": {}})
            props = parameters.get("properties", {})
            required = set(parameters.get("required", []))
            if not isinstance(props, dict) or not required.issubset(props):
                raise ValueError(f"invalid JSON Schema parameters in NPS {descriptor['id']}")
            fields = {}
            for field_name, spec in props.items():
                if not field_name.isidentifier() or not isinstance(spec, dict):
                    raise ValueError(f"invalid parameter definition: {field_name}")
                kind = spec.get("type", "string")
                field_type = {"string": str, "integer": int, "number": float, "boolean": bool}.get(kind, Any)
                if "enum" in spec:
                    choices = tuple(spec["enum"])
                    if choices:
                        field_type = Literal[choices]
                default = ... if field_name in required else spec.get("default", None)
                fields[field_name] = (field_type, Field(default, description=str(spec.get("description", ""))))
            model_name = "NPS_" + hashlib.sha256(descriptor["id"].encode()).hexdigest()[:16] + "_Args"
            schema = create_model(model_name, **fields) if fields else create_model(model_name, payload=(str, Field("{}", description="JSON object arguments")))
            def invoke(_id=descriptor["id"], **kwargs):
                if "payload" in kwargs and len(kwargs) == 1:
                    kwargs = json.loads(kwargs["payload"])
                return json.dumps(self.invoke(_id, kwargs), ensure_ascii=False, default=str)
            tool_name = "nps_" + hashlib.sha256(descriptor["id"].encode()).hexdigest()[:20]
            tools.append(StructuredTool.from_function(func=invoke, name=tool_name, description=descriptor["description"], args_schema=schema))
        return tools
