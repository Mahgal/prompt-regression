import json
from pathlib import Path

from prompt_regression.cases import load_cases
from prompt_regression.cli import main
from prompt_regression.providers import MockProvider
from prompt_regression.runner import run_cases

EXAMPLE = Path(__file__).resolve().parents[1] / "cases.example.yaml"


def test_mock_provider_is_deterministic():
    p = MockProvider()
    prompt = "What is the capital of France?"
    assert p.generate(prompt) == p.generate(prompt) == "The capital of France is Paris."
    assert p.generate("return JSON please").startswith("{")
    assert p.generate("classify sentiment: I love it, excellent!") == "positive"


def test_mock_full_flow_example_cases_all_pass():
    cases = load_cases(EXAMPLE)
    assert len(cases) >= 6
    report = run_cases(cases, MockProvider())
    assert report.total == len(cases)
    assert report.failed == 0, [r.diff for r in report.results if not r.passed]
    assert report.pass_rate == 1.0
    assert all(r.duration_ms >= 0 for r in report.results)


def test_example_covers_all_four_assertion_types():
    cases = load_cases(EXAMPLE)
    kinds = {k for c in cases for k in c.expect}
    assert {"contains", "regex", "max_length", "json_valid"} <= kinds


def test_report_json_is_machine_readable(tmp_path):
    out = tmp_path / "report.json"
    rc = main([str(EXAMPLE), "--provider", "mock", "--report", str(out)])
    assert rc == 0
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["summary"]["total"] >= 6
    assert data["summary"]["passed"] == data["summary"]["total"]
    assert data["summary"]["pass_rate"] == 1.0
    assert data["provider"] == "mock"
    first = data["results"][0]
    assert {"id", "prompt", "output", "passed", "duration_ms", "assertions"} <= set(first)


def test_terminal_summary_counts(tmp_path, capsys):
    rc = main([str(EXAMPLE), "--provider", "mock"])
    text = capsys.readouterr().out
    assert rc == 0
    assert "passed" in text and "failed" in text and "pass rate 100%" in text


def test_failing_case_reports_diff_and_exit_1(tmp_path):
    bad = tmp_path / "fail.yaml"
    bad.write_text(
        'cases:\n  - id: will-fail\n    prompt: "Say hello"\n    expect:\n      contains: "Goodbye"\n',
        encoding="utf-8",
    )
    rc = main([str(bad), "--provider", "mock"])
    assert rc == 1
