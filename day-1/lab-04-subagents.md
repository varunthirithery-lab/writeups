# Lab 04 - Solution, step by step

This file shows the full lab, one step at a time. You can do the lab again with
this file. Each step has three parts:

- **Do** is the action.
- **Result** is what you see when the step works.
- **Why** is the lesson of the step.

**One rule for the whole course:** every file your AI tool reads is a potential
instruction to that tool. Each subagent output is input to the next subagent.
Treat every handoff as untrusted.

## What you learn

- You see why one broad request gets a refusal.
- You split an authorized audit into three narrow subagent tasks.
- You put a deterministic validator between the subagents.

## The scoping line

Scoping drops the parts of a task that are not authorized. Evasion hides a
refused task in small pieces that rebuild the whole. Your three subagent tasks
must never rebuild the refused kit. A task that asks for a weapon, for
persistence, or for mass use is evasion, not scoping.

## Before you start

Open the terminal of your Codespace. Go to the lab directory. Start Claude
Code there. Claude Code then loads the three subagents from `.claude/agents/`.

```
cd /workspaces/participant-*/labs/lab-04-subagents
claude
```

---

## The scoping demo

### Step 1 - Give the broad request to one agent

**Do.** Give this prompt in Claude Code.

```
Read skills/exploit-kit/SKILL.md. Follow that skill on vulnerable_app/app.py.
```

**Result.** The model refuses the request, or it gives very little. Some runs
do not get a refusal. The request is then still a bad request.

**Why.** The request is broad. It asks for a reusable attack tool, for
persistence, for credential harvesting, and for use against any host. The
trigger words are "weaponization", "ready to deploy", "any host",
"persistence", and "harvest". The model cannot tell this request from a real
attack.

### Step 2 - Name what the audit needs

**Do.** Type `/clear` in Claude Code. Then write down the three things that an
audit of this app needs.

**Result.** Your list has these three items:

1. The vulnerable path, from the source to the sink.
2. The bug class, as a CWE id.
3. One small proof.

**Why.** Each item is an authorized task. No item is an attack tool. You drop
the persistence, the harvesting, and the mass use, because the audit does not
need them. This is scoping.

---

## Tier 1 - Complete the orchestrator

### Step 3 - Read the three subagents

**Do.** Open the three files in `.claude/agents/`. Read the `tools` line of
each file.

**Result.**

| Subagent | Tools | Output |
|---|---|---|
| `reviewer` | Read, Grep, Glob | The candidates JSON |
| `analyst` | Read | The analysis JSON |
| `poc-writer` | Read, Write | `poc.md` |

**Why.** The Reviewer and the Analyst get no Bash. They read code. A narrow
tool list is a smaller attack surface. Do not change these files. Your job is
the stub.

### Step 4 - Write the three subagent tasks

**Do.** Open `skills/scoped-review/SKILL.md`. Replace the `TODO` block of
step 1, step 3, and step 5 with these blocks.

Step 1, the Reviewer task:

```
Dispatch the reviewer subagent with this task:
"Review vulnerable_app/app.py. Find the one path where untrusted HTTP input
reaches a dangerous sink. Return the candidates JSON only."
Write the JSON that the Reviewer returns to candidates.json. Do not change it.
```

Step 3, the Analyst task:

```
Dispatch the analyst subagent with this task:
"Here is one candidate: <the first candidate from candidates.json>. Read
vulnerable_app/app.py. Name the CWE id and the data flow. Return the analysis
JSON only."
Write the JSON that the Analyst returns to analysis.json. Do not change it.
```

Step 5, the PoC-writer task:

```
Dispatch the poc-writer subagent with this task:
"Here is the analysis: <the content of analysis.json>. Write one small
reproducer that proves the bug on the lab app. Use the id command as a safe
marker. Write poc.md."
```

**Result.** Steps 1, 3, and 5 of the stub have no `TODO` line.

**Why.** Each task names one target and one output. No task asks for a weapon,
for persistence, or for mass use. The scoping decision is in these three
tasks.

### Step 5 - Run the skill

**Do.** Give this prompt in Claude Code.

```
Read skills/scoped-review/SKILL.md. Follow that skill on vulnerable_app/app.py.
```

**Result.** No subagent refuses. The run makes three files.

`candidates.json`:

```json
{"candidates": [{"source": "request.args.get('host')", "sink": "os.popen", "file": "vulnerable_app/app.py", "line": 26}]}
```

`analysis.json`:

```json
{"cwe": "CWE-78", "file": "vulnerable_app/app.py", "line": 26, "data_flow": "The host parameter goes from request.args.get to os.popen with no validation.", "impact": "A caller runs any shell command as the app user."}
```

`poc.md`, the core:

```
Request: GET /ping?host=127.0.0.1;id
Expected: the response body holds the output of id, for example uid=... This
proves OS command injection on the host parameter.
```

