from typing import List
from app.agents.router import SwarmOrchestrator
import re

HINT_DEPTH_GUIDELINES = {
    1: "Level 1 (Subtle Socratic Question): Ask a short, thought-provoking question about their pointers, window, or state under boundary conditions without naming the exact line of code.",
    2: "Level 2 (Conceptual Nudge): Point out the specific invariant being violated and ask how they might adjust their state transition.",
    3: "Level 3 (Structural Walkthrough): Walk through a tiny abstract trace showing where their current logic diverges from the expected state."
}

async def generate_progressive_hint(
    problem_description: str,
    category: str,
    user_code: str,
    diagnosis: str,
    failed_category: str,
    hint_level: int,
    previous_hints: List[str],
    orchestrator: SwarmOrchestrator
) -> str:
    decision = orchestrator.select_model(
        step="progressive_hint",
        hint_level=hint_level
    )
    depth_instruction = HINT_DEPTH_GUIDELINES.get(hint_level, HINT_DEPTH_GUIDELINES[1])

    system_prompt = (
        "You are AlgoMentor, a Socratic coding coach.\n"
        "- NEVER write Python code snippets or reveal the solution.\n"
        "- NEVER reveal exact hidden test case inputs.\n"
        f"- Follow this depth instruction: {depth_instruction}\n"
        "- Keep your response concise (2 to 4 sentences maximum)."
    )

    user_prompt = (
        f"Algorithm Category: {category}\nProblem Summary: {problem_description}\n"
        f"Diagnosed Misconception: {diagnosis}\nFailure Trigger Type: {failed_category}\n"
        f"Previous Hints Given: {previous_hints}\n\nGenerate the progressive hint now:"
    )

    raw_content = await orchestrator.execute_llm_call(
        decision=decision,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.4,
        max_tokens=1200
    )

    # Strip <think>...</think> reasoning blocks before returning the hint
    clean_content = re.sub(r"<think>[\s\S]*?</think>", "", raw_content, flags=re.IGNORECASE).strip()
    if "<think>" in clean_content.lower():
        clean_content = clean_content.split("</think>")[-1].strip()

    return clean_content