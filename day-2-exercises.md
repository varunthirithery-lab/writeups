# Day 2 — Exercise Guide (2026-10-07)

A step-by-step guide to repeat each exercise from Day 2 and end up with a
working result. Each section is self-contained.

---

## Exercise 1: Build and harden a workbench MCP server

**What you learned**

How to expose a Kali container to Claude Code through MCP, then lock it down
with token auth, DNS validation, and scope control.

**Starting point**

You have the `ai-security-workbench` directory with a Kali `workbench`
container in `autolab/docker-compose.yml`. The container runs but Claude Code
cannot call tools on it — no MCP channel exists.

**Repeat it yourself**

1. Start a Claude Code session in the workbench directory:
   ```bash
   cd /workspaces/*/ai-security-workbench
   claude
   ```

2. Tell Claude Code the problem:
   ```
   The kali workbench is not connected to the claude-code compose stack.
   Fix this by having workbench expose an MCP server reachable by claude-code
   that will give it jobs (e.g. execute command).
   ```

3. Claude Code will create `autolab/docker/workbench/mcp_server.py` with an
   initial tool (e.g. `run_nmap`). Review the generated code. Look for:
   - How it validates targets (DNS resolution, private-address check).
   - How it runs subprocesses (argv list, no shell=True).
   - How it caps output size and timeout.

4. Add auth and network isolation:
   ```
   Add token auth and a separate Docker network.
   ```
   Claude Code adds `Authorization: Bearer` checking with
   `hmac.compare_digest` and a new network in docker-compose.

5. Rebuild and test:
   ```bash
   make build && make up-lab
   make attach
   # inside the claude-code container:
   /mcp   # workbench should show 'connected'
   ```

6. Test the scope gate. From inside claude-code, call:
   - `tool_versions` — returns the tool list without an auth error.
   - `set_scope` with targets `["10.0.0.0/8"]`.
   - `run_nmap` against a private IP — passes.
   - `run_nmap` against a public IP — rejected.

**Check your result**

- [ ] `tool_versions` returns without auth error
- [ ] `run_nmap` rejects public IPs with "not a private address"
- [ ] Requests without the Bearer token get 403
- [ ] Audit log appears at `/shared/output/audit.jsonl`

**Gotchas**

- FastMCP ignores environment variables if you pass `host`/`port` to the
  constructor. Set `mcp.settings.host` after construction instead.
- DNS rebinding protection in FastMCP blocks `0.0.0.0`. For a container that
  must bind all interfaces, set `mcp.settings.transport_security = None`.
- The workbench container needs packages installed at build time. If a tool
  binary is missing, add it to the `Dockerfile` and rebuild.

**Key file:** `ai-security-workbench/autolab/docker/workbench/mcp_server.py`

---

## Exercise 2: Expand the workbench toolset through brainstorming

**What you learned**

How to use a structured brainstorm interview to scope a large tool surface, and
how to implement 30+ tools with a shared guardrail pattern.

**Starting point**

You have a working MCP server with 2–3 tools (`run_command`, `run_nmap`). You
want a full offensive toolkit.

**Repeat it yourself**

1. Start the brainstorm. Ask Claude Code:
   ```
   Brainstorm additional tools to add to the workbench MCP with me.
   Interview and grill me on which ones and the scope until we have
   shared understanding.
   ```

2. Claude Code asks structured questions about categories and scope. Answer
   based on what your Kali container has installed. Typical groups:
   - **Network recon:** nmap, nuclei, http-probe, dns-enum, tls-scan
   - **Web fuzzing:** sqlmap, ffuf
   - **Code/binary analysis:** semgrep, bandit, gitleaks, trivy, checksec,
     readelf, strings, gdb-batch
   - **Compilation:** gcc/make (build C exploits)
   - **Credential cracking:** john (offline only, via start/results pattern)
   - **Container/image analysis:** hadolint, trivy-image (with registry
     allowlist)
   - **Android static analysis:** apktool, jadx
   - **Infrastructure:** background jobs (start/status/output/cancel), file
     access (list/read/write artifacts), scope/audit (set/get scope,
     tool_versions)

