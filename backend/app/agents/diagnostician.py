import json
from typing import List, Dict, Any
from app.core.config import nebius_client, PRIMARY_MODEL

async def diagnose_misconception(
    problem_description: str,
    category: str,
    user_code: str,
    failed_tests: List[Dict[str, Any]]
) -> Dict[str, str]:
    """
    Step 4: Uses NVIDIA Nemotron to reason from the learner's code and observed
    sandbox failures to diagnose the underlying algorithmic misconception.
    """
    system_prompt = (
        "You are an expert Computer Science Pedagogical Diagnostician.\n"
        "You are given an algorithmic problem, its pattern category, the learner's Python code, "
        "and the exact test cases (including hidden adversarial edge cases) where their code failed in the sandbox.\n\n"
        "Your task is to:\n"
        "1. Identify the exact algorithmic or boundary misconception causing the failure "
        "(e.g., 'Window fails to shrink when duplicate characters appear consecutively', "
        "'Two-pointer loop terminates one index early on even-length arrays', or 'Time Limit Exceeded due to O(N^2) nested slicing').\n"
        "2. Classify the failure trigger (e.g., 'Empty/Single-Element Input', 'Duplicate Values', 'Boundary Off-By-One', 'Suboptimal Time Complexity').\n\n"
        "CRITICAL RULE: Do NOT write corrected code. Focus purely on diagnosing the mental model flaw.\n"
        "Return ONLY valid JSON with two keys: 'failed_edge_case_category' and 'diagnosis'."
    )

    user_payload = (
        f"Category: {category}\n"
        f"Problem: {problem_description}\n\n"
        f"Learner Code:\n```python\n{user_code}\n```\n\n"
        f"Observed Sandbox Failures:\n{json.dumps(failed_tests, indent=2)}"
    )

    try:
        response = await nebius_client.chat.completions.create(
            model=PRIMARY_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ],
            temperature=0.2,
            max_tokens=400
        )
        raw_content = response.choices[0].message.content.strip()
        # Strip markdown fences if the model wraps the JSON
        if raw_content.startswith("```"):
            raw_content = raw_content.strip("`").removeprefix("json").strip()
        return json.loads(raw_content)
    except Exception as e:
        return {
            "failed_edge_case_category": "Logic / Runtime Error",
            "diagnosis": f"Code failed on edge-case execution. Trace analysis fallback: {str(e)}"
        }