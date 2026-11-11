"""Command-line entry point.

Usage:
    prompt-regression cases.yaml [--provider mock|openai-compatible]
                                 [--model NAME] [--base-url URL]
                                 [--api-key-env VAR] [--report out.json]

Exit codes: 0 = all cases passed, 1 = at least one case failed,
2 = case file / configuration error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .cases import CaseError, load_cases
from .providers import ProviderError, get_provider
from .runner import run_cases


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="prompt-regression",
        description="Run YAML-defined prompt regression cases against a model endpoint "
                    "and report pass/fail with per-case diffs.",
    )
    p.add_argument("cases", help="path to the YAML case file")
    p.add_argument("--provider", default="mock", choices=["mock", "openai-compatible"],
                   help="model provider (default: mock — offline, zero cost)")
    p.add_argument("--model", default=None, help="model name (openai-compatible only)")
    p.add_argument("--base-url", default=None, help="endpoint base URL (openai-compatible only)")
    p.add_argument("--api-key-env", default=None,
                   help="env var holding the API key (default: OPENAI_API_KEY)")
    p.add_argument("--report", default=None, help="also write a machine-readable JSON report to this path")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        cases = load_cases(args.cases)
        provider = get_provider(
            args.provider,
            model=args.model or "gpt-4o-mini",
            base_url=args.base_url or "https://api.openai.com/v1",
            api_key_env=args.api_key_env or "OPENAI_API_KEY",
        )
    except (CaseError, ProviderError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    report = run_cases(cases, provider)
    print(report.format_terminal())

    if args.report:
        Path(args.report).write_text(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n",
                                     encoding="utf-8")
        print(f"JSON report written to {args.report}")
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
