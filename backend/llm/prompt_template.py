from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Set
import re


@dataclass(frozen=True)
class PromptTemplate:
    template: str
    bound: Dict[str, Any] = field(default_factory=dict)
    start: str = "[["
    end: str = "]]"
    # variable names: letters, digits, underscore; first char letter/_.
    var_pattern: str = r"[A-Za-z_][A-Za-z0-9_]*"

    def __post_init__(self):
        # Compile regex for [[var]] (or your chosen delimiters)
        pat = re.escape(self.start) + f"({self.var_pattern})" + re.escape(self.end)
        object.__setattr__(self, "_re", re.compile(pat))

    # --- composition ---
    def concat(self, *others: "PromptTemplate", sep: str = "\n") -> "PromptTemplate":
        tmpl = sep.join([self.template] + [o.template for o in others])
        merged = {**self.bound}
        for o in others:
            merged.update(o.bound)
        # keep current delimiters
        return PromptTemplate(
            tmpl, merged, start=self.start, end=self.end, var_pattern=self.var_pattern
        )

    def __add__(self, other: "PromptTemplate") -> "PromptTemplate":
        return self.concat(other)

    # --- binding (no formatting yet) ---
    def bind(self, **kwargs) -> "PromptTemplate":
        merged = {**self.bound, **kwargs}
        return PromptTemplate(
            self.template,
            merged,
            start=self.start,
            end=self.end,
            var_pattern=self.var_pattern,
        )

    # --- rendering ---
    def render(self, strict: bool = True, **kwargs) -> str:
        data = {**self.bound, **kwargs}

        def repl(m: re.Match) -> str:
            key = m.group(1)
            if key in data:
                return str(data[key])
            if strict:
                raise KeyError(f"Missing key: {key}")
            # safe mode: leave placeholder untouched
            return f"{self.start}{key}{self.end}"

        return self._re.sub(repl, self.template)

    # --- introspection ---
    def required_fields(self) -> Set[str]:
        return set(m.group(1) for m in self._re.finditer(self.template))

    def missing_fields(self, **extra) -> Set[str]:
        provided = set({**self.bound, **extra}.keys())
        return self.required_fields() - provided
