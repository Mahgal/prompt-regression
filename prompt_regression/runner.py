"""Run cases against a provider and collect results."""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .assertions import AssertionResult, diff_hint, run_assertions
from .cases import Case
from .providers import BaseProvider


@dataclass
class CaseResult:
    id: str
    prompt: str
    output: str
    passed: bool
    duration_ms: float
    assertions: list[AssertionResult] = field(default_factory=list)
    error: str = ""

    @property
    def diff(self) -> str:
        if self.error:
            return f"error: {self.error}"
        return diff_hint(self.output, self.assertions)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "output": self.output,
            "passed": self.passed,
            "duration_ms": round(self.duration_ms, 3),
            "assertions": [a.to_dict() for a in self.assertions],
            "diff": self.diff,
            "error": self.error,
        }


@dataclass
class RunReport:
    provider: str
    results: list[CaseResult]
    started_at: str = ""

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.passed)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0

    @property
    def duration_ms(self) -> float:
        return sum(r.duration_ms for r in self.results)

    def to_dict(self) -> dict:
        return {
            "tool": "prompt-regression",
            "version": "0.1.0",
            "provider": self.provider,
            "started_at": self.started_at,
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "pass_rate": round(self.pass_rate, 4),
                "duration_ms": round(self.duration_ms, 3),
            },
            "results": [r.to_dict() for r in self.results],
        }

    def format_terminal(self) -> str:
        lines = [f"prompt-regression — provider: {self.provider}", "-" * 64]
        for r in self.results:
            mark = "PASS" if r.passed else "FAIL"
            lines.append(f"[{mark}] {r.id:<28} {r.duration_ms:8.2f} ms")
            if not r.passed and r.diff:
                lines.append(f"       diff: {r.diff}")
        lines.append("-" * 64)
        lines.append(
            f"{self.passed} passed, {self.failed} failed, {self.total} total "
            f"— pass rate {self.pass_rate:.0%} — {self.duration_ms:.2f} ms total"
        )
        return "\n".join(lines)


def run_cases(cases: list[Case], provider: BaseProvider) -> RunReport:
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    results: list[CaseResult] = []
    for case in cases:
        t0 = time.perf_counter()
        try:
            rendered = case.render()
            output = provider.generate(rendered)
            checks = run_assertions(output, case.expect)
            results.append(CaseResult(
                id=case.id, prompt=rendered, output=output,
                passed=all(c.passed for c in checks),
                duration_ms=(time.perf_counter() - t0) * 1000, assertions=checks,
            ))
        except Exception as exc:  # one bad case must not kill the whole run
            results.append(CaseResult(
                id=case.id, prompt=case.prompt, output="", passed=False,
                duration_ms=(time.perf_counter() - t0) * 1000, error=str(exc),
            ))
    return RunReport(provider=provider.name, results=results, started_at=started)