3. After agreement, tell Claude Code to implement:
   ```
   Sounds good, add these tools. Make sure the required packages are
   getting installed on Kali if they don't exist yet.
   ```

4. Review the generated code for the shared guardrail pattern:
   - `_safe_path(path)` — resolves the path and checks it stays under
     `/work` or `/shared/output`. No `..` escapes, no symlink escapes.
   - `_check_target(host)` — resolves DNS once, checks all addresses are
     private, checks scope. Returns the resolved IP for the caller to use.
   - `@audited` decorator — logs every tool call to `audit.jsonl`.
   - `start_job` / `job_status` / `job_output` / `cancel_job` — for
     anything that runs longer than the 300s MCP call timeout.

5. Test without rebuilding containers. The guardrail functions and tool
   decorators are pure Python — run the logic offline:
   ```bash
   python3 -c "from mcp_server import _safe_path; print(_safe_path('/work/test.txt'))"
   python3 -c "from mcp_server import _check_target; print(_check_target('localhost'))"
   ```

**Check your result**

- [ ] `tool_versions` lists all expected tools
- [ ] `_safe_path('/etc/passwd')` raises or returns an error
- [ ] `_safe_path('/work/../etc/passwd')` raises or returns an error
- [ ] `_check_target('8.8.8.8')` returns an error (public address)
- [ ] `_check_target('localhost')` returns `(None, '127.0.0.1')`
- [ ] `run_trivy_image` rejects images from registries not in the allowlist

**Gotchas**

- The first brainstorm attempt may hit a safety classifier if you list
  offensive tools without context. Restart as an interview and explain the
  authorized-testing scope.
- `run_command` and `start_job` are escape hatches — they bypass the
  private-address and scope checks. Document this as a known limitation.
- `run_trivy_image` pulls from a registry — a different threat surface than
  the private-address rule. Use a separate `WORKBENCH_REGISTRY_ALLOWLIST`
  env var, read once at startup, not changeable at runtime.

**Key file:** `ai-security-workbench/autolab/docker/workbench/mcp_server.py`
(~1,280 lines)

---

## Exercise 3: Enforce a workbench gate across exploitation skills

**What you learned**

How to update a set of skills so that active exploitation runs only on an
isolated container, while recon stays on the main agent.

**Starting point**

You have 13 web exploitation skills (web-sqli, web-xss, web-ssrf, etc.) and
the `web-pentest-dispatch` orchestrator. All skills use Playwright or Bash for
every phase. You want Phases 2–5 (injection, client-side, auth, supplementary)
to use the workbench instead.

**Repeat it yourself**

1. Tell Claude Code to update the skills:
   ```
   Update the skills to force usage of kali workbench tools for any
   active offensive security activities that go beyond recon.
   ```

2. Claude Code creates a shared gate protocol at
   `skills/web-pentest-dispatch/protocols/workbench-gate.md`. Review it.
   It defines:
   - A **tool mapping** table (which workbench tool handles which activity).
   - A **pre-exploitation checklist** (`tool_versions`, `set_scope`).
   - A **stop rule** (if workbench tools are not available, report recon
     findings only).

3. Claude Code updates each of the 13 skill `SKILL.md` files to:
   - Add `mcp__workbench__*` and `mcp__security-tool-harness__*` to
     `allowed-tools`.
   - Add a "Workbench gate" section at the top of the workflow, before the
     existing steps.
   - Reference the shared gate protocol.

4. Claude Code updates the orchestrator at
   `skills/web-pentest-dispatch/protocols/orchestrator.md` to add a
   "Workbench gate" section and routing notes.

5. If the skills exist in two places (repo root and workbench agent config),
   apply the same changes to both:
   ```
   Now do the same for the workbench copies in
   ai-security-workbench/agent-config/skills
   ```

6. Verify by reading one updated skill:
   ```bash
   head -30 .claude/skills/web-sqli/SKILL.md
   ```
   The `allowed-tools` line should include `mcp__workbench__*`, and a
   "Workbench gate" section should appear before the workflow.

