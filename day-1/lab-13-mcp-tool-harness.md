# Lab 13 - Solution, step by step

This file shows the full lab, one step at a time. You can do the lab again with
this file. Each step has three parts:

- **Do** is the action.
- **Result** is what you see when the step works.
- **Why** is the lesson of the step.

The three scanners are your choice. This solution wraps semgrep, nuclei, and
nmap. `server.py` already holds the nmap tool as the worked example.

**One rule for the whole course:** every file your AI tool reads is a potential
instruction to that tool. A tool argument comes from a model. Treat every tool
argument as untrusted.

## What you learn

- You wrap a scanner as an MCP tool with a fixed contract.
- You validate each argument before the scanner starts.
- You return a structured error, not a Python error, on each failure.

## The harness contract

Each tool does these four things:

1. It declares typed inputs.
2. It enforces a timeout.
3. It returns JSON, not raw scanner output.
4. It parses the scanner output into fields.

## Before you start

Open the terminal of your Codespace. Go to the lab directory.

```
cd /workspaces/participant-*/labs/lab-13-mcp-tool-harness
```

---

## Tier 1 - One tool

### Step 1 - Make the allowed base directory

**Do.**

```
sudo mkdir -p /home/user/targets
sudo chown "$USER" /home/user/targets
echo 127.0.0.1 > /home/user/targets/hosts.txt
cp -r /workspaces/participant-*/labs/lab-13-mcp-tool-harness /home/user/targets/code
```

**Result.** `ls /home/user/targets` shows `code` and `hosts.txt`.

**Why.** `server.py` sets `ALLOWED_BASE` to `/home/user/targets`. A new
Codespace has no such directory. Without it, each path argument fails with
`INVALID_PATH`. The `code` directory is your target for a code scanner. The
`hosts.txt` file is your target for nmap.

### Step 2 - Read the worked example

**Do.** Open `server.py`. Read the `run_nmap` function. Find these five steps
in the code:

1. The tool validates the path with `_safe_path`.
2. The tool validates the `ports` argument.
3. The tool builds an argument vector, not a shell string.
4. The tool runs the scanner through `_run` with a timeout.
5. The tool parses the output and returns JSON.

**Result.** You can point to the line of each step.

**Why.** Each tool that you write has this same shape.

### Step 3 - Add a helper against option injection

**Do.** Add this function to `server.py`, below the `run_nmap` function.

```python
def _reject_option(value: str, field: str) -> None:
    """Reject an argument that a scanner can read as a command-line option.

    Args:
        value: The argument value from the model. This value is untrusted.
        field: The argument name. The error message names this field.

    Raises:
        ValueError: The value starts with a dash.
    """
    if value.startswith("-"):
        raise ValueError(f"Field {field} starts with a dash: {value}")
```

**Result.** `python3 -c "import server"` prints nothing. The file has no
syntax error.

**Why.** The argument vector stops shell injection. It does not stop option
injection. A value that starts with a dash becomes an option of the scanner.
This helper rejects such a value.

### Step 4 - Add the semgrep tool

**Do.** Add this function to `server.py`, below the helper.

