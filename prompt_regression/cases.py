"""Loading and validation of YAML case files."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .assertions import SUPPORTED


class CaseError(ValueError):
    """Raised for any malformed case file — message always names the problem."""


@dataclass
class Case:
    id: str
    prompt: str
    expect: dict
    variables: dict = field(default_factory=dict)

    def render(self) -> str:
        try:
            return self.prompt.format(**self.variables)
        except KeyError as exc:
            raise CaseError(f"case {self.id!r}: missing variable {exc} for prompt template") from exc
        except (IndexError, ValueError) as exc:
            raise CaseError(f"case {self.id!r}: bad prompt template: {exc}") from exc


def _load_yaml(text: str):
    try:
        import yaml  # PyYAML, when available
    except ImportError:
        from . import mini_yaml
        return mini_yaml.loads(text)
    return yaml.safe_load(text)


def parse_cases(data, source: str = "<string>") -> list[Case]:
    if not isinstance(data, dict) or "cases" not in data:
        raise CaseError(f"{source}: top level must be a mapping with a 'cases:' list")
    raw_cases = data["cases"]
    if not isinstance(raw_cases, list) or not raw_cases:
        raise CaseError(f"{source}: 'cases:' must be a non-empty list")

    cases: list[Case] = []
    seen: set[str] = set()
    for i, raw in enumerate(raw_cases, 1):
        where = f"{source}: case #{i}"
        if not isinstance(raw, dict):
            raise CaseError(f"{where}: each case must be a mapping, got {type(raw).__name__}")
        cid = raw.get("id")
        if not cid or not isinstance(cid, str):
            raise CaseError(f"{where}: missing or non-string 'id'")
        if cid in seen:
            raise CaseError(f"{where}: duplicate case id {cid!r}")
        seen.add(cid)
        prompt = raw.get("prompt")
        if not prompt or not isinstance(prompt, str):
            raise CaseError(f"case {cid!r}: missing or non-string 'prompt'")
        expect = raw.get("expect")
        if not isinstance(expect, dict) or not expect:
            raise CaseError(f"case {cid!r}: 'expect' must be a non-empty mapping of assertions")
        unknown = set(expect) - SUPPORTED
        if unknown:
            raise CaseError(
                f"case {cid!r}: unknown assertion(s) {sorted(unknown)}; "
                f"supported: {sorted(SUPPORTED)}"
            )
        variables = raw.get("variables") or {}
        if not isinstance(variables, dict):
            raise CaseError(f"case {cid!r}: 'variables' must be a mapping")
        cases.append(Case(id=cid, prompt=prompt, expect=dict(expect),
                          variables={str(k): v for k, v in variables.items()}))
    return cases


def load_cases(path: str | Path) -> list[Case]:
    p = Path(path)
    if not p.is_file():
        raise CaseError(f"case file not found: {p}")
    try:
        data = _load_yaml(p.read_text(encoding="utf-8"))
    except CaseError:
        raise
    except Exception as exc:  # YAML syntax errors etc.
        raise CaseError(f"{p}: could not parse YAML: {exc}") from exc
    return parse_cases(data, source=str(p))