**Check your result**

- [ ] All 13 skill files have `mcp__workbench__*` in `allowed-tools`
- [ ] All 13 skill files have a "Workbench gate" section
- [ ] `protocols/workbench-gate.md` exists with the tool mapping table
- [ ] `protocols/orchestrator.md` references the workbench gate
- [ ] Both skill copies (repo root + agent-config) match

**Gotchas**

- The `allowed-tools` field in SKILL.md frontmatter uses glob syntax. Use
  `mcp__workbench__*` (with double underscores), not `mcp_workbench_*`.
- The recon-only fallback is important. If a participant does not have the
  workbench running, the skill should still produce recon findings instead
  of failing silently.
- Ensure the tool mapping table is consistent across the shared protocol and
  the individual skill sections. If you add a new workbench tool later,
  update both.

**Key files:**
- `.claude/skills/web-pentest-dispatch/protocols/workbench-gate.md`
- `.claude/skills/web-pentest-dispatch/protocols/orchestrator.md`
- `.claude/skills/web-sqli/SKILL.md` (and 12 others)

---

## Exercise 4: Integrate a knowledge-graph MCP (Grafeo)

**What you learned**

How to add a persistent knowledge graph to a Claude Code environment so the
agent can remember targets, findings, tasks, and their relationships across
sessions.

**Starting point**

You have the `ai-security-workbench` compose stack with pyrunner, playwright,
and searxng. You want to add Grafeo as a fourth MCP server for structured
memory.

**Repeat it yourself**

1. Tell Claude Code what you want:
   ```
   Add the grafeo MCP server for the claude code and enable it for the
   main agent to remember and plan complex tasks! Add skills and
   instructions for this, brainstorm with me until we got a common
   understanding.
   ```

2. Claude Code asks structured questions about the integration. Key decisions:
   - **Transport:** streamable-http (not stdio) — the server runs in its own
     container.
   - **Storage:** embedded GrafeoDB on a persistent bind-mount volume at
     `./data/grafeo/`.
   - **Schema:** fixed node labels (Target, Finding, Task, Evidence, Tool,
     Session) and edge types (AFFECTS, FOUND_BY, EVIDENCED_BY, etc.).

3. Claude Code creates:
   - `docker/grafeo-mcp/Dockerfile` — Python 3.12-slim, installs `grafeo-mcp`
     via pip.
   - `docker/grafeo-mcp/start.py` — wrapper that sets host/port from env vars.
   - `skills/use-grafeo/SKILL.md` — graph schema, rules, and tool reference.
   - Updates to `docker-compose.yml`, `agent-config/.mcp.json`,
     `agent-config/CLAUDE.md`, and `agent-config/settings.local.json`.

4. Build and start:
   ```bash
   make setup && make build && make up
   ```

5. Verify MCP connectivity:
   ```bash
   make attach
   # inside claude-code container:
   /mcp   # grafeo should show 'connected'
   ```

6. Test the graph. From inside claude-code, call:
   - `graph_info` — returns schema and node counts.
   - `create_node` with label `Target`, properties `{"name": "test-app"}`.
   - `search_nodes_by_label` with label `Target` — returns the node you
     created.

**Check your result**

- [ ] `docker compose ps` shows grafeo-mcp running and healthy
- [ ] `/mcp` inside claude-code shows grafeo connected
- [ ] `graph_info` returns without error
- [ ] A created node persists after container restart (bind-mount volume)

**Gotchas**

- FastMCP constructor default for `host` overrides the `GRAFEO_MCP_HOST`
  env var. Set `mcp.settings.host` after constructing the FastMCP instance.
- FastMCP DNS rebinding protection rejects `0.0.0.0`. Set
  `mcp.settings.transport_security = None` for containers that need to bind
  all interfaces.
- The grafeo-mcp container needs to be on the same Docker network as
  claude-code. Add it to `claude-network` (or whatever your bridge network
  is called) in docker-compose.yml.
- The `enabledMcpjsonServers` array in `settings.local.json` must include
  `"grafeo"` for the agent to see it.

