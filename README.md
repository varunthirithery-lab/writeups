# Writeups

This repository holds the step-by-step solutions of the training "AI as a
Tool for Security Work". Each writeup shows one lab, one step at a time. Each
step has three parts: **Do** (the action), **Result** (what you see when the
step works), and **Why** (the lesson).

You can do each lab again with its writeup. Run the commands in the terminal
of your own Codespace. The lab directories are in your `participant-NN` repo
under `labs/`.

**One rule for the whole course:** every file your AI tool reads is a potential
instruction to that tool.

## Day 1

In the order of the day:

1. [Lab 00 - Setup and the slop demo](day-1/lab-00-setup.md)
2. [Lab 12 - Local AI dev environment](day-1/lab-12-local-ai-dev-env.md)
3. [Exercise - Threat model of LiteLLM](day-1/exercise-threat-model-litellm.md)
4. [Lab 16 - Skill versus MCP for state](day-1/lab-16-skill-vs-mcp-state.md)
5. [Lab 13 - MCP tool harness](day-1/lab-13-mcp-tool-harness.md)
6. [Lab 04 - Subagents](day-1/lab-04-subagents.md)

## Corrected lab files for Day 1

Two Day 1 labs got corrections after the release. The writeups describe the
corrected files. Copy them into your repo from the Codespace terminal:

```
cd /workspaces/participant-*
git clone https://github.com/ai4sec-training/writeups /tmp/writeups
cp /tmp/writeups/day-1/fixes/lab-16-skill-vs-mcp-state/mcp-version/state_server.py labs/lab-16-skill-vs-mcp-state/mcp-version/state_server.py
cp /tmp/writeups/day-1/fixes/lab-04-subagents/README.md labs/lab-04-subagents/README.md
cp /tmp/writeups/day-1/fixes/lab-04-subagents/CLAUDE.md labs/lab-04-subagents/CLAUDE.md
```

| File | Correction |
|---|---|
| `lab-16-skill-vs-mcp-state/mcp-version/state_server.py` | A tool call that comes after its step passed now returns the `OUT_OF_ORDER` error. Before, a second `review_read` call raised a Python `KeyError`. |
| `lab-04-subagents/README.md` and `CLAUDE.md` | Step 6 no longer refers to `validate.py` from Lab 03. It asks for a validator that you write in the lab directory. |