```python
@mcp.tool()
async def run_semgrep(repo_path: str, config: str = "auto", timeout: int = DEFAULT_TIMEOUT) -> str:
    """Scan a code directory with semgrep and return parsed JSON results.

    Args:
        repo_path: Absolute path to a directory under the allowed base.
        config: A semgrep rule set, for example "auto" or "p/python".
        timeout: The timeout in seconds for the scan.

    Returns:
        A JSON string with parsed results, or a structured error object.
    """
    # Step 1: validate the path argument. The path is untrusted.
    try:
        safe_repo = _safe_path(repo_path)
    except ValueError as exc:
        return _structured_error(
            "INVALID_PATH", str(exc),
            "Give an absolute path under the allowed base directory.")

    # Step 2: validate the free-text argument. Each helper raises ValueError.
    try:
        _reject_metacharacters(config, "config")
        _reject_option(config, "config")
    except ValueError as exc:
        return _structured_error(
            "INVALID_ARGUMENT", str(exc),
            "Give a rule set name, for example auto or p/python.")

    # Step 3: build the argument vector. Never build a shell string.
    argv = ["semgrep", "--config", config, "--json", str(safe_repo)]

    # Step 4: run the scanner with the enforced timeout.
    try:
        code, stdout, stderr = await _run(argv, timeout)
    except asyncio.TimeoutError:
        return _structured_error(
            "TIMEOUT", f"semgrep ran longer than {timeout} seconds.",
            "Scan a smaller directory, or raise the timeout.")
    except FileNotFoundError:
        return _structured_error(
            "TOOL_MISSING", "The semgrep binary is not on the PATH.",
            "Install semgrep, or choose a different tool.")

    # Step 5: parse the scanner output. Keep only the fields that the agent needs.
    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError:
        return _structured_error(
            "PARSE_FAILED", stderr[-500:],
            "Validate that semgrep produced JSON output.")
    results = [
        {
            "rule_id": result.get("check_id", ""),
            "path": result.get("path", ""),
            "line": result.get("start", {}).get("line", 0),
            "severity": result.get("extra", {}).get("severity", ""),
        }
        for result in parsed.get("results", [])
    ]
    return json.dumps({
        "error": False,
        "tool": "semgrep",
        "target": str(safe_repo),
        "results": results,
        "result_count": len(results),
    })
```

**Result.** `python3 -c "import server"` prints nothing.

**Why.** Compare the function with the contract:

- **Typed inputs.** `repo_path: str`, `config: str`, `timeout: int`.
- **Validation.** `_safe_path` keeps the path under the allowed base. The two
  helpers reject shell control characters and options.
- **Structured error.** The helpers raise `ValueError`. The tool catches the
  exception and returns `_structured_error`. A tool that does not catch the
  exception gives the agent a Python error.
- **Timeout.** `_run` stops the scanner after `timeout` seconds.
- **Parsed output.** The tool keeps four fields of each result. The full
  semgrep output is large. A small result costs fewer tokens.

### Step 5 - Register the server

**Do.**

```
claude mcp add security-tool-harness -- python3 "$PWD/server.py"
claude mcp list
```

**Result.** `claude mcp list` shows `security-tool-harness` as connected.

**Why.** The registration applies to the current directory. Thus you must
start `claude` from the lab directory. `"$PWD"` makes the path absolute.

### Step 6 - Ask the agent to call your tool

**Do.**

```
claude -p "Call the run_semgrep tool with repo_path /home/user/targets/code. Print the JSON that the tool returns." --allowedTools "mcp__security-tool-harness__run_semgrep"
```

**Result.** The agent prints one JSON object. The object starts like this:

```json
{"error": false, "tool": "semgrep", "target": "/home/user/targets/code", "results": [], "result_count": 0}
```

The `results` list depends on the rules and on the code. An empty list is a
valid result. Tier 1 passes when the agent gets this JSON.

**Why.** The agent decided when to call the tool. The scanner decided what the
tool returns. The agent ran no shell command. This is principle P3: wrap, do
not replace.

The `auto` rule set needs the network. Without a network, pass a different
rule set, for example `config` with the value `p/python`.

---

## Tier 2 - Three tools with validation

### Step 7 - Add the nuclei tool

**Do.** Add this function to `server.py`, below the semgrep tool.

