import json
import re
import logging
from typing import List, Dict, Any
from app.agents.router import SwarmOrchestrator

logger = logging.getLogger(__name__)

def _extract_json_array(raw_text: str) -> List[Dict[str, Any]]:
    """Strips <think> reasoning blocks, markdown fences, and extracts the JSON list."""
    # 1. Remove <think>...</think> blocks produced by Nemotron reasoning models
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_text, flags=re.IGNORECASE).strip()
    
    # If the <think> tag was unclosed due to token limits, strip everything before the last '['
    if "<think>" in cleaned.lower():
        cleaned = cleaned.split("</think>")[-1].strip()

    # 2. Extract the JSON array between the first '[' and last ']'
    start_idx = cleaned.find("[")
    end_idx = cleaned.rfind("]")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        json_candidate = cleaned[start_idx : end_idx + 1]
        data = json.loads(json_candidate)
        if isinstance(data, list):
            return data

    # 3. Fallback: check if the model returned a dict wrapping the list (e.g. {"test_cases": [...]})
    start_brace = cleaned.find("{")
    end_brace = cleaned.rfind("}")
    if start_brace != -1 and end_brace != -1 and end_brace > start_brace:
        obj = json.loads(cleaned[start_brace : end_brace + 1])
        if isinstance(obj, dict):
            for val in obj.values():
                if isinstance(val, list):
                    return val

    return []


async def generate_edge_cases(
    problem_description: str,
    category: str,
    sample_public_cases: List[Dict[str, Any]],
    orchestrator: SwarmOrchestrator
) -> List[Dict[str, Any]]:
    decision = orchestrator.select_model(step="edge_case_generation")

    sample_format_str = json.dumps(sample_public_cases[:1], indent=2) if sample_public_cases else '[{"input": ..., "expected_output": ...}]'

    system_prompt = (
        "You are an expert algorithm tester. Generate 3 hidden edge cases (duplicates, boundaries, negative numbers, or minimal length inputs)[cite: 1].\n"
        "CRITICAL RULES:\n"
        "1. Keep any internal thinking brief.\n"
        "2. The 'input' and 'expected_output' structure MUST strictly match the data types and keys of the sample test case.\n"
        "3. Return ONLY a valid JSON array of 3 objects with 'input' and 'expected_output' keys."
    )

    user_prompt = (
        f"Category: {category}\n"
        f"Problem: {problem_description}\n\n"
        f"Match this exact JSON schema for each test case:\n{sample_format_str}"
    )

    try:
        raw_output = await orchestrator.execute_llm_call(
            decision=decision,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.2,
            max_tokens=1500  # Crucial for Nemotron-3-Nano reasoning + JSON completion
        )

        parsed_cases = _extract_json_array(raw_output)
        valid_cases = [
            tc for tc in parsed_cases
            if isinstance(tc, dict) and "input" in tc and "expected_output" in tc
        ]
        logger.info(f"Generated {len(valid_cases)} valid hidden edge cases.")
        return valid_cases

    except Exception as e:
        logger.error(f"Failed to parse generated edge cases: {e} | Raw output: {raw_output[:300]}")
        return []