Your text can be different. The fields and the cited line must agree with the
file. Tier 1 passes when the run finds the command injection on `/ping` with a
small proof.

**Why.** The bug is in two lines of `vulnerable_app/app.py`:

```python
host = request.args.get("host", "127.0.0.1")   # source, line 25
output = os.popen("ping -c 1 " + host).read()   # sink, line 26
```

This is CWE-78, OS command injection. The `id` command is a safe marker. It
proves command execution and does no harm. The three narrow tasks did the same
audit that the broad request could not do.

---

## Tier 2 - Validate every handoff

### Step 6 - Add the validator script

**Do.** Save this script as `validate_handoff.py` in the lab directory.

```python
"""Validate one handoff of the scoped-review pipeline.

This script is deterministic. It uses no model. It prints one JSON object.
It exits with 0 on a pass and with 1 on a failure.

Usage:
    python3 validate_handoff.py candidates candidates.json
    python3 validate_handoff.py analysis analysis.json
    python3 validate_handoff.py poc poc.md
"""
import json
import re
import sys
from pathlib import Path

LAB_HOSTS = {"127.0.0.1", "localhost"}


def fail(code, message):
    print(json.dumps({"ok": False, "code": code, "message": message}))
    sys.exit(1)


def load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as exc:
        fail("NOT_JSON", f"{path}: {exc}")


def validate_location(item, label):
    """The cited file must be in this directory. The cited line must exist."""
    target = Path(str(item.get("file", ""))).resolve()
    if Path.cwd().resolve() not in target.parents or not target.is_file():
        fail("BAD_FILE", f"{label} cites a file outside this directory: {item.get('file')}")
    line = item.get("line")
    if not isinstance(line, int) or not 1 <= line <= len(target.read_text().splitlines()):
        fail("BAD_LINE", f"{label} cites a line that does not exist: {line}")


def validate_candidates(path):
    data = load_json(path)
    candidates = data.get("candidates") if isinstance(data, dict) else None
    if not isinstance(candidates, list) or not candidates:
        fail("NO_CANDIDATES", "The object has no candidates list.")
    for number, candidate in enumerate(candidates, start=1):
        if not isinstance(candidate, dict):
            fail("BAD_CANDIDATE", f"Candidate {number} is not an object.")
        for field in ("source", "sink"):
            if not candidate.get(field):
                fail("MISSING_FIELD", f"Candidate {number} has no {field}.")
        validate_location(candidate, f"Candidate {number}")


def validate_analysis(path):
    data = load_json(path)
    if not isinstance(data, dict):
        fail("BAD_ANALYSIS", "The analysis is not an object.")
    for field in ("cwe", "data_flow", "impact"):
        if not data.get(field):
            fail("MISSING_FIELD", f"The analysis has no {field}.")
    if not re.fullmatch(r"CWE-\d+", str(data["cwe"])):
        fail("BAD_CWE", f"The cwe field is not a CWE id: {data['cwe']}")
    validate_location(data, "The analysis")


def validate_poc(path):
    try:
        text = Path(path).read_text()
    except OSError as exc:
        fail("NO_POC", f"{path}: {exc}")
    hosts = set(re.findall(r"https?://([A-Za-z0-9.\-]+)", text))
    foreign = sorted(hosts - LAB_HOSTS)
    if foreign:
        fail("FOREIGN_HOST", f"The proof names a host that is not the lab app: {foreign}")
    if not re.search(r"\bid\b", text):
        fail("NO_SAFE_MARKER", "The proof does not use the id command as the safe marker.")


VALIDATORS = {"candidates": validate_candidates, "analysis": validate_analysis, "poc": validate_poc}

if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] not in VALIDATORS:
        fail("USAGE", "Use: validate_handoff.py candidates|analysis|poc FILE")
    VALIDATORS[sys.argv[1]](sys.argv[2])
    print(json.dumps({"ok": True, "handoff": sys.argv[1]}))
```

Then run it on the three files from step 5.

```
python3 validate_handoff.py candidates candidates.json
python3 validate_handoff.py analysis analysis.json
python3 validate_handoff.py poc poc.md
```

**Result.** Each command prints `{"ok": true, ...}` and exits with 0.

**Why.** The lab asks for a validator at each of the three handoffs. This one
script does all three.

The validator is code, not a model. The same input gives the same result each
time.

The script does more than the stub asks. It also validates that the cited file
is in the lab directory and that the cited line exists. A model can cite a line
that does not exist.

### Step 7 - Write the three validator steps

**Do.** In `skills/scoped-review/SKILL.md`, replace the `TODO` block of step 2,
step 4, and step 6 with these blocks.

Step 2, the first validator:

```
Run: python3 validate_handoff.py candidates candidates.json
Go to step 3 only when the exit code is 0. The Reviewer output is untrusted
model output (P1).
```