```python
@mcp.tool()
async def run_nuclei(target_url: str, templates: str = "cves", timeout: int = DEFAULT_TIMEOUT) -> str:
    """Scan one URL with nuclei and return parsed JSON findings.

    Args:
        target_url: The URL to scan. It must start with http:// or https://.
        templates: A template directory name, for example "cves".
        timeout: The timeout in seconds for the scan.

    Returns:
        A JSON string with parsed findings, or a structured error object.
    """
    # Step 1: validate every argument. Each helper raises ValueError.
    try:
        _reject_metacharacters(target_url, "target_url")
        _reject_metacharacters(templates, "templates")
        _reject_option(templates, "templates")
    except ValueError as exc:
        return _structured_error(
            "INVALID_ARGUMENT", str(exc),
            "Remove the forbidden characters. Then call the tool again.")
    if not target_url.startswith(("http://", "https://")):
        return _structured_error(
            "INVALID_URL", f"Bad target URL: {target_url}",
            "Give a URL that starts with http:// or https://.")

    # Step 2: build the argument vector. Never build a shell string.
    argv = ["nuclei", "-u", target_url, "-t", templates, "-jsonl", "-silent"]

    # Step 3: run the scanner with the enforced timeout.
    try:
        code, stdout, stderr = await _run(argv, timeout)
    except asyncio.TimeoutError:
        return _structured_error(
            "TIMEOUT", f"nuclei ran longer than {timeout} seconds.",
            "Use fewer templates, or raise the timeout.")
    except FileNotFoundError:
        return _structured_error(
            "TOOL_MISSING", "The nuclei binary is not on the PATH.",
            "Install nuclei, or choose a different tool.")
    if code != 0:
        return _structured_error(
            "SCAN_FAILED", stderr[-500:],
            "Review the target URL and the template name.")

    # Step 4: parse each JSON line. Keep only the fields that the agent needs.
    findings = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            return _structured_error(
                "PARSE_FAILED", f"nuclei printed a line that is not JSON: {line[:200]}",
                "Run the scan again. Validate the nuclei version.")
        info = item.get("info", {})
        findings.append({
            "template_id": item.get("template-id", ""),
            "name": info.get("name", ""),
            "severity": info.get("severity", ""),
            "matched_at": item.get("matched-at", ""),
        })
    return json.dumps({
        "error": False,
        "tool": "nuclei",
        "target": target_url,
        "findings": findings,
        "finding_count": len(findings),
    })
```

**Result.** `python3 -c "import server"` prints nothing.

**Why.** This tool takes a URL, not a path. Thus it has a different validation: the
URL must start with `http://` or `https://`. The metacharacter set holds `?`,
`&`, and `#`. Thus the tool rejects a URL with a query string. This is strict
on purpose. Scan the base URL.

The Codespace image has no `nuclei` binary. The tool then returns the
`TOOL_MISSING` error. This is the expected behavior: a structured error, not a
Python error.

### Step 8 - Make the nmap tool work

**Do.** The Codespace image has no `nmap` binary. Install it. Then call the
worked example. Each `claude` command starts a new session, so the agent sees
your new tools.

```
sudo apt-get update -qq && sudo apt-get install -y -qq nmap
claude -p "Call the run_nmap tool with target_path /home/user/targets/hosts.txt and ports 1-1024. Print the JSON that the tool returns." --allowedTools "mcp__security-tool-harness__run_nmap"
```

**Result.** The agent prints JSON with the fields `tool`, `ports_scanned`,
`open_ports`, and `open_count`. It does not print the raw nmap output.

**Why.** You now have three tools, and each tool wraps a different scanner.
Scan only targets that you own. `127.0.0.1` is your own Codespace.

### Step 9 - Test each tool with bad input

**Do.** Call the functions directly from Python. This test uses no model and no
tokens.

```
python3 -c "import asyncio, server; print(asyncio.run(server.run_semgrep('/home/user/targets/../../etc')))"
python3 -c "import asyncio, server; print(asyncio.run(server.run_semgrep('/home/user/targets/code', config='auto; id')))"
python3 -c "import asyncio, server; print(asyncio.run(server.run_semgrep('/home/user/targets/code', config='--help')))"
python3 -c "import asyncio, server; print(asyncio.run(server.run_nuclei('file:///etc/passwd')))"
python3 -c "import asyncio, server; print(asyncio.run(server.run_nuclei('http://127.0.0.1:8080')))"
```

**Result.** Each command prints one object with `"error": true`. The codes are,
in order:

| Call | Code |
|---|---|
| A path that escapes the allowed base | `INVALID_PATH` |
| The config `auto; id` | `INVALID_ARGUMENT` |
| The config `--help` | `INVALID_ARGUMENT` |
| The URL `file:///etc/passwd` | `INVALID_URL` |
| A scanner that is not installed | `TOOL_MISSING` |

