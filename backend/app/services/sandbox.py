import os
import sys
import json
import asyncio
import tempfile
import logging
import httpx
from typing import List, Dict, Any
from app.core.config import NEBIUS_API_KEY

logger = logging.getLogger(__name__)

# Optional remote sandbox URL. If unset or unreachable, automatically falls back to local isolated runner.
SANDBOX_ENDPOINT = os.getenv("NEBIUS_SANDBOX_URL", "").strip()

# Self-contained harness script executed inside an isolated child process
LOCAL_RUNNER_HARNESS = """
import sys
import json
import ast
import traceback

def find_entry_function(tree):
    \"\"\"Finds the last defined function or Solution method in the learner's code.\"\"\"
    func_name = None
    in_solution_class = False
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "Solution":
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    func_name = item.name
                    in_solution_class = True
        elif isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
            func_name = node.name
            in_solution_class = False
    return func_name, in_solution_class

def main():
    payload = json.loads(sys.stdin.read())
    user_code = payload["user_code"]
    test_input = payload["input"]

    try:
        tree = ast.parse(user_code)
    except SyntaxError as e:
        print(json.dumps({
            "actual_output": None,
            "stderr": f"SyntaxError: {e.msg} at line {e.lineno}"
        }))
        return

    func_name, in_solution_class = find_entry_function(tree)
    if not func_name:
        print(json.dumps({
            "actual_output": None,
            "stderr": "NameError: No callable solution function found in submission."
        }))
        return

    namespace = {}
    try:
        exec(compile(tree, filename="<learner_submission>", mode="exec"), namespace)
        target = namespace["Solution"]() if in_solution_class else namespace[func_name]
        if in_solution_class:
            target = getattr(target, func_name)

        # Unpack input appropriately based on type (dict -> kwargs, list/tuple -> args, or single arg)
        if isinstance(test_input, dict):
            result = target(**test_input)
        elif isinstance(test_input, list) and target.__code__.co_argcount > 1:
            result = target(*test_input)
        else:
            result = target(test_input)

        print(json.dumps({"actual_output": result, "stderr": None}))
    except Exception:
        print(json.dumps({
            "actual_output": None,
            "stderr": traceback.format_exc(limit=3)
        }))

if __name__ == "__main__":
    main()
"""

async def _run_single_test_locally(
    user_code: str,
    test_case: Dict[str, Any],
    timeout_sec: float = 2.5
) -> Dict[str, Any]:
    """Runs a single test case in an isolated child process with a strict timeout."""
    expected = test_case.get("expected_output")
    test_input = test_case.get("input")

    with tempfile.TemporaryDirectory() as tmpdir:
        harness_path = os.path.join(tmpdir, "runner.py")
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(LOCAL_RUNNER_HARNESS)

        # Strip sensitive environment variables (like NEBIUS_API_KEY) from child process
        safe_env = {"PATH": os.environ.get("PATH", ""), "PYTHONIOENCODING": "utf-8"}

        proc = await asyncio.create_subprocess_exec(
            sys.executable, "-I", harness_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tmpdir,
            env=safe_env
        )

        input_payload = json.dumps({
            "user_code": user_code,
            "input": test_input
        }).encode("utf-8")

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_payload),
                timeout=timeout_sec
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return {
                "input": test_input,
                "passed": False,
                "actual_output": None,
                "stderr": f"TimeoutError: Execution exceeded {timeout_sec}s time limit (possible infinite loop or O(N^2) TLE).",
                "timed_out": True
            }

        if stdout:
            try:
                parsed = json.loads(stdout.decode("utf-8").strip().splitlines()[-1])
                actual = parsed.get("actual_output")
                err = parsed.get("stderr")
                passed = (err is None) and (actual == expected)
                return {
                    "input": test_input,
                    "passed": passed,
                    "actual_output": actual,
                    "stderr": err,
                    "timed_out": False
                }
            except json.JSONDecodeError:
                pass

        err_msg = stderr.decode("utf-8").strip() or "RuntimeError: Unexpected output format."
        return {
            "input": test_input,
            "passed": False,
            "actual_output": None,
            "stderr": err_msg,
            "timed_out": False
        }


async def _execute_local_fallback(user_code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Executes all public and hidden test cases using the isolated local subprocess runner."""
    results = []
    any_timeout = False

    for tc in test_cases:
        res = await _run_single_test_locally(user_code, tc)
        if res.pop("timed_out", False):
            any_timeout = True
        results.append(res)

    return {
        "status": "timeout" if any_timeout else "completed",
        "execution_mode": "local_isolated_sandbox",
        "results": results
    }


async def execute_in_sandbox(user_code: str, test_cases: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Primary entry point: Attempts remote Token Factory Sandbox execution if configured,
    and seamlessly falls back to the isolated local subprocess sandbox.
    """
    if SANDBOX_ENDPOINT:
        headers = {
            "Authorization": f"Bearer {NEBIUS_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "language": "python",
            "code": user_code,
            "test_cases": test_cases,
            "timeout": 5.0
        }
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    SANDBOX_ENDPOINT,
                    json=payload,
                    headers=headers,
                    timeout=8.0
                )
                response.raise_for_status()
                data = response.json()
                data["execution_mode"] = "nebius_remote_sandbox"
                return data
        except Exception as e:
            logger.warning(f"Remote sandbox unavailable ({str(e)}). Triggering local isolated fallback.")

    # Seamless fallback to local isolated subprocess execution
    return await _execute_local_fallback(user_code, test_cases)