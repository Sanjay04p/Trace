import json
from app.core.config import nebius_client, FAST_MODEL

async def generate_edge_cases(problem_description: str, category: str) -> list[dict]:
    """
    Uses a fast LLM to generate adversarial edge cases for a specific algorithm problem.
    """
    system_prompt = (
        "You are an expert algorithm tester. Given a problem description and category "
        "(e.g., arrays, sliding windows), generate 3 hidden edge cases. "
        "Include duplicates, empty inputs, boundaries, or adversarial arrays.\n"
        "Return ONLY a valid JSON array of objects with 'input' and 'expected_output' keys. "
        "Do not include markdown blocks or any other text."
    )
    
    try:
        response = await nebius_client.chat.completions.create(
            model=FAST_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Category: {category}\nProblem: {problem_description}"}
            ],
            temperature=0.2, # Low temperature for structured, deterministic JSON output
            max_tokens=500
        )
        
        # Parse the JSON directly from the fast model's response
        raw_output = response.choices[0].message.content.strip()
        test_cases = json.loads(raw_output)
        return test_cases
        
    except json.JSONDecodeError:
        # Fallback in case the model hallucinates formatting
        return []