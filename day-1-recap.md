# Training Day Recap — 2026-10-06

Assembled from Claude Code prompt logs, git commits, and file timestamps.
All times in IST (GMT+5:30). The Codespace runs in UTC; times below are converted.
Note: no `~/.bash_history` exists, so terminal commands aren't captured — this
timeline is built from Claude Code prompts, git history, and file timestamps.

## Timeline

### Early afternoon — Threat modeling (litellm project)
- **12:39–14:29** — Threat modeling exercise: ran `/skills`, prompted Claude as a security engineer to build a threat model for the litellm project (two passes). Outputs: `litellm-threat-model.md` and `threat-model-litellm.md`.

### Mid-afternoon — MCP tool harness (lab-13)
- **15:15–15:28** — Explored the MCP server: inspected tools via `/mcp`, worked through tool invocation and verification ("check if the tool really executed", "check the source code"), then extended `server.py` with a version-scan wrapped tool and reloaded plugins.
- **15:30–15:38** — Added a second scanning tool to the server, switched its interface from a file argument to host/port arguments, then used the skill generator to build a staged workflow skill with strict ordering enforcement.
- **15:53** — Course-corrected the design: "don't wrap the MCP servers themselves in a driver."

### Release commits
- **13:48** — `Release 17` (RAG grounding lab).
- **16:26** — `Release base` (devcontainer setup, update.sh).
- **16:32** — `Release 16, 13, 15` (MCP tool harness, context-efficiency, skill-vs-MCP-state labs — 1,311 insertions).
- **16:41** — `Release 18` (pcap-MCP lab with capture files).
- **16:42** — `Release 04` (subagents lab: analyst/poc-writer/reviewer agents, scoped-review + exploit-kit skills).
- Also landed: `Release 00, 14, 12`.

### Late afternoon — Subagents lab (lab-04)
- **17:13–17:37** — Ran the exploit-kit and scoped-review skills against the lab's vulnerable_app, with `/clear` resets between runs (scoped-review run twice).

### Evening
- **18:55 onward** — Training wrap-up and this recap.

## Topics covered across the day
1. Threat modeling a real project (litellm)
2. Building and extending MCP tool servers
3. Tool verification and source inspection
4. Skill generation with enforced multi-step workflows
5. Subagents (analyst / poc-writer / reviewer roles)
6. Context efficiency, RAG grounding, skill-vs-MCP-state tradeoffs
