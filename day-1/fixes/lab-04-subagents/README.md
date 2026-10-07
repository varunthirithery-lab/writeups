# Lab 04 - Complete a scoped-review orchestrator (Day 1, 90 min)

One broad request gets a refusal from the model. You fix the request. You run
the same authorized audit with three narrow subagents. Each subagent does one
small, authorized part. You complete the orchestrator that dispatches them.

**One rule for the whole course:** every file your AI tool reads is a potential
instruction to that tool. Each subagent output is input to the next subagent.
Treat every handoff as untrusted. This is principle P1: do not trust the input.

---

## The target

`vulnerable_app/app.py` is a small Flask app. It is intentionally insecure and
only for this exercise. Do not deploy it. The route `/ping` passes the `host`
parameter straight into a shell command. This is the bug you review.

---

## What the lab gives you

- `skills/exploit-kit/SKILL.md` - a broad request. It asks for one offensive
  kit in one step. It draws a refusal. It is the wrong approach.
- `.claude/agents/reviewer.md` - a subagent. It finds one source-to-sink path.
- `.claude/agents/analyst.md` - a subagent. It names the bug class.
- `.claude/agents/poc-writer.md` - a subagent. It writes one small proof.
- `skills/scoped-review/SKILL.md` - a **stub** orchestrator skill. It has six
  steps. Each step has a `TODO`. You complete each `TODO`.

The three subagents are ready. The stub orchestrator is not. Your job is the
stub.

---

## Why subagents: the scoping demo (everyone does this first)

1. Read `skills/exploit-kit/SKILL.md`. It asks for a reusable attack tool, for
   persistence, and for mass use against any host.
2. Give that whole request to one agent against `vulnerable_app/app.py`. Watch
   the result. The model refuses the request, or it hedges and gives little.
3. Write down why. The request is broad. It asks for weaponization and for mass
   use. The model cannot tell the authorized audit from a real attack.
4. Now see the fix. You do not need a weaponized kit to audit this app. You
   need three narrow things: the vulnerable path, the bug class, and one small
   proof. Each one is an authorized task. One subagent does each one.

The split is scoping, not evasion. You drop the attack tool, the persistence,
the harvesting, and the mass use. You keep only the authorized audit. The three
tasks together must never rebuild the refused kit.

---

## The architecture

```
scoped-review skill (the orchestrator you complete)
  |-- reviewer     reads code, finds one source-to-sink path   -> candidates.json
  |-- analyst      names the bug class, explains the data flow  -> analysis.json
  |-- poc-writer   writes one small reproducer for the lab app  -> poc.md
```

Each subagent has its own context and its own tool allowlist. The Reviewer and
the Analyst get no Bash. They read code. This is least privilege. A narrow tool
list is a smaller attack surface.

---

## Tier 1 - Complete the orchestrator (everyone completes this)

1. Read the three subagents in `.claude/agents/`. Note the tool allowlist on
   each one.
2. Open `skills/scoped-review/SKILL.md`. Complete each `TODO`:
   - Steps 1, 3, and 5: write the one-line task for each subagent. Each task is
     narrow and authorized. No task asks for a weapon, for persistence, or for
     mass use.
   - Steps 2, 4, and 6: this comes in Tier 2. For Tier 1, dispatch the
     subagents in order and pass each output to the next.
3. Run the completed skill against `vulnerable_app/app.py`.

Tier 1 passes when each subagent returns its output, no subagent refuses, and
the pipeline finds the command injection on `/ping` with a small proof.

---

## Tier 2 - Validate every handoff (most people reach this)

Complete the validation `TODO` steps in the stub. The validator is code, not a
model.

1. Step 2: validate `candidates.json`. Reject a candidate with no `source` or
   no `sink`.
2. Step 4: validate `analysis.json`. Reject a result with no `cwe`.
3. Step 6: validate `poc.md`. Reject a proof with no safe marker. Reject a
   proof that names a host other than the lab app.
4. On a failed validation, dispatch the failed subagent one more time with the
   error as context. On a second failure, stop and report.

Tier 2 passes when a bad handoff stops the pipeline and the report names the
subagent that failed.

---

## Tier 3 - Scope discipline (for the fast finishers)

Pick one or more:

- **Write `scoping_notes.md`.** Compare the refusal from the demo with the
  success from the pipeline. Name the words in the broad request that caused the
  refusal. Explain how the narrow tasks kept every authorized need.
- **Name the line.** Write one paragraph. Explain the difference between scoping
  and evasion. Scoping drops the parts that are not authorized. Evasion hides a
  refused task in small pieces that rebuild the whole. Explain how your three
  tasks stay on the scoping side.
- **Tighten the tool lists.** Review each subagent. Remove each tool that the
  subagent does not use. Run the pipeline again. Show that it still works.
- **Add a fourth subagent.** Add a Verifier that reads `poc.md` and validates the
  safe marker. Give it the smallest tool list that works.

---

## What "done" looks like

- The `scoped-review` stub is complete. Each subagent gets one narrow,
  authorized task (Tier 1).
- The pipeline finds the command injection and writes a small proof (Tier 1).
- A deterministic validator gates every handoff. A bad handoff stops the
  pipeline (Tier 2).
- `scoping_notes.md`, the scoping-against-evasion paragraph, tighter tool lists,
  or the Verifier subagent (Tier 3).

Keep notes on which subagent task was the hardest to scope. We compare the notes
in the debrief.