**Key files:**
- `ai-security-workbench/docker/grafeo-mcp/Dockerfile`
- `ai-security-workbench/docker/grafeo-mcp/start.py`
- `ai-security-workbench/skills/use-grafeo/SKILL.md`

---

## Exercise 5: RAG grounding for a bug hunter (lab-17)

**What you learned**

How to ground an AI reviewer in proven past findings using a local RAG
pipeline, so it reasons from real verdicts instead of invented patterns.

**Starting point**

You have `labs/lab-17-rag-grounding/` with a corpus of 12 past findings, an
embedding script, a query script, a skill wrapper, and an MCP server.

**Repeat it yourself**

1. Install dependencies (CPU only, takes a few minutes):
   ```bash
   bash /workspaces/*/labs/lab-17-rag-grounding/install.sh
   ```

2. Embed the corpus into ChromaDB:
   ```bash
   cd /workspaces/*/labs/lab-17-rag-grounding
   python3 scripts/embed_corpus.py
   ```
   The script prints the count of embedded findings (12).

3. Query the corpus:
   ```bash
   python3 scripts/query_corpus.py "SQL injection via string concatenation"
   ```
   The top hits should be SQL injection findings with `true_positive` or
   `false_positive` labels and proof text.

4. Register the MCP server:
   ```bash
   claude mcp add --scope project past-findings -- python3 server.py
   ```

5. Ask Claude Code to call `search_past_findings` with a query. Compare the
   MCP result with the skill result (invoke `/search-past-findings`).

6. (Bonus) Embed the SEI CERT library (2,989 examples):
   ```bash
   python3 scripts/embed_sei.py
   python3 scripts/query_sei.py "out-of-bounds array subscript" --language c
   ```
   The top hit should be ARR30-C.

**Check your result**

- [ ] `embed_corpus.py` completes without error
- [ ] A "SQL injection" query returns SQL injection findings on top
- [ ] Each hit shows label (`true_positive` / `false_positive`) and proof
- [ ] The MCP tool and the skill return the same results
- [ ] (Bonus) `query_sei.py` returns ARR30-C for array bounds queries

**Gotchas**

- If `query_sei.py` returns no results, the SEI collection has not been
  embedded yet. Run `embed_sei.py` first. The corpus and SEI collections
  are separate — embedding one does not embed the other.
- The embedding model downloads on first run (~90 MB). If the download
  fails, check network access from the Codespace.
- The corpus is untrusted input (P1). A poisoned corpus entry is an indirect
  prompt injection. The proof field is the ground truth — if a retrieved
  finding has no proof, do not trust its label.

**Key files:**
- `labs/lab-17-rag-grounding/scripts/embed_corpus.py`
- `labs/lab-17-rag-grounding/scripts/query_corpus.py`
- `labs/lab-17-rag-grounding/server.py`
- `labs/lab-17-rag-grounding/search-past-findings/SKILL.md`

---

## Exercise 6: Review Day 1 solutions

**What you learned**

The trainer released `SOLUTION.md` files for six exercises from Day 1. Compare
your work against the reference solutions.

**Repeat it yourself**

1. Pull the latest releases:
   ```bash
   cd /workspaces/participant-04
   bash update.sh
   ```

2. Read each solution:
   ```bash
   cat labs/lab-00-setup/SOLUTION.md
   cat labs/lab-04-subagents/SOLUTION.md
   cat labs/lab-12-local-ai-dev-env/SOLUTION.md
   cat labs/lab-13-mcp-tool-harness/SOLUTION.md
   cat labs/lab-16-skill-vs-mcp-state/SOLUTION.md
   cat labs/exercise-threat-model-litellm/SOLUTION.md
   ```

3. Compare with your own outputs from Day 1. Note:
   - Approaches you took that differ from the reference.
   - Findings or steps you missed.
   - Techniques in the solution that you want to adopt.

**Check your result**

- [ ] All six `SOLUTION.md` files are present
- [ ] You read and compared each against your own Day 1 work

---

## Exercise 7: Run a pentest through the workbench

**What you learned**

