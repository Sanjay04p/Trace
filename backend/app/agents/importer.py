import json
import re
from typing import Dict, Any
from app.agents.router import SwarmOrchestrator
from app.core.config import MODEL_TIERS

async def import_leetcode_problem(query: str, orchestrator: SwarmOrchestrator) -> Dict[str, Any]:
    """Uses Nemotron Nano to instantly fetch problem details and format them into our sandbox schema."""
    decision = orchestrator.select_model(step="problem_import", hint_level=1)
    
    system_prompt = (
        "You are a competitive programming database. Given a problem identifier (e.g., 'LC 2' or 'Two Sum'), "
        "return its details in strict JSON format. Include standard public test cases.\n"
        "EXPECTED JSON SCHEMA:\n"
        "{\n"
        '  "title": "Problem Name",\n'
        '  "category": "e.g., Two Pointers, Linked List, DP",\n'
        '  "description": "Full problem description...",\n'
        '  "public_test_cases": [{"input": {"nums": [2,7], "target": 9}, "expected_output": [0,1]}]\n'
        "}\n"
        "CRITICAL: Return ONLY valid JSON. Keep internal thinking brief."
    )

    try:
        raw_output = await orchestrator.execute_llm_call(
            decision=decision,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Lookup: {query}"}
            ],
            temperature=0.1,
            max_tokens=1500
        )

        # Strip think tags and markdown
        cleaned = re.sub(r"<think>[\s\S]*?</think>", "", raw_output, flags=re.IGNORECASE).strip()
        if "<think>" in cleaned.lower():
            cleaned = cleaned.split("</think>")[-1].strip()
        
        start_idx = cleaned.find("{")
        end_idx = cleaned.rfind("}")
        
        if start_idx != -1 and end_idx != -1:
            json_str = cleaned[start_idx : end_idx + 1]
            return json.loads(json_str)
            
        return {}
    except Exception as e:
        print(f"Import failed: {e}")
        return {}