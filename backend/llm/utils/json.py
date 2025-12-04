import json
from json import JSONDecodeError
import re
from typing import Any, Iterator, Tuple

_ZW = ("\u200b", "\ufeff")  # zero-width space, BOM


def _strip_code_fences(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        # remove leading ```lang and trailing ```
        s = re.sub(r"^```[a-zA-Z0-9_-]*\s*", "", s, count=1)
        if s.endswith("```"):
            s = s[: s.rfind("```")]
    return s


def _preprocess(text: str) -> str:
    for ch in _ZW:
        text = text.replace(ch, "")
    return _strip_code_fences(text)


def _balanced_from(s: str, start: int) -> Tuple[str, int, int] | None:
    """
    If s[start] is '{' or '[', return the smallest balanced JSON substring
    starting at start as (substring, start, end_exclusive). Returns None if unbalanced.
    String/escape aware.
    """
    if start >= len(s) or s[start] not in "{[":
        return None
    stack = [s[start]]
    in_str = False
    esc = False
    for j in range(start + 1, len(s)):
        c = s[j]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            continue
        else:
            if c == '"':
                in_str = True
                continue
            if c in "{[":
                stack.append(c)
            elif c in "}]":
                if not stack:
                    return None
                expected = "}" if stack[-1] == "{" else "]"
                if c != expected:
                    return None
                stack.pop()
                if not stack:
                    return s[start : j + 1], start, j + 1
    return None  # never closed


def _string_mask(s: str) -> list[bool]:
    """Marks indices that are inside double-quoted strings (escape-aware)."""
    mask = [False] * len(s)
    in_str = False
    esc = False
    for i, c in enumerate(s):
        if in_str:
            mask[i] = True
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                # The closing quote is considered inside; next char will be outside
                mask[i] = True
                in_str = False
        else:
            if c == '"':
                mask[i] = True
                in_str = True
    return mask


def iter_json_candidates(text: str) -> Iterator[Tuple[str, int, int]]:
    """
    Yields every balanced JSON object/array substring in source order as (json_str, start, end).
    We do NOT skip nested opens; we try them all so we can find the first parseable.
    """
    s = _preprocess(text)
    mask = _string_mask(s)
    for i, ch in enumerate(s):
        if ch in "{[" and not mask[i]:
            res = _balanced_from(s, i)
            if res is not None:
                yield res


def parse_first_json(text: str) -> Any:
    """
    Tries each balanced JSON candidate and returns the FIRST one that parses.
    If none parse, raises ValueError with a count of candidates tried.

    """
    tried = 0
    last_err: Exception | None = None
    for js, _, _ in iter_json_candidates(text):
        tried += 1
        try:
            return json.loads(js)
        except JSONDecodeError as e:
            last_err = e

    if tried == 0:
        raise ValueError("No balanced JSON candidates found.")
    raise ValueError(f"No PARSEABLE JSON among {tried} candidates.") from last_err