Two more codes exist. A scan that runs longer than the timeout returns
`TIMEOUT`. Scanner output that is not JSON returns `PARSE_FAILED`.

Tier 2 passes when no command prints a Python error message.

**Why.** A model produces each argument. A malicious target can steer the
model. Thus you test the tool with the input that an attacker would send. The
agent can read the `code` field and decide the next action.

---

## Tier 3 - Stretch

### Step 10 - Add a dispatch tool

**Do.** Add this function to `server.py`.

```python
@mcp.tool()
async def dispatch(request: str) -> str:
    """Select one tool from a plain-language request. Return the tool name."""
    request_lower = request.lower()
    if "port" in request_lower or "host" in request_lower or "network" in request_lower:
        choice = "run_nmap"
    elif "url" in request_lower or "web" in request_lower or "cve" in request_lower:
        choice = "run_nuclei"
    else:
        choice = "run_semgrep"
    return json.dumps({"error": False, "selected_tool": choice,
                       "reason": "Keyword match on the request."})
```

**Result.** A request with the word "port" selects `run_nmap`. A request with
the word "CVE" selects `run_nuclei`. Each other request selects `run_semgrep`.

**Why.** The point of dispatch is context efficiency. The agent loads only the
one tool contract that it needs. This is important in a long session with many
tools.

### Step 11 - Write the attack-surface paragraph

**Do.** Write one paragraph. Explain why an MCP server is attack surface.

**Result.** This is one valid paragraph:

> An MCP server is attack surface. The server runs tools for a model. A
> malicious target can plant text that steers the model. The model then sends
> arguments to your tools. A weak tool passes those arguments to a shell. The
> attacker then runs commands on your host. Each validation step in this lab
> blocks one path. Path validation blocks directory escape. The metacharacter
> validation blocks shell injection. The argument vector blocks shell parsing.
> The dash validation blocks option injection. The timeout blocks a denial of
> service.

One attack that the validation blocks: the model sends the config value
`auto; id` to `run_semgrep`. With a shell string, the shell runs `id`. With
this server, the tool returns `INVALID_ARGUMENT` and starts no process.

**Why.** This is the Day 2 lesson in one tool. Your security tools are targets
too.

---

## What a pass looks like

- **Tier 1.** One `@mcp.tool()` function wraps a scanner. The tool declares
  typed inputs. The tool enforces a timeout. The tool returns parsed JSON. The
  agent calls the tool and gets JSON.
- **Tier 2.** You have three tools, and each tool wraps a different scanner.
  Each tool validates its path with `_safe_path`. Each tool rejects shell
  control characters. No tool uses `shell=True`. Each tool returns the
  structured error shape on bad input and on failure.
- **Tier 3.** You have a dispatch tool that routes by request, a global timeout
  budget, or a clear attack-surface paragraph.

A different set of scanners is fine. Semgrep plus bandit plus nmap is a good
set for Python code.

---

## Common mistakes

- **The tool returns raw stdout.** The agent then parses prose. The parse step
  is the control, not a convenience.
- **No timeout.** The tool calls `communicate()` without `asyncio.wait_for`. A
  slow scan stops the agent. Use the `_run` helper.
- **The tool uses `shell=True`.** The tool builds a command string and runs it
  in a shell. A malicious argument then runs a shell command. Pass an argument
  vector.
- **An unvalidated path.** The tool calls the scanner on a raw `repo_path`. A
  path such as `../../etc` escapes the lab. Use `_safe_path`.
- **A Python error in place of a structured error.** A validation helper raises
  `ValueError` and the tool does not catch it. The agent cannot act on the
  result. Catch the exception and return `_structured_error`.
- **One giant tool.** One tool with a mode flag is hard to audit. Keep each
  tool small with a narrow contract.
- **You changed `server.py` and the agent does not see the new tool.** The
  agent loads the tools when a session starts. Start a new `claude` session.
