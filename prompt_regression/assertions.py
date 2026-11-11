"""Assertion checks for a single model output.

Four core assertion types (plus a few small helpers):

  contains      output contains a string (or every string in a list)
  regex         output matches a regular expression (re.search)
  max_length    len(output) <= N
  json_valid    output parses as JSON (optionally: is a dict / list)
  not_contains  output does NOT contain a string (helper)
  min_length    len(output) >= N (helper)
  equals        output.strip() == expected (helper)
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field

SUPPORTED = {"contains", "not_contains", "regex", "max_length", "min_length", "json_valid", "equals"}


@dataclass
class AssertionResult:
    kind: str
    expected: object
    passed: bool
    detail: str = ""

    def to_dict(self) -> dict:
        return {"kind": self.kind, "expected": self.expected, "passed": self.passed, "detail": self.detail}


def _check_contains(output: str, expected) -> AssertionResult:
    wanted = expected if isinstance(expected, list) else [expected]
    missing = [w for w in wanted if str(w) not in output]
    if missing:
        return AssertionResult("contains", expected, False, f"missing substring(s): {missing!r}")
    return AssertionResult("contains", expected, True, "all substrings present")


def _check_not_contains(output: str, expected) -> AssertionResult:
    unwanted = expected if isinstance(expected, list) else [expected]
    found = [w for w in unwanted if str(w) in output]
    if found:
        return AssertionResult("not_contains", expected, False, f"forbidden substring(s) present: {found!r}")
    return AssertionResult("not_contains", expected, True, "no forbidden substrings")


def _check_regex(output: str, expected) -> AssertionResult:
    try:
        ok = re.search(str(expected), output, flags=re.MULTILINE) is not None
    except re.error as exc:
        return AssertionResult("regex", expected, False, f"invalid regex: {exc}")
    return AssertionResult("regex", expected, ok, "regex matched" if ok else f"regex {expected!r} did not match")


def _check_max_length(output: str, expected) -> AssertionResult:
    try:
        limit = int(expected)
    except (TypeError, ValueError):
        return AssertionResult("max_length", expected, False, "max_length must be an integer")
    ok = len(output) <= limit
    return AssertionResult("max_length", expected, ok, f"length {len(output)} {'<=' if ok else '>'} {limit}")


def _check_min_length(output: str, expected) -> AssertionResult:
    try:
        limit = int(expected)
    except (TypeError, ValueError):
        return AssertionResult("min_length", expected, False, "min_length must be an integer")
    ok = len(output) >= limit
    return AssertionResult("min_length", expected, ok, f"length {len(output)} {'>=' if ok else '<'} {limit}")


def _check_json_valid(output: str, expected) -> AssertionResult:
    if expected is not True and str(expected).lower() not in ("true", "yes"):
        return AssertionResult("json_valid", expected, True, "json_valid disabled for this case")
    try:
        json.loads(output)
    except (ValueError, TypeError) as exc:
        return AssertionResult("json_valid", expected, False, f"output is not valid JSON: {exc}")
    return AssertionResult("json_valid", expected, True, "output parses as JSON")


def _check_equals(output: str, expected) -> AssertionResult:
    ok = output.strip() == str(expected).strip()
    return AssertionResult("equals", expected, ok, "exact match" if ok else f"got {output.strip()!r}, want {expected!r}")


_CHECKERS = {
    "contains": _check_contains,
    "not_contains": _check_not_contains,
    "regex": _check_regex,
    "max_length": _check_max_length,
    "min_length": _check_min_length,
    "json_valid": _check_json_valid,
    "equals": _check_equals,
}


def run_assertions(output: str, expect: dict) -> list[AssertionResult]:
    """Run every assertion in ``expect`` against ``output`` (order-stable)."""
    results = []
    for kind in sorted(expect, key=lambda k: list(SUPPORTED).index(k) if k in SUPPORTED else 99):
        checker = _CHECKERS.get(kind)
        if checker is None:  # guarded earlier by case validation, keep safe
            results.append(AssertionResult(kind, expect[kind], False, f"unknown assertion {kind!r}"))
        else:
            results.append(checker(output, expect[kind]))
    return results


def diff_hint(output: str, results: list[AssertionResult]) -> str:
    """One-line human hint for the first failing assertion — the 'diff' in the report."""
    for r in results:
        if not r.passed:
            return f"{r.kind}: expected {r.expected!r} — {r.detail}; got output: {output[:120]!r}"
    return ""
