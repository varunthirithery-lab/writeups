"""FastMCP server that enforces the review step order with deterministic state.

This server runs one short review flow. The flow has three steps in a fixed
order. Step 1 is review_read. Step 2 is review_prove. Step 3 is review_emit.

The server holds a step counter. The counter is plain Python state. The counter
is not in the model's memory of the chat. Each tool reads the counter. Each tool
checks the order. A tool returns an OUT_OF_ORDER error when the agent calls it
early. A tool advances the counter only after it succeeds.

This is principle P3: wrap, do not replace. The model decides when to call a
tool. The deterministic counter decides if the call is allowed.

This is principle P1: do not trust the input. The model produces each argument.
The server treats each argument as untrusted. The server checks each argument
before it advances the counter.

Run this server with: python3 state_server.py
Restart the server to reset the counter to zero.
"""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("review-state-machine")

# The ordered steps. The index is the required value of the counter before the
# step runs. Step 1 needs a counter of 0. Step 2 needs a counter of 1. Step 3
# needs a counter of 2.
STEP_NAMES = {1: "review_read", 2: "review_prove", 3: "review_emit"}

# The deterministic state. This single integer is the whole state machine. It
# counts the steps that passed. The chat history does not hold this number.
_completed_steps = 0


def _structured_error(code: str, message: str, suggestion: str) -> str:
    """Build the one error shape that every tool returns on failure.

    Args:
        code: A short uppercase code. The agent reads this code and branches.
        message: A short plain description of the failure.
        suggestion: One next action for the agent to try.

    Returns:
        A JSON string. The shape is always the same.
    """
    return json.dumps({
        "error": True,
        "code": code,
        "message": message,
        "suggestion": suggestion,
    })


def _order_error(step_index: int) -> str:
    """Build the OUT_OF_ORDER error for a step that the agent calls out of order.

    A call is out of order in two cases. The agent calls the step too early.
    Or the agent calls a step that already passed.

    Args:
        step_index: The number of the step that the agent called.

    Returns:
        A JSON error string with the code OUT_OF_ORDER.
    """
    this_step = STEP_NAMES[step_index]
    if _completed_steps >= step_index:
        # The step already passed. Step 1 always takes this branch, because
        # step 1 has no earlier step.
        if _completed_steps < len(STEP_NAMES):
            suggestion = f"Call {STEP_NAMES[_completed_steps + 1]} next."
        else:
            suggestion = "The review is complete. Restart the server to start a new review."
        return _structured_error(
            "OUT_OF_ORDER",
            f"Step {step_index} ({this_step}) already passed. "
            f"The counter is at {_completed_steps}.",
            suggestion,
        )
    need_step = STEP_NAMES[step_index - 1]
    return _structured_error(
        "OUT_OF_ORDER",
        f"Step {step_index} ({this_step}) needs step {step_index - 1} "
        f"({need_step}) to pass first. The counter is at {_completed_steps}.",
        f"Call {need_step} first. Then call {this_step}.",
    )


def _success(step_index: int, output: str) -> str:
    """Build the success shape and report the new counter value.

    Args:
        step_index: The number of the step that passed.
        output: The required output text that the step produced.

    Returns:
        A JSON success string. The shape is always the same.
    """
    return json.dumps({
        "error": False,
        "step": step_index,
        "name": STEP_NAMES[step_index],
        "completed_steps": _completed_steps,
        "output": output,
    })


@mcp.tool()
async def review_read(source_file: str, comprehension: str) -> str:
    """Step 1 of the review. Read the target file and report what it does.

    Call this tool first. The server allows this tool only when the counter is
    at 0. The required output is a short plain note. The note lists the
    functions and the entry points of the file.

    Args:
        source_file: The path to the target file. This path is untrusted.
        comprehension: A short note on the file. This text is untrusted.

    Returns:
        A JSON success object, or a structured error object.
    """
    global _completed_steps
    # Check the order first. Step 1 needs a counter of 0.
    if _completed_steps != 0:
        return _order_error(1)
    # Check the path argument. The path comes from the model.
    resolved = Path(source_file).resolve()
    if not resolved.is_file():
        return _structured_error(
            "INVALID_PATH",
            f"The target file does not exist: {resolved}",
            "Give the path to a file that exists.")
    # Check the output argument. An empty note does not pass.
    if not comprehension.strip():
        return _structured_error(
            "EMPTY_OUTPUT",
            "Step 1 needs a comprehension note. The note is empty.",
            "Read the file. Write a short note. Call review_read again.")
    # The step passed. Advance the counter.
    _completed_steps = 1
    return _success(1, comprehension.strip())


@mcp.tool()
async def review_prove(proof: str) -> str:
    """Step 2 of the review. Prove one finding with concrete evidence.

    The server allows this tool only when the counter is at 1. The required
    output is one proof. The proof is a short test, a dataflow trace, or a
    scanner result.

    Args:
        proof: The proof text for one finding. This text is untrusted.

    Returns:
        A JSON success object, or a structured error object.
    """
    global _completed_steps
    # Check the order first. Step 2 needs a counter of 1.
    if _completed_steps != 1:
        return _order_error(2)
    # Check the output argument. An empty proof does not pass.
    if not proof.strip():
        return _structured_error(
            "EMPTY_OUTPUT",
            "Step 2 needs a proof. The proof is empty.",
            "Write one proof for the finding. Call review_prove again.")
    # The step passed. Advance the counter.
    _completed_steps = 2
    return _success(2, proof.strip())


@mcp.tool()
async def review_emit(finding: str) -> str:
    """Step 3 of the review. Emit the final finding as a JSON string.

    The server allows this tool only when the counter is at 2. The required
    output is the final finding. The finding is a valid JSON object.

    Args:
        finding: The final finding as a JSON string. This text is untrusted.

    Returns:
        A JSON success object, or a structured error object.
    """
    global _completed_steps
    # Check the order first. Step 3 needs a counter of 2.
    if _completed_steps != 2:
        return _order_error(3)
    # Check the output argument. The finding must parse as JSON.
    try:
        parsed = json.loads(finding)
    except json.JSONDecodeError as exc:
        return _structured_error(
            "INVALID_JSON",
            f"Step 3 needs a valid JSON finding. The parser failed: {exc}",
            "Fix the JSON. Call review_emit again.")
    # The step passed. Advance the counter.
    _completed_steps = 3
    return _success(3, json.dumps(parsed))


if __name__ == "__main__":
    mcp.run()
