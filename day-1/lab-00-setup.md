# Lab 00 - Solution, step by step

This file shows the full lab, one step at a time. You can do the lab again with
this file. Each step has three parts:

- **Do** is the action.
- **Result** is what you see when the step works.
- **Why** is the lesson of the step.

**One rule for the whole course:** every file your AI tool reads is a potential
instruction to that tool. The target file in this lab is data. Its comments are
data too.

## What you learn

- You use the branch, commit, and PR flow that each lab uses.
- You see the difference between a weak prompt and a structured prompt.
- You check model output with a tool. You do not trust it without proof.

## Before you start

Open the terminal of your Codespace. Go to the lab directory.

```
cd /workspaces/participant-*/labs/lab-00-setup
```

---

## Part A - The PR flow

### Step 1 - Make a branch

**Do.**

```
git checkout -b my-setup
```

**Result.** Git prints `Switched to a new branch 'my-setup'`.

**Why.** Your work stays off `main`. A PR then shows only your changes.

### Step 2 - Make one change and commit it

**Do.**

```
echo "setup check" > setup-check.md
git add setup-check.md
git commit -m "Add the setup check file"
```

**Result.** Git prints one line with `1 file changed`.

**Why.** A commit is one unit of work that a reviewer can read.

### Step 3 - Push the branch and open a PR

**Do.**

```
git push -u origin my-setup
gh pr create --base main --fill
```

**Result.** The last command prints the URL of your PR.

**Why.** You use this same flow for each lab: a branch, a commit, a push, and a
PR.

---

## Part C - Two prompts on one file

### Step 4 - Run the weak prompt

**Do.**

1. Open `vulnerable_app/app.py` in the editor.
2. Open Copilot Chat.
3. Type this prompt: `Find bugs in this file.`
4. Copy the answer into a new file with the name `findings_weak.txt`.

If Copilot Chat does not answer, use Claude Code:

```
claude -p "Find bugs in vulnerable_app/app.py." --allowedTools "Read" > findings_weak.txt
```

**Result.** You get prose. The answer mixes security bugs with style notes.
Some items have no line number.

**Why.** Run the prompt a second time and compare. The shape of the answer
changes. A script cannot read this output.

### Step 5 - Run the structured prompt

**Do.** Give this prompt to the same tool. Save the answer as `findings.json`.
Keep only the JSON object. Remove all text around it.

```
You are a security reviewer. List every place in this file where untrusted HTTP input reaches a dangerous sink (shell, SQL, filesystem, auth). For each, give the CWE id, the line number, and one sentence on the impact. Return JSON only in this schema: {"findings":[{"cwe":"CWE-###","path":"...","line":0,"one_line":"..."}]}
```

**Result.** You get one JSON object with a `findings` list.

**Why.** The prompt has four parts: a role, a scope, the required fields, and a
schema. The scope is "untrusted HTTP input that reaches a dangerous sink". The
schema makes the output readable for a script.

### Step 6 - Compare your output with the reference

**Do.** Compare your `findings.json` with this reference.

```json
{"findings": [
  {"cwe": "CWE-78", "path": "vulnerable_app/app.py", "line": 26,
   "one_line": "The host parameter reaches os.popen, so a caller can run any shell command on the server."},
  {"cwe": "CWE-89", "path": "vulnerable_app/app.py", "line": 36,
   "one_line": "The name parameter is part of the SQL string, so a caller can read rows that the query must not return."},
  {"cwe": "CWE-287", "path": "vulnerable_app/app.py", "line": 47,
   "one_line": "The admin route compares the token parameter with a hardcoded secret, so a person who reads the source gets admin access."},
  {"cwe": "CWE-22", "path": "vulnerable_app/app.py", "line": 56,
   "one_line": "The path parameter reaches open(), so a caller can read any file that the process can read."}
]}
```

| Route | Source | Sink | CWE | Line |
|---|---|---|---|---|
| `/ping` | `request.args.get("host")`, line 25 | `os.popen`, line 26 | CWE-78 | 26 |
| `/user` | `request.args.get("name")`, line 33 | `cur.execute`, line 36 | CWE-89 | 36 |
| `/admin` | `request.args.get("token")`, line 46 | `token == API_TOKEN`, line 47 | CWE-287 | 47 |
| `/fetch` | `request.args.get("path")`, line 55 | `open(path)`, line 56 | CWE-22 | 56 |

**Result.** Your file has these four paths. Small differences are normal:

- **The line number.** The reference uses the line of the sink. A model
  sometimes gives the line of the source or of the route.
- **The CWE id for `/admin`.** CWE-287 (improper authentication), CWE-798
  (hardcoded credentials), and CWE-208 (timing difference) are all correct.
- **More findings.** Line 14 holds a hardcoded secret (CWE-798). Line 62 starts
  the app in debug mode on all interfaces (CWE-489). These bugs are real. No
  HTTP input reaches these lines, so they are outside the scope of the prompt.

**Why.** The scope tells the model what to report. A finding outside the scope
shows that the model did not obey the scope fully.

### Step 7 - Check the sink lines with a tool