How to use the hardened workbench you built in Exercises 1 to 3 against a live
target. The scope control, the workbench gate, and the audit log all work
together in a real test.

**Starting point**

You have the full workbench stack from Exercises 1 to 3: 33 tools, token auth,
scope control, and the workbench gate enforced across all 13 web exploitation
skills. The stack runs in Docker Compose.

> **Target note.** The original target was Juice Shop
> (`juice-shop.herokuapp.com`). Juice Shop went down during the day. The
> trainer switched the target to `demo.testfire.net` (only!). Do not test any
> other target.

**Repeat it yourself**

1. Start the stack and attach to the claude-code container:
   ```bash
   cd /workspaces/*/ai-security-workbench
   make setup && make build && make up
   make attach
   ```

2. Verify the workbench tools are available:
   ```
   /mcp
   ```
   The workbench should show as connected with 33+ tools.

3. Set the target scope:
   ```
   Call set_scope with targets ["demo.testfire.net"]
   ```

4. Run recon through the workbench:
   ```
   Run recon against demo.testfire.net: nmap, http-probe, and nuclei.
   Summarize the findings.
   ```

5. Run the web-pentest-dispatch skill. The skill routes active exploitation
   through the workbench and keeps recon on the main agent:
   ```
   /web-pentest-dispatch demo.testfire.net
   ```

6. Check the audit log after the run:
   ```bash
   cat /shared/output/audit.jsonl | python3 -m json.tool
   ```
   Every tool call should appear with its timestamp, tool name, and result.

**Check your result**

- [ ] `set_scope` accepted `demo.testfire.net`
- [ ] Recon tools returned structured results (open ports, HTTP headers, nuclei findings)
- [ ] The web-pentest-dispatch skill used workbench tools for active testing
- [ ] `audit.jsonl` logged every tool call
- [ ] No tool call reached a target outside the scope

**Gotchas**

- `demo.testfire.net` is a public address. The workbench rejects public
  addresses by default. The `set_scope` call adds the target to the allowlist.
  Without `set_scope`, every tool call fails with "not in scope".
- If Juice Shop comes back online, you can use it instead. Set the scope to
  `juice-shop.herokuapp.com` and repeat the steps.
- The audit log grows fast during a full pentest dispatch. Check it between
  phases to confirm the gate routes traffic to the workbench.

**Key files:**
- `ai-security-workbench/autolab/docker/workbench/mcp_server.py`
- `.claude/skills/web-pentest-dispatch/SKILL.md`
- `/shared/output/audit.jsonl`

---

## Showcases

Two items were trainer presentations during the day, not hands-on exercises.

### Showcase A: Muraena AiTM proxy

The trainer released a Muraena (evilginx-style) adversary-in-the-middle proxy
as a Docker container in the compose stack (released at 16:24 IST, 643 lines).

**What it does.** Muraena is a transparent reverse proxy that sits between a
victim and a legitimate web application. It captures session tokens and
credentials in real time. The container runs in the compose stack alongside the
Kali workbench.

**How the trainer added it.** The trainer asked Claude Code outside the
Docker Compose to add a container for the phishing proxy. The reference was this
guide: `medium.com/@itsdavidmandal/setting-up-evilginx-in-a-docker-container-on-kali-linux-a-step-by-step-guide-b9076213ad88`.
The trainer reviewed the changes and ensured the proxy enforces local-target
restrictions (it must not proxy traffic to arbitrary external sites).

**To explore it yourself:**
```bash
cd /workspaces/*/ai-security-workbench
docker compose ps    # muraena should appear as running
```

### Showcase B: Structured analysis skill

The trainer shared the Blevene structured-analysis-skill repository:
`github.com/Blevene/structured-analysis-skill`. This skill adds analytical
verification steps to workflows and skills. It helps the agent make better
decisions by forcing structured reasoning before a verdict.

**To install it yourself:**
```bash
cd /workspaces/*/
gh repo clone Blevene/structured-analysis-skill .claude/skills/structured-analysis
```

Then invoke it in a workflow to verify findings before the agent commits to a
verdict.

