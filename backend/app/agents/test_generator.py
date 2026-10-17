import json
from app.agents.router import SwarmOrchestrator

async def generate_edge_cases(
    problem_description: str,
    category: str,
    orchestrator: SwarmOrchestrator
) -> list[dict]:
    decision = orchestrator.select_model(step="edge_case_generation")
    
    system_prompt = (
        "You are an expert algorithm tester. Given a problem description and category "
        "(e.g., arrays, sliding windows), generate 3 hidden edge cases. "
        "Include duplicates, empty inputs, boundaries, or adversarial arrays.\n"
        "Return ONLY a valid JSON array of objects with 'input' and 'expected_output' keys. "
        "Do not include markdown blocks or any other text."
    )
    
    try:
        raw_output = await orchestrator.execute_llm_call(
            decision=decision,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Category: {category}\nProblem: {problem_description}"}
            ],
            temperature=0.2,
            max_tokens=500
        )
        if raw_output.startswith("```"):
            raw_output = raw_output.strip("`").removeprefix("json").strip()
        return json.loads(raw_output)
    except Exception:
        return []