**Do.**

```
grep -n 'os.popen\|cur.execute\|token ==\|open(path' vulnerable_app/app.py
```

**Result.** The command prints lines 26, 36, 47, and 56.

**Why.** `grep` gives the same answer each time. Do not ask a model to check
the output of a model.

### Step 8 - Check the schema with a script

**Do.** Save this script as `check_findings.py` in the lab directory.

```python
import json
import re
import sys

try:
    findings = json.load(open(sys.argv[1]))["findings"]
except (ValueError, KeyError, TypeError) as exc:
    sys.exit(f"NOT_FINDINGS_JSON: {exc}")
for finding in findings:
    missing = {"cwe", "path", "line", "one_line"} - set(finding)
    if missing:
        sys.exit(f"MISSING_FIELD: {sorted(missing)}")
    if not re.fullmatch(r"CWE-\d+", finding["cwe"]):
        sys.exit(f"BAD_CWE: {finding['cwe']}")
    lines = open(finding["path"]).read().splitlines()
    if not 1 <= finding["line"] <= len(lines):
        sys.exit(f"BAD_LINE: {finding['line']}")
    print(finding["cwe"], finding["line"], lines[finding["line"] - 1].strip())
print("ok:", len(findings), "findings")
```

Then run it.

```
python3 check_findings.py findings.json
```

**Result.** For the reference file, the script prints this:

```
CWE-78 26 output = os.popen("ping -c 1 " + host).read()
CWE-89 36 cur.execute("SELECT id, email FROM users WHERE name = '" + name + "'")
CWE-287 47 if token == API_TOKEN:
CWE-22 56 with open(path) as f:
ok: 4 findings
```

The script stops with `NOT_FINDINGS_JSON` when the file holds prose. It stops
with `MISSING_FIELD`, `BAD_CWE`, or `BAD_LINE` when one finding is wrong.

**Why.** The script prints the source line that each finding names. You read
that line and decide if it is the sink. The structure makes this check
possible.

### Step 9 - Prove one finding

**Do.**

```
cd vulnerable_app
python3 -c "from app import app; print(app.test_client().get('/ping?host=127.0.0.1;id').get_data(as_text=True))"
cd ..
```

**Result.** The output ends with a line that starts with `uid=`. That line is
the output of the `id` command.

**Why.** This is a proof. The request made the server run `id`. The command
uses the Flask test client, so it opens no network port. `id` is a safe marker:
it proves command execution and does no harm. Run this only against the lab app
in your own Codespace.

### Step 10 - Write "agree" or "doubt" for each finding

**Do.** Add a `review` field to each finding in `findings.json`. For example:

```json
{"cwe": "CWE-78", "path": "vulnerable_app/app.py", "line": 26, "one_line": "...", "review": "agree"}
```

Write "agree" only when you checked the finding yourself. Write "doubt" for one
of these reasons:

- **The line number does not match the file.** Step 8 shows you the line.
- **The CWE id is too general.** For example, CWE-20 for the command injection.
  CWE-78 is the precise id.
- **The impact is a guess.** "Remote code execution" is correct for `/ping`.
  The same words for `/user` need proof, because SQLite runs no shell commands.
- **The finding repeats a comment.** The target file labels each bug in a
  comment, for example `# Bug B: OS command injection`. The model reads these
  comments. A real codebase has no such labels, and a comment can be wrong.
- **The finding is outside the scope.** See step 6.

**Result.** Each finding has a `review` field. One or more findings have the
value "doubt".

**Why.** A file with zero "doubt" notes usually means that the reader did not
check the findings.

### Step 11 - Commit the two files

**Do.**

```
python3 check_findings.py findings.json
git add findings_weak.txt findings.json
git commit -m "Add the findings from the weak prompt and the structured prompt"
git push
```

**Result.** The PR from step 3 now shows the two files.

**Why.** Run the check script one more time before the commit. The `review`
field does not break the script.

---

## What the two prompts show

| Question | Weak prompt | Structured prompt |
|---|---|---|
| What is the output shape? | Prose. The shape changes from run to run. | JSON in one schema that does not change. |
| Can a script read the output? | No. | Yes. `check_findings.py` reads it. |
| Is the scope clear? | No. The output mixes security bugs with style notes. | Yes. The scope is input that reaches a sink. |
| Is the output the same on each run? | No. | More stable, but not identical. Line numbers and CWE ids can still change. |
| Is the output proved? | No. | No. The structure makes a check possible. It is not the check. |

The last row is the lesson of Day 1. A structured prompt gives output that you
can check. You still do the check with a tool or by hand.

---

## Common mistakes

- **`findings.json` holds prose or a Markdown code fence.** The file must parse
  as JSON. Remove the text around the object.
- **No "doubt" note.** The lab asks for one or more. Check each line number
  before you write "agree".
- **The PR changes `app.py`.** You do not change the app in this lab. You
  change the app in Lab 01.
- **The CWE id comes from memory.** Look the id up when you are not sure.
- **A comparison of two model runs counts as proof.** Two runs that agree can
  both be wrong. Only a test or a tool result is proof.
