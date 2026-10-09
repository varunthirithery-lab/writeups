# Training Day Recap — 2026-10-08

Assembled from Claude Code session logs, git commits, bash history, and file
timestamps. All times in IST (GMT+5:30).

## Timeline

### Early morning — Trainer releases (before participant starts)

- **10:46–14:02 IST (trainer)** — Lab 19 (ai-harness) released twice. Muraena MCP server bug fixes (TOML injection, link-local bypass, stale target, signal handler). Base, lab-14, lab-15, and lab-17 updates pushed.

### Morning — Lab 17 exploration (bash history)

- **~11:00–11:30** — Browsed lab-17 RAG grounding corpus from the terminal. Read `README.md`, `corpus/findings.json`, explored `corpus/sei/` directory tree, read SEI CERT Perl coding standard examples.

### Late morning — AI harness: first runs (lab-19)

- **12:22** — Read lab-19 `README.md`. Cloned litellm (`git clone --depth=1`).
- **12:25** — First harness run (`quick-scan` against `vulnerable_app`). Status: completed.
- **12:54–13:08** — Ran `quick-scan` against litellm. Browsed run directories from the terminal: `state.json`, `steps/map/output.json`, `steps/hunt/output.json`, `report/summary.md`, `report/findings.sarif`. Litellm scan cost $1.35.

### Midday — Agenda review and more harness runs

- **14:11** — Asked the `ai4sec-c0c0n-2026-trainer` skill for the Day 1 agenda. Asked about labs 04 and 16.
- **14:09–14:24** — Ran `quick-scan` twice more. Both runs against `vulnerable_app`. One failed (allowed_tools bug).
- **15:51–15:57** — More `quick-scan` runs. Multiple failures.

### Afternoon — DocETL: run comparison and benchmarking

- **15:59** — Ran DocETL `/init`. Created a pipeline to compare two harness runs (map outputs). Pipeline found 18 common findings and 3 unique to one run. Output: `HARNESS_COMPARISON_SUMMARY.md`.
- **16:11** — Trainer released the DocETL lab.
- **16:38–17:00** — Built a prompt optimization benchmark loop (`benchmark.py`). The loop runs the harness, asks an LLM to shorten the prompt, runs again, and compares findings with DocETL. Four iterations: baseline cost $0.105, best iteration $0.076 (28% reduction). Ran `quick-scan-bench` workflow. Updated benchmark.

### Late afternoon — Debugging the harness agent client

- **18:22** — Reported that the harness fails silently. No conversation content in logs.
- **18:29** — Ran `/code-review` on the harness.
- **18:37** — Analyzed latest run failures.
- **18:49** — Committed: "Add full conversation logging and fix three bugs in agent client" (+120/−24 lines in `ai_harness/agents/client.py`). Three bugs fixed: (1) `allowed_tools`/`disallowed_tools` passed as `None`, (2) `_count_tokens` using `hasattr` on a dict, (3) retry missing `fan_out_key`.
- **18:50** — Ran `quick-scan` against `vulnerable_app` to verify fixes. Status: completed.

### Evening — Verification runs and recap

- **19:05–19:19** — Multiple `quick-scan` and `quick-scan-bench` runs against `vulnerable_app` to verify stability. Mixed results (some completed, some failed).
- **19:19** — This recap session.

## Release commits (trainer, IST)

- **10:46** — `Release 19` (initial ai-harness lab).
- **09:23** — `Fix Muraena MCP server` (TOML injection, link-local bypass, stale target, signal handler).
- **13:27** — `Release 19` (updated ai-harness).
- **13:49** — `Release base`.
- **13:56–14:02** — `Release 14`, `Release 15`, `Release 17`.
- **15:31** — `Release docetl` (SARIF triage pipeline).
- **18:48** — `Release docetl` (update with benchmark pipeline).
- **19:20** — `Grant Codespace read access to ai-security-workbench`.

## Participant commits

- **17:00** — `update benchmark` (benchmark.py iteration).
- **18:49** — `Add full conversation logging and fix three bugs in agent client` (+120/−24).

## Topics covered across the day

1. Running a DAG workflow harness for automated bug hunting (lab-19)
2. Reading and interpreting harness run output (SARIF, JSON, Markdown)
3. Scanning a real project (litellm) with budget constraints
4. Comparing harness runs with DocETL pipelines
5. Prompt optimization: reducing cost while keeping findings
6. Debugging silent agent failures and adding conversation logging
7. The harness as an attack surface: `setting_sources=[]` and untrusted targets

## Key artifacts produced

- `labs/lab-19-ai-harness/ai-harness/runs/` — 17 harness run directories
- `labs/lab-19-ai-harness/ai-harness/ai_harness/agents/client.py` — conversation logging and three bug fixes
- `labs/lab-19-ai-harness/ATTACK_SURFACE_ANALYSIS.md` — attack surface analysis of vulnerable_app
- `labs/lab-19-ai-harness/ATTACK_SURFACE_MAP.json` — structured attack surface map
- `labs/lab-19-ai-harness/vulnerable_app/SECURITY_REPORT.md` — security audit report (3 critical findings)
- `labs/docetl-simple-example/benchmark.py` — prompt optimization benchmark loop
- `labs/docetl-simple-example/output/benchmark_results.json` — optimization results (28% cost reduction)
- `labs/docetl-simple-example/output/best_prompt.txt` — optimized bug-hunter prompt
- `labs/docetl-simple-example/output/HARNESS_COMPARISON_SUMMARY.md` — run comparison (18 common, 3 unique findings)
