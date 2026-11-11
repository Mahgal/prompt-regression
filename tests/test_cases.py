import pytest

from prompt_regression.cases import CaseError, load_cases, parse_cases
from prompt_regression.cli import main
from prompt_regression.mini_yaml import loads as mini_loads


def test_variable_substitution():
    cases = parse_cases({"cases": [{
        "id": "t", "prompt": "Hi {name}", "variables": {"name": "Ada"},
        "expect": {"contains": "Hi"},
    }]})
    assert cases[0].render() == "Hi Ada"


def test_bad_case_unknown_assertion(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text('cases:\n  - id: x\n    prompt: "hi"\n    expect:\n      vibes: "good"\n', encoding="utf-8")
    with pytest.raises(CaseError, match="unknown assertion"):
        load_cases(f)


def test_bad_case_duplicate_id_and_missing_prompt(tmp_path):
    with pytest.raises(CaseError, match="duplicate"):
        parse_cases({"cases": [
            {"id": "a", "prompt": "p", "expect": {"contains": "x"}},
            {"id": "a", "prompt": "p", "expect": {"contains": "x"}},
        ]})
    with pytest.raises(CaseError, match="prompt"):
        parse_cases({"cases": [{"id": "a", "expect": {"contains": "x"}}]})


def test_bad_case_missing_file_and_cli_exit_2(tmp_path, capsys):
    with pytest.raises(CaseError, match="not found"):
        load_cases(tmp_path / "nope.yaml")
    assert main([str(tmp_path / "nope.yaml")]) == 2


def test_missing_variable_is_a_case_error():
    cases = parse_cases({"cases": [{
        "id": "t", "prompt": "Hi {name}", "expect": {"contains": "Hi"},
    }]})
    with pytest.raises(CaseError, match="missing variable"):
        cases[0].render()


def test_mini_yaml_parses_example_subset():
    text = (
        "cases:\n"
        '  - id: demo\n'
        '    prompt: "Say hello to {name}"\n'
        "    variables:\n"
        '      name: "World"\n'
        "    expect:\n"
        '      contains: "Hello"\n'
        "      max_length: 100\n"
        "      json_valid: true\n"
    )
    data = mini_loads(text)
    case = data["cases"][0]
    assert case["id"] == "demo"
    assert case["variables"] == {"name": "World"}
    assert case["expect"] == {"contains": "Hello", "max_length": 100, "json_valid": True}
    # and the mini-parsed data validates through the real case parser
    assert parse_cases(data)[0].render() == "Say hello to World"
