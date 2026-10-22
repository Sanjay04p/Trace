import json
from typing import List, Dict, Any
from app.agents.router import SwarmOrchestrator
import re

async def diagnose_misconception(
    problem_description: str,
    category: str,
    user_code: str,
    failed_tests: List[Dict[str, Any]],
    hint_level: int,
    execution_status: str,
    orchestrator: SwarmOrchestrator
) -> Dict[str, str]:
    decision = orchestrator.select_model(
        step="misconception_diagnosis",
        failed_tests=failed_tests,
        hint_level=hint_level,
        execution_status=execution_status
    )

    system_prompt = (
        "You are an expert Computer Science Pedagogical Diagnostician.\n"
        "Identify the exact algorithmic or boundary misconception causing the sandbox failure. "
        "CRITICAL RULE: Do NOT write corrected code.\n"
        "Return ONLY valid JSON with two keys: 'failed_edge_case_category' and 'diagnosis'."
    )

    user_payload = (
        f"Category: {category}\nProblem: {problem_description}\n\n"
        f"Learner Code:\n```python\n{user_code}\n```\n\n"
        f"Observed Sandbox Failures:\n{json.dumps(failed_tests, indent=2)}"
    )

    try:
        raw_content = await orchestrator.execute_llm_call(
            decision=decision,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_payload}
            ],
            temperature=0.2,
            max_tokens=1200
        )
        
        # BONUS TIP ADDED HERE: Strip <think> tags before parsing
        # This removes everything between <think> and </think> (case-insensitive)
        raw_content = re.sub(r"<think>[\s\S]*?</think>", "", raw_content, flags=re.IGNORECASE).strip()
        
        # Also handle edge cases where the token limit cut off the closing </think> tag
        if "<think>" in raw_content.lower():
            raw_content = raw_content.split("</think>")[-1].strip()

        if raw_content.startswith("```"):
            raw_content = raw_content.strip("`").removeprefix("json").strip()
            
        return json.loads(raw_content)
        
    except Exception as e:
        return {
            "failed_edge_case_category": "Logic / Runtime Error",
            "diagnosis": f"Code failed on edge-case execution: {str(e)}"
        }