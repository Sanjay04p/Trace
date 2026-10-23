import os
import sys
import json
import ast
import asyncio
import tempfile
import logging
import httpx
from typing import List, Dict, Any
from app.core.config import NEBIUS_API_KEY
import subprocess

logger = logging.getLogger(__name__)

# Optional remote sandbox URL. If unset or unreachable, automatically falls back to local isolated runner.
SANDBOX_ENDPOINT = os.getenv("NEBIUS_SANDBOX_URL", "").strip()

# ----------------- LAYER 1: STATIC AST SECURITY GATE -----------------
ALLOWED_MODULES = {
    "math", "collections", "heapq", "bisect", "itertools",
    "functools", "typing", "string", "re", "operator", "copy"
}

FORBIDDEN_CALLS = {
    "eval", "exec", "compile", "open", "__import__", "input",
    "breakpoint", "globals", "locals", "vars", "getattr", "setattr",
    "delattr", "memoryview", "help", "exit", "quit"
}

FORBIDDEN_ATTRIBUTES = {
    "__builtins__", "__globals__", "__subclasses__", "__bases__",
    "__mro__", "__class__", "__code__", "__closure__", "__func__",
    "__self__", "__module__", "__dict__", "__import__", "__loader__", "__spec__"
}

class SecurityViolationError(Exception):
    """Raised when user code contains forbidden imports, calls, or introspection."""
    pass

def validate_user_code_ast(user_code: str) -> None:
    """
    Statically analyzes user code before execution.
    Blocks forbidden imports, dangerous built-in invocations, and Python escape dunder chains.
    """
    try:
        tree = ast.parse(user_code)
    except SyntaxError:
        # Let SyntaxErrors be handled gracefully during normal compilation
        return

    for node in ast.walk(tree):
        # 1. Reject forbidden `import x`
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_mod = alias.name.split(".")[0]
                if root_mod not in ALLOWED_MODULES:
                    raise SecurityViolationError(
                        f"Security Violation: Import of module '{alias.name}' is prohibited in the sandbox."
                    )

        # 2. Reject forbidden `from x import y`
        elif isinstance(node, ast.ImportFrom):
            root_mod = (node.module or "").split(".")[0]
            if root_mod not in ALLOWED_MODULES:
                raise SecurityViolationError(
                    f"Security Violation: Import from '{node.module}' is prohibited in the sandbox."
                )

        # 3. Reject forbidden function calls like open(), eval(), exec(), getattr()
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise SecurityViolationError(
                    f"Security Violation: Built-in function '{node.func.id}()' is disabled."
                )

        # 4. Reject forbidden dunder attribute access (e.g., ().__class__.__bases__)
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRIBUTES:
                raise SecurityViolationError(
                    f"Security Violation: Access to attribute '{node.attr}' is prohibited."
                )

        # 5. Reject forbidden identifiers directly
        elif isinstance(node, ast.Name):
            if node.id in FORBIDDEN_ATTRIBUTES:
                raise SecurityViolationError(
                    f"Security Violation: Identifier '{node.id}' is prohibited in the sandbox."
                )

# ----------------- LAYER 2 & 3: ISOLATED HARNESS SCRIPT -----------------
LOCAL_RUNNER_HARNESS = """
import sys
import json
import ast
import traceback
import math
import collections
import heapq
import bisect
import itertools
import functools
import typing
import string
import re
import operator
import copy

# OS-level resource limits on Linux environments (prevents RAM/CPU exhaustion and fork bombs)
try:
    import resource
    MEM_LIMIT = 128 * 1024 * 1024  # 128 MB RAM max
    resource.setrlimit(resource.RLIMIT_AS, (MEM_LIMIT, MEM_LIMIT))
    resource.setrlimit(resource.RLIMIT_CPU, (3, 3))  # 3 seconds max CPU time
    resource.setrlimit(resource.RLIMIT_NPROC, (0, 0)) # Disallow spawning processes
except Exception:
    pass

class ListNode:
    def __init__(self, val=0, next=None):
        self.val = val
        self.next = next

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

ALLOWED_MODULES = {
    "math": math, "collections": collections, "heapq": heapq,
    "bisect": bisect, "itertools": itertools, "functools": functools,
    "typing": typing, "string": string, "re": re, "operator": operator,
    "copy": copy
}

def _safe_import(name, globals=None, locals=None, fromlist=(), level=0):
    root = name.split(".")[0]
    if root in ALLOWED_MODULES:
        return ALLOWED_MODULES[root]
    raise ImportError(f"Module '{name}' is blocked by sandbox security policy.")

def build_safe_builtins():
    raw_builtins = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
    safe = dict(raw_builtins)
    for blocked in (
        "open", "eval", "exec", "compile", "input", "breakpoint",
        "globals", "locals", "vars", "getattr", "setattr", "delattr",
        "memoryview", "help", "exit", "quit"
    ):
        safe.pop(blocked, None)
    safe["__import__"] = _safe_import
    return safe

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

    namespace = {
        "__builtins__": build_safe_builtins(),
        "ListNode": ListNode,
        "TreeNode": TreeNode,
        "math": math,
        "collections": collections,
        "heapq": heapq,
        "bisect": bisect,
        "itertools": itertools,
        "functools": functools,
        "typing": typing,
        "List": typing.List,
        "Dict": typing.Dict,
        "Set": typing.Set,
        "Tuple": typing.Tuple,
        "Optional": typing.Optional,
        "deque": collections.deque,
        "defaultdict": collections.defaultdict,
        "Counter": collections.Counter,
    }

    try:
        compiled_code = compile(tree, filename="<learner_submission>", mode="exec")
        exec(compiled_code, namespace)
        
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
    """Runs a single test case in an isolated child process using a non-blocking thread (Windows & Linux safe)."""
    expected = test_case.get("expected_output")
    test_input = test_case.get("input")

    with tempfile.TemporaryDirectory() as tmpdir:
        harness_path = os.path.join(tmpdir, "runner.py")
        with open(harness_path, "w", encoding="utf-8") as f:
            f.write(LOCAL_RUNNER_HARNESS)

        # Stripped environment dictionary: strictly prevents NEBIUS_API_KEY from entering process memory
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),  # Required on Windows to initialize Python
            "PYTHONIOENCODING": "utf-8",
            "PYTHONDONTWRITEBYTECODE": "1",
            "PYTHONNOUSERSITE": "1"
        }

        input_payload = json.dumps({
            "user_code": user_code,
            "input": test_input
        }).encode("utf-8")

        try:
            completed_proc = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, "-I", harness_path],
                input=input_payload,
                capture_output=True,
                cwd=tmpdir,
                env=safe_env,
                timeout=timeout_sec
            )
            stdout = completed_proc.stdout
            stderr = completed_proc.stderr

        except subprocess.TimeoutExpired:
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
    # Run AST check before launching subprocesses
    try:
        validate_user_code_ast(user_code)
    except SecurityViolationError as sec_err:
        return {
            "status": "security_violation",
            "execution_mode": "local_isolated_sandbox",
            "results": [
                {
                    "input": tc.get("input"),
                    "passed": False,
                    "actual_output": None,
                    "stderr": str(sec_err)
                }
                for tc in test_cases
            ]
        }

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