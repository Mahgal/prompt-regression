"""A tiny YAML subset parser — fallback when PyYAML is not installed.

Supports exactly the subset used by prompt-regression case files:

  cases:
    - id: greeting
      prompt: "Say hello to {name}"
      variables:
        name: "World"
      expect:
        contains: "Hello"
        max_length: 100
        json_valid: true

That is: a top-level ``cases:`` list, nested mappings (variables / expect),
plain / single-quoted / double-quoted scalars, integers, booleans and
inline flow lists like ``["a", "b"]``. It is *not* a general YAML parser.
If your file uses anchors, multi-line blocks or other YAML features,
install PyYAML (``pip install pyyaml``) — it will be used automatically.
"""
from __future__ import annotations

import re


class MiniYamlError(ValueError):
    pass


def _scalar(token: str):
    token = token.strip()
    if token == "":
        return ""
    if token.startswith("[") and token.endswith("]"):
        inner = token[1:-1].strip()
        if not inner:
            return []
        return [_scalar(part) for part in _split_flow(inner)]
    if (token.startswith('"') and token.endswith('"')) or (
        token.startswith("'") and token.endswith("'")
    ):
        body = token[1:-1]
        if token.startswith('"'):
            body = body.replace('\\"', '"').replace("\\n", "\n").replace("\\\\", "\\")
        return body
    low = token.lower()
    if low in ("true", "yes"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "~"):
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        return token


def _split_flow(inner: str) -> list[str]:
    parts, depth, cur, quote = [], 0, "", None
    for ch in inner:
        if quote:
            cur += ch
            if ch == quote:
                quote = None
        elif ch in ("'", '"'):
            quote = ch
            cur += ch
        elif ch == "[":
            depth += 1
            cur += ch
        elif ch == "]":
            depth -= 1
            cur += ch
        elif ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    return parts


def loads(text: str) -> dict:
    """Parse the supported subset and return ``{"cases": [...]}``."""
    root: dict = {}
    cases: list = []
    current: dict | None = None
    section: str | None = None  # "variables" | "expect" | None

    for lineno, raw in enumerate(text.splitlines(), 1):
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()

        if indent == 0:
            if line.rstrip(":") == "cases" and line.endswith(":"):
                root["cases"] = cases
                current, section = None, None
                continue
            raise MiniYamlError(f"line {lineno}: unsupported top-level key {line!r} "
                                "(mini parser only supports 'cases:')")

        if line.startswith("- "):
            if indent != 2:
                raise MiniYamlError(f"line {lineno}: case items must be indented by 2 spaces")
            current = {}
            cases.append(current)
            section = None
            line = line[2:].strip()
            if not line:
                continue

        if current is None:
            raise MiniYamlError(f"line {lineno}: content outside a case item")

        if ":" not in line:
            raise MiniYamlError(f"line {lineno}: expected 'key: value', got {line!r}")
        key, _, value = line.partition(":")
        key, value = key.strip(), value.strip()

        # Nested mapping start, e.g. "variables:" with no value.
        if value == "" and indent >= 4:
            if indent == 4 and key in ("variables", "expect"):
                section = key
                current[section] = {}
                continue
            raise MiniYamlError(f"line {lineno}: unsupported nested key {key!r}")

        if indent >= 6 and section is not None:
            current[section][key] = _scalar(value)
        elif indent in (2, 4):
            section = None if indent == 4 else section
            if indent == 4 and key in ("variables", "expect"):
                section = key
                current[section] = {}
            else:
                current[key] = _scalar(value)
        else:
            current[key] = _scalar(value)

    if "cases" not in root:
        raise MiniYamlError("no top-level 'cases:' key found")
    return root
