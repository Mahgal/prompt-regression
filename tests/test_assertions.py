from prompt_regression.assertions import run_assertions


def _only(output, expect):
    results = run_assertions(output, expect)
    assert len(results) == 1
    return results[0]


def test_contains_pass_and_fail():
    assert _only("Hello, World!", {"contains": "Hello"}).passed
    assert not _only("Hi there", {"contains": "Hello"}).passed
    # list form: every substring must be present
    assert _only("a b c", {"contains": ["a", "c"]}).passed
    assert not _only("a b", {"contains": ["a", "c"]}).passed


def test_regex_pass_and_fail():
    assert _only("positive", {"regex": "^positive$"}).passed
    assert not _only("mostly positive", {"regex": "^positive$"}).passed
    assert not _only("anything", {"regex": "[unclosed"}).passed  # invalid regex = failure, not crash


def test_max_length_pass_and_fail():
    assert _only("short", {"max_length": 10}).passed
    assert _only("exactlyten", {"max_length": 10}).passed
    assert not _only("this is too long", {"max_length": 10}).passed


def test_json_valid_pass_and_fail():
    assert _only('{"a": 1}', {"json_valid": True}).passed
    assert _only("[1, 2, 3]", {"json_valid": True}).passed
    assert not _only("not json at all", {"json_valid": True}).passed
    assert not _only('{"a": }', {"json_valid": True}).passed


def test_helpers_not_contains_min_length_equals():
    assert _only("clean output", {"not_contains": "error"}).passed
    assert not _only("an error occurred", {"not_contains": "error"}).passed
    assert _only("long enough", {"min_length": 5}).passed
    assert not _only("tiny", {"min_length": 5}).passed
    assert _only("  exact  ", {"equals": "exact"}).passed
