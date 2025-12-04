from __future__ import annotations

import importlib
import importlib.util
import inspect
import types
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Union, get_args, get_origin

# --- Utilities ---------------------------------------------------------------

_PRIMITIVE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
}


def _json_type_from_annotation(ann: Any) -> Dict[str, Any]:
    """Map a Python type annotation to a (minimal) JSON Schema snippet."""
    if ann is inspect._empty:
        return {"type": "string"}

    if ann in _PRIMITIVE_MAP:
        return {"type": _PRIMITIVE_MAP[ann]}

    origin = get_origin(ann)
    args = get_args(ann)

    # Optional[T] == Union[T, NoneType]
    if origin is Union and type(None) in args:
        inner = [a for a in args if a is not type(None)][0]
        return _json_type_from_annotation(inner)

    # List[T] / list[T]
    if origin in (list, List):
        items = _json_type_from_annotation(args[0]) if args else {"type": "string"}
        return {"type": "array", "items": items}

    # Dict[K,V] / dict[K,V]
    if origin in (dict, Dict) or ann in (dict,):
        return {"type": "object"}

    if ann in (list,):
        return {"type": "array", "items": {"type": "string"}}

    return {"type": "string"}


@dataclass
class Tool:
    name: str
    description: str
    func: Callable[..., Any]
    params: Dict[str, Any] = field(default_factory=dict)
    required_params: List[str] = field(default_factory=list)

    @staticmethod
    def from_function(func: Callable[..., Any]) -> "Tool":
        """
        Generate a tool from a Python function. Uses the docstring as description
        and inspects annotations/defaults to build a JSON Schema.
        """
        sig = inspect.signature(func)
        doc = (func.__doc__ or "").strip()

        properties: Dict[str, Any] = {}
        required: List[str] = []

        for pname, param in sig.parameters.items():
            if pname == "self":
                continue

            schema = _json_type_from_annotation(param.annotation)
            schema.setdefault("description", f"Parameter {pname}")
            properties[pname] = schema

            if param.default is inspect._empty:
                required.append(pname)

        return Tool(
            name=func.__name__,
            description=doc,
            params=properties,
            required_params=required,
            func=func,
        )

    def to_schema(self) -> Dict[str, Any]:
        """Produce the OpenAI tool spec."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self.params,
                    "required": self.required_params,
                    "additionalProperties": False,
                },
            },
        }

    def execute(self, args: Dict[str, Any], tool_cls: type) -> Any:
        """Call the underlying function with the provided arguments."""
        if tool_cls is None:
            return self.func(**args)
        cls_instance = tool_cls()
        # invoke as method of tool_cls
        return self.func(cls_instance, **args)


class ToolSet:
    def __init__(self, namespace: Optional[str] = None):
        self.namespace = namespace or "default"
        self._tools: Dict[str, Tool] = {}

    def has(self, name: str) -> bool:
        return name in self._tools

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def list_tools(self) -> List[str]:
        return sorted(self._tools.keys())

    def schemas(self) -> List[Dict[str, Any]]:
        return [self._tools[name].to_schema() for name in sorted(self._tools)]

    # (Kept for your original naming; now returns List[dict], not str)
    def to_schema(self) -> List[Dict[str, Any]]:
        return self.schemas()

    def get_tool_by_name(self, name: str) -> Optional[Tool]:
        return self._tools.get(name, None)

    def __len__(self) -> int:
        return len(self._tools)


# --- Registry ----------------------------------------------------------------


class ToolSetRegistry:
    """
    Holds multiple ToolSets, each keyed by a namespace (usually the module name).
    Can load tools from a .py file path or an importable module name, filtering
    by a function-name prefix (e.g., 'tool_').
    """

    def __init__(self):
        self._toolsets: Dict[str, ToolSet] = {}
        self._toolcls: Dict[str, ToolSet] = {}

    def namespaces(self) -> List[str]:
        return sorted(self._toolsets.keys())

    def get_toolset(self, namespace: str) -> ToolSet:
        if namespace not in self._toolsets:
            return []
        if len(self._toolsets[namespace]) == 0:
            return []
        return self._toolsets[namespace]

    def get_toolsets(self, namespaces: [str]) -> [ToolSet]:
        return [self._toolsets[ns] for ns in namespaces]

    def get_tool(self, name: str, namespace: str) -> Tool:
        return self._toolsets[namespace].get(name)

    def schemas(self, namespaces: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        specs = []
        if namespaces is None:
            for ns in sorted(self._toolsets):
                specs.extend(self._toolsets[ns].schemas())
        else:
            for ns in sorted(namespaces):
                specs.extend(self._toolsets[ns].schemas())
        return specs

    def load(
        self,
        src: str | types.ModuleType | type,
        *,
        namespace: Optional[str] = None,
        ignore_prefix: str = "_",
    ) -> ToolSet:
        """
        Load tools from a module object, module name, file path, or class.
        - src: can be a module object, module name, file path, or class
        - namespace: override namespace; default is module.__name__ or class.__name__
        - ignore_prefix: only functions whose __name__.startswith(ignore_prefix) are skipped
        """
        # Handle class input
        if inspect.isclass(src):
            cls = src
            module = importlib.import_module(cls.__module__)
            ns = namespace or cls.__name__
            self._toolcls[ns] = cls

            # Create a module-like object from class methods
            mod_obj = types.ModuleType(cls.__name__)
            for attr_name in dir(cls):
                attr = getattr(cls, attr_name)
                if inspect.isfunction(attr):
                    setattr(mod_obj, attr_name, attr)

            vars_to_process = vars(mod_obj)
        else:
            # Handle module input (module object, module name, or file path)
            module = self._resolve_module(src)
            ns = namespace or module.__name__
            vars_to_process = vars(module)

        self._toolsets[ns] = ToolSet(namespace=ns)
        ts = self._toolsets[ns]

        exported = set(
            getattr(module, "__all__", [])
        )  # honor explicit exports if present

        for attr_name, obj in vars_to_process.items():
            # only plain functions defined in this module
            if not inspect.isfunction(obj):
                continue
            if getattr(obj, "__module__", None) != module.__name__:
                continue
            if attr_name.startswith(ignore_prefix):
                continue
            if exported and attr_name not in exported:
                continue

            tool = Tool.from_function(obj)

            ts.register(tool)
        return ts

    def _resolve_module(self, src: str | types.ModuleType) -> types.ModuleType:
        """Accept a module object, module name, or filesystem path to .py."""
        if isinstance(src, types.ModuleType):
            return src

        if isinstance(src, str):
            # Try module import by name first
            try:
                return importlib.import_module(src)
            except ModuleNotFoundError:
                pass

            # Then treat as file path
            path = Path(src)
            if not path.exists() or path.suffix != ".py":
                raise FileNotFoundError(
                    f"Cannot import '{src}'. Not a module name or .py file path."
                )
            mod_name = path.stem  # e.g., my_tools
            spec = importlib.util.spec_from_file_location(mod_name, path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Failed to load spec for {src}")
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)  # type: ignore[attr-defined]
            return module

        raise TypeError(f"Unsupported src type: {type(src)}")
