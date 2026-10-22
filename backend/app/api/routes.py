from fastapi import APIRouter, HTTPException
from app.schemas.submission import (
    CodeSubmissionRequest,
    SwarmEvaluationResponse,
    TestExecutionResult
)
from app.agents.router import SwarmOrchestrator
from app.agents.test_generator import generate_edge_cases
from app.services.sandbox import execute_in_sandbox
from app.agents.diagnostician import diagnose_misconception
from app.agents.mentor import generate_progressive_hint

router = APIRouter(prefix="/api/v1/swarm", tags=["AlgoMentor Swarm"])

@router.post("/evaluate", response_model=SwarmEvaluationResponse)
async def evaluate_submission(payload: CodeSubmissionRequest):
    """
    Full Agentic Pipeline with Intelligent NVIDIA Model Routing:
    1. Instantiates a request-scoped SwarmOrchestrator for routing & token telemetry.
    2. Generates adversarial hidden edge cases via Nemotron Nano[cite: 1].
    3. Executes both public + hidden test cases in the Token Factory Sandbox[cite: 1].
    4. Dynamically routes misconception diagnosis (Nano / Super / Ultra) based on failure traces[cite: 1].
    5. Dynamically routes Socratic hint generation based on learner hint_level[cite: 1].
    """
    # Initialize the intelligent router and token telemetry tracker for this request
    orchestrator = SwarmOrchestrator()

    public_tests_dicts = [
        {"input": tc.input, "expected_output": tc.expected_output, "is_hidden": False}
        for tc in payload.public_test_cases
    ]
    # Step 3 (Prep): Generate hidden adversarial edge cases dynamically (Routed to NANO)
    generated_hidden_raw = await generate_edge_cases(
        problem_description=payload.problem_description,
        category=payload.category,
        sample_public_cases=public_tests_dicts,
        orchestrator=orchestrator
    )

    # Combine public and hidden test cases for a single sandbox execution batch
    combined_tests = list(public_tests_dicts)
    for h_tc in generated_hidden_raw:
        combined_tests.append({
            "input": h_tc["input"],
            "expected_output": h_tc["expected_output"],
            "is_hidden": True
        })

    # Step 2: Execute learner code in the Token Factory Sandbox
    sandbox_response = await execute_in_sandbox(
        user_code=payload.user_code,
        test_cases=combined_tests
    )

    execution_status = sandbox_response.get("status", "completed")
    if execution_status in ["api_error", "internal_error"]:
        raise HTTPException(
            status_code=502,
            detail=f"Sandbox execution failed: {sandbox_response.get('error')}"
        )

    raw_results = sandbox_response.get("results", [])
    public_results = []
    hidden_passed = 0
    hidden_failed = 0
    failed_cases_for_diagnosis = []

    for idx, res in enumerate(raw_results):
        test_meta = combined_tests[idx] if idx < len(combined_tests) else {"input": None, "expected_output": None, "is_hidden": False}
        is_hidden = test_meta.get("is_hidden", False)
        passed = res.get("passed", False)

        if is_hidden:
            if passed:
                hidden_passed += 1
            else:
                hidden_failed += 1
        else:
            public_results.append(
                TestExecutionResult(
                    input=test_meta["input"],
                    expected_output=test_meta["expected_output"],
                    actual_output=res.get("actual_output"),
                    passed=passed,
                    stderr=res.get("stderr"),
                    is_hidden=False
                )
            )

        if not passed:
            failed_cases_for_diagnosis.append({
                "input": test_meta["input"],
                "expected_output": test_meta["expected_output"],
                "actual_output": res.get("actual_output"),
                "stderr": res.get("stderr"),
                "is_hidden_edge_case": is_hidden
            })

    all_passed = len(failed_cases_for_diagnosis) == 0

    # Fast-path if all public AND adversarial hidden cases pass (Zero extra LLM calls for Steps 4 & 5!)
    if all_passed:
        return SwarmEvaluationResponse(
            all_passed=True,
            execution_status=execution_status,
            public_results=public_results,
            hidden_results_summary={
                "total": hidden_passed + hidden_failed,
                "passed": hidden_passed,
                "failed": hidden_failed
            },
            failed_edge_case_category=None,
            misconception_diagnosis="Optimal execution across all public and adversarial boundary cases.",
            progressive_hint="Spot on! Your solution handled both the standard inputs and our hidden adversarial edge cases. Can you analyze the time and space complexity of your approach?",
            telemetry=orchestrator.get_telemetry_summary()
        )

    # Step 4: Diagnose the misconception (Dynamically routed to NANO, SUPER, or ULTRA)
    diagnosis_data = await diagnose_misconception(
        problem_description=payload.problem_description,
        category=payload.category,
        user_code=payload.user_code,
        failed_tests=failed_cases_for_diagnosis,
        hint_level=payload.hint_level,
        execution_status=execution_status,
        orchestrator=orchestrator
    )

    failed_category = diagnosis_data.get("failed_edge_case_category", "Edge Case Failure")
    diagnosis_text = diagnosis_data.get("diagnosis", "Logical discrepancy detected on boundary inputs.")

    # Step 5: Generate the progressive Socratic hint (Dynamically routed by hint_level)
    hint = await generate_progressive_hint(
        problem_description=payload.problem_description,
        category=payload.category,
        user_code=payload.user_code,
        diagnosis=diagnosis_text,
        failed_category=failed_category,
        hint_level=payload.hint_level,
        previous_hints=payload.previous_hints,
        orchestrator=orchestrator
    )

    return SwarmEvaluationResponse(
        all_passed=False,
        execution_status=execution_status,
        public_results=public_results,
        hidden_results_summary={
            "total": hidden_passed + hidden_failed,
            "passed": hidden_passed,
            "failed": hidden_failed
        },
        failed_edge_case_category=failed_category,
        misconception_diagnosis=diagnosis_text,
        progressive_hint=hint,
        telemetry=orchestrator.get_telemetry_summary()
    )