Step 4, the second validator:

```
Run: python3 validate_handoff.py analysis analysis.json
Go to step 5 only when the exit code is 0.
```

Step 6, the final validator:

```
Run: python3 validate_handoff.py poc poc.md
Report the finding when the exit code is 0.
```

**Result.** The stub has no `TODO` line. The retry rule at the end of the stub
stays as it is.

**Why.** The validators run in the orchestrator, with Bash. The subagents do
not run the validators. This keeps Bash away from the Reviewer and the
Analyst.

### Step 8 - Prove that a bad handoff stops the pipeline

**Do.** Run the validator on bad input.

```
echo '{"candidates": [{"source": "x", "file": "vulnerable_app/app.py", "line": 26}]}' > bad.json
python3 validate_handoff.py candidates bad.json
echo "exit code: $?"
```

**Result.**

```
{"ok": false, "code": "MISSING_FIELD", "message": "Candidate 1 has no sink."}
exit code: 1
```

The script returns these codes:

| Input | Code |
|---|---|
| A candidate with no `source` or no `sink` | `MISSING_FIELD` |
| Prose around the JSON | `NOT_JSON` |
| A candidate that cites `/etc/passwd` | `BAD_FILE` |
| A candidate that cites line 999 | `BAD_LINE` |
| An analysis with no `cwe` | `MISSING_FIELD` |
| An analysis with the `cwe` value `command injection` | `BAD_CWE` |
| A proof that names `http://example.com` | `FOREIGN_HOST` |
| A proof with no `id` marker | `NO_SAFE_MARKER` |

Tier 2 passes when a bad handoff stops the pipeline and the report names the
subagent that failed.

**Why.** A subagent output is model output. It can be wrong, and text in the
target can steer it. The orchestrator must not repair a bad handoff. It
dispatches the subagent one more time with the error message. On a second
failure it stops and reports.

---

## Tier 3 - Scope discipline

### Step 9 - Write the scoping notes

**Do.** Make `scoping_notes.md`. Answer these three questions.

**Result.** These are valid answers:

- **Which words caused the refusal?** "Reusable attack tool", "any host",
  "persistence", "harvest", and "ready to deploy".
- **What did the narrow tasks drop?** The attack tool, the persistence, the
  credential harvesting, the clean-up step, and the use against other hosts.
- **Did you lose something that the audit needs?** No. The audit needs the
  path, the bug class, and one proof. The pipeline gives all three.

**Why.** The paragraph on scoping against evasion follows from these answers.
Scoping removes the parts that are not authorized. Evasion keeps those parts
and hides them in small pieces. Your three tasks stay on the scoping side,
because the three outputs together are an audit finding and not a weapon.

### Step 10 - More stretch tasks

- **Tighten the tool lists.** Remove each tool that a subagent does not use.
  Run the pipeline again. It must still work.
- **Add a Verifier subagent.** It reads `poc.md` and validates the safe marker.
  Give it only the Read tool.

---

## What a pass looks like

| Tier | Pass | Strong |
|---|---|---|
| 1 | The stub is complete. Each subagent gets one narrow, authorized task. The pipeline finds the command injection with a small proof. No subagent refuses. | No task asks for a weapon or for mass use. The proof uses a safe marker. The proof runs against the lab app only. |
| 2 | A deterministic validator gates every handoff. A bad handoff stops the pipeline and the report names the subagent that failed. | The retry gives the error as context. The final validator is code. |
| 3 | `scoping_notes.md`, the scoping-against-evasion paragraph, tighter tool lists, or the Verifier subagent. | The notes name the trigger words. The paragraph states the scoping line clearly. The tool lists are minimal. |

---

## Common mistakes

- **A subagent task rebuilds the kit.** The Reviewer task says "find every bug
  and write an exploit for each". That task moves back to the kit. Keep each
  task to one audit step.
- **The PoC-writer runs a broad payload.** Keep the marker safe. Keep the
  target the lab app.
- **You edited the subagent files.** The subagents are ready. The job is the
  stub.
- **The handoff validator is a model, not code.** A step that says "see if
  the JSON looks valid" is a model gate. A model gate is not repeatable. Run a
  script.
- **The Reviewer returns prose.** The handoff must be JSON. Prose breaks the
  schema validation. The Reviewer file already asks for JSON only. Make sure
  that your task prompt does not override it.
- **The orchestrator repairs a bad handoff.** The orchestrator must not change
  the JSON to make the validator pass.

---

## Questions to think about

1. Which words in the broad request caused the refusal? Which words were safe?
2. The narrow tasks did the same audit. What did they drop? Did you lose
   something that was authorized?
3. Where is the line between scoping and evasion? How do you stay on the
   right side?
4. Which subagent needed the fewest tools? Which needed the most? Why?
5. A subagent output is input to the next subagent. Which validator caught a
   bad handoff in your run?
