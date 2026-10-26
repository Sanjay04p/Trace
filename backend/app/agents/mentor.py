from typing import List,Dict, Any, Optional
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

async def answer_followup_question(
    problem_title: str,
    problem_description: str,
    category: str,
    user_code: str,
    diagnosis: Optional[str],
    failed_category: Optional[str],
    chat_history: List[Dict[str, str]],
    user_message: str,
    orchestrator: SwarmOrchestrator
) -> str:
    """
    Handles multi-turn Socratic follow-up questions using the current session context
    (learner's code, sandbox diagnosis, and prior chat history) without spoiling the solution.
    """
    # Escalate to SUPER if the conversation is deep (>= 4 messages) or asks conceptual "why/invariant/complexity" questions
    deep_keywords = ("why", "invariant", "complexity", "walkthrough", "trace", "understand", "stuck")
    is_deep_query = len(chat_history) >= 4 or any(k in user_message.lower() for k in deep_keywords)
    effective_level = 3 if is_deep_query else 1

    decision = orchestrator.select_model(
        step="followup_chat",
        hint_level=effective_level
    )

    system_prompt = (
    "You are AlgoMentor, an interactive Socratic coding coach for algorithms and data structures.\n"
    "You are in an active mentoring session helping a learner debug their Python code.\n"
    "STRICT GUARDRAILS:\n"
    "- NEVER write the complete corrected Python solution or hand over copy-pasteable code fixes.\n"
    "- NEVER reveal exact hidden test case inputs.\n"
    "- STRICT SCOPE ENFORCEMENT: You MUST NOT answer any general knowledge questions, math queries (e.g., 'What is 1+1?'), or off-topic chat. If the user asks an unrelated question, immediately refuse by replying EXACTLY with: 'I am a Socratic Code Mentor. I can only assist you with diagnosing your code and explaining algorithmic concepts. Let's get back to your code.'\n"
    "- Answer the learner's follow-up question directly, clearly, and encouragingly using tiny conceptual examples or pointer traces.\n"
    "- End your reply with a brief check-in question that nudges them toward editing and re-running their code.\n"
    "- Keep your response concise (2 to 5 sentences)."
    )

    context_header = (
        f"Problem: {problem_title} ({category})\n"
        f"Description: {problem_description}\n\n"
        f"Learner's Current Code:\n```python\n{user_code}\n```\n\n"
        f"Latest Sandbox Diagnosis: {diagnosis or 'Not yet diagnosed'}\n"
        f"Failure Category: {failed_category or 'N/A'}\n"
    )

    messages: List[Dict[str, str]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"SESSION CONTEXT:\n{context_header}"}
    ]

    # Append recent session chat history (last 8 turns to keep token usage lean)
    for msg in chat_history[-8:]:
        role = "assistant" if msg.get("role") == "assistant" else "user"
        messages.append({"role": role, "content": msg.get("content", "")})

    messages.append({"role": "user", "content": user_message})

    return await orchestrator.execute_llm_call(
        decision=decision,
        messages=messages,
        temperature=0.4,
        max_tokens=1200
    )