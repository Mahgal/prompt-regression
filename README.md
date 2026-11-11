# prompt-regression

**Changed a prompt? Run the cases before and after — and know, in seconds, whether you broke something.**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![Tests](https://img.shields.io/badge/tests-17%20passed-brightgreen.svg)](#tests)
[![Provider: mock](https://img.shields.io/badge/demo-offline%20%2F%20zero%20cost-success.svg)](#quick-start)

`prompt-regression` is a small Python CLI for regression-testing LLM prompts. You describe what your prompts *must* keep doing in a YAML file — the prompt template, its input variables, and plain assertions about the output — and the tool runs every case against a model endpoint, prints a pass/fail summary with per-case timing, shows a diff line for each failure, and can write a machine-readable JSON report for CI.

Edit the prompt, re-run the same file, compare the pass rate. That's the whole workflow.

## Features

- **YAML case files** — prompt template + `{variables}` + expected assertions, one file per feature or prompt.
- **Four core assertion types** — `contains` (substring / list of substrings), `regex`, `max_length`, `json_valid` — plus helpers `not_contains`, `min_length`, and `equals`.
- **Two providers out of the box**
  - `mock` — deterministic, offline, zero cost. Its rules are documented (see below), so demos and tests are fully predictable.
  - `openai-compatible` — calls any OpenAI-compatible `/chat/completions` endpoint (OpenAI, local servers, gateways) using only the Python standard library. The API key is read from an environment variable at runtime — it is never written into code, case files, or reports.
- **Terminal summary + JSON report** — pass/fail counts, pass rate, per-case duration in the terminal; `--report out.json` for machines and CI.
- **CI-friendly exit codes** — `0` all passed, `1` at least one case failed, `2` case-file or configuration error (with a message that names the problem: duplicate id, unknown assertion, missing variable, …).
- **Minimal dependencies** — PyYAML is used when installed. If it isn't, a bundled mini parser handles the case-file subset automatically (plain mappings, lists, quoted scalars, numbers, booleans, inline lists — no anchors or multi-line blocks), so the tool still runs in stripped-down environments.
- **One bad case doesn't kill the run** — provider/template errors are reported as that case's failure, the rest still execute.

## Quick start

No install needed to try the demo — clone, then run the bundled example against the mock provider:

```bash
git clone https://github.com/Mahgal/prompt-regression.git
cd prompt-regression
python -m prompt_regression cases.example.yaml --provider mock --report report.json
```

Or install it as a command:

```bash
pip install .
prompt-regression cases.example.yaml --provider mock
```

### Real output (mock provider, verbatim)

The exact output of the command above on the bundled `cases.example.yaml`:

```text
prompt-regression — provider: mock
----------------------------------------------------------------
[PASS] greeting-contains-hello          0.04 ms
[PASS] capital-of-france                0.01 ms
[PASS] sentiment-is-a-single-label      0.12 ms
[PASS] json-extraction-is-valid-json     0.04 ms
[PASS] summary-stays-short              0.01 ms
[PASS] spanish-translation              0.01 ms
[PASS] capital-answer-format            0.17 ms
----------------------------------------------------------------
7 passed, 0 failed, 7 total — pass rate 100% — 0.40 ms total
JSON report written to report.json
```

When a case fails, the summary gains a per-case diff line, e.g. `diff: contains: expected 'Goodbye' — missing substring(s): ['Goodbye']; got output: 'Hello! …'`, and the process exits with code `1`.

## Writing cases

```yaml
cases:
  - id: greeting-contains-hello          # unique, required
    prompt: "Say hello and greet the user named {name}"
    variables:                            # optional; fills {placeholders}
      name: "Ada"
    expect:                               # at least one assertion, required
      contains: "Hello"

  - id: json-extraction-is-valid-json
    prompt: "Extract the user profile and return JSON only."
    expect:
      json_valid: true
      contains: '"status"'

  - id: summary-stays-short
    prompt: "Summarize the quarterly report in one short line."
    expect:
      max_length: 120
      regex: "^Summary:"
```

Assertion reference:

| Assertion | Meaning |
|---|---|
| `contains: "text"` or `contains: ["a", "b"]` | Output contains the string (or every string in the list) |
| `not_contains: "text"` | Output must not contain the string |
| `regex: "^positive$"` | Output matches the regular expression (`re.search`, multiline) |
| `max_length: 120` | Output length is at most N characters |
| `min_length: 10` | Output length is at least N characters |
| `json_valid: true` | Output parses as JSON |
| `equals: "positive"` | Output, stripped, equals the expected string exactly |

See [`cases.example.yaml`](cases.example.yaml) for a complete 7-case file covering all four core assertion types.

## Using a real endpoint

```bash
export OPENAI_API_KEY="..."   # your key, in your shell only — never commit it
python -m prompt_regression cases.example.yaml \
  --provider openai-compatible \
  --base-url https://api.openai.com/v1 \
  --model gpt-4o-mini \
  --report report.json
```

`--base-url` can point at any OpenAI-compatible endpoint (including local ones); `--api-key-env` changes which environment variable holds the key (default `OPENAI_API_KEY`). Requests use `temperature: 0` for repeatability.

## The mock provider's rules

The mock is deliberately simple and predictable, checked in order (case-insensitive): a prompt mentioning **JSON** gets a fixed valid-JSON object; **sentiment** prompts get `positive` / `negative` / `neutral` based on obvious sentiment words in the prompt; **Spanish translation** prompts get a short Spanish greeting; the **capital of France** gets a sentence naming Paris; **summarise/summarize** prompts get a one-line summary; **hello/greet** prompts get a greeting containing “Hello”; anything else gets `Mock response to: <first 80 chars of the prompt>`.

## Tests

```bash
pip install pytest pyyaml   # or: pip install -e ".[dev]"
python -m pytest -q
```

17 tests cover: all four core assertion types (pass and fail paths), the helper assertions, mock-provider determinism, the full mock run over the example file, JSON report generation, terminal summary counts, failing-case diff + exit code `1`, and malformed-case errors (unknown assertion, duplicate id, missing prompt, missing file, missing template variable) plus the bundled mini YAML parser.

## Project layout

```text
prompt_regression/
  cli.py         argument parsing, exit codes
  cases.py       YAML loading + validation (clear CaseError messages)
  assertions.py  the assertion checks and diff hints
  providers.py   mock + openai-compatible providers
  runner.py      per-case timing, run report, terminal formatting
  mini_yaml.py   fallback parser for the case-file YAML subset
cases.example.yaml
tests/
```

## Need this wired into a real product?

This tool is maintained by [Khaan Superintelligence](https://khaan.si). If you want prompt regression (or LLM evaluation more broadly) set up for your own prompts, endpoints and CI — case design, provider integration, reporting — get in touch at contact@khaan.si. No client list or testimonials are published for this project; the code and the demo above are the reference.

## License

[MIT](LICENSE) — © 2026 Khaan Superintelligence.
