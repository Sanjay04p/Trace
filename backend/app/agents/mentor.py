from typing import List
from app.core.config import nebius_client, PRIMARY_MODEL

HINT_DEPTH_GUIDELINES = {
    1: "Level 1 (Subtle Socratic Question): Ask a short, thought-provoking question about what happens to their pointers, window, or state under a specific condition (like duplicates or boundary indices) without naming the exact line of code.",
    2: "Level 2 (Conceptual Nudge): Point out the specific invariant being violated (e.g., how the sliding window condition or hash map state gets out of sync) and ask how they might adjust their state transition.",
    3: "Level 3 (Structural Walkthrough): Walk through a tiny abstract trace showing where their current logic diverges from the expected state, and ask them to modify that specific condition."
}

async def generate_progressive_hint(
    problem_description: str,
    category: str,
    user_code: str,
    diagnosis: str,
    failed_category: str,
    hint_level: int = 1,
    previous_hints: List[str] = []
) -> str:
    """
    Step 5: Translates the technical diagnosis into a progressive Socratic hint
    without revealing the code solution.
    """
    depth_instruction = HINT_DEPTH_GUIDELINES.get(hint_level, HINT_DEPTH_GUIDELINES[1])

    system_prompt = (
        "You are AlgoMentor, a Socratic coding coach for data structures and algorithms.\n"
        "STRICT GUARDRAILS:\n"
        "- NEVER write Python code snippets or give away the solution.\n"
        "- NEVER reveal the exact hidden test case array values.\n"
        "- Guide the learner by asking a targeted question based on the diagnosed misconception.\n"
        f"- Follow this hint depth instruction: {depth_instruction}\n"
        "- Keep your response concise (2 to 4 sentences maximum)."
    )

    user_prompt = (
        f"Algorithm Category: {category}\n"
        f"Problem Summary: {problem_description}\n"
        f"Diagnosed Misconception: {diagnosis}\n"
        f"Failure Trigger Type: {failed_category}\n"
        f"Previous Hints Given (do not repeat these): {previous_hints}\n\n"
        "Generate the progressive hint for the learner now:"
    )

    response = await nebius_client.chat.completions.create(
        model=PRIMARY_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
        max_tokens=250
    )

    return response.choices[0].message.content.strip()