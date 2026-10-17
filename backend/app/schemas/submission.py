from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class TestCase(BaseModel):
    input: Any
    expected_output: Any
    is_hidden: bool = False

class CodeSubmissionRequest(BaseModel):
    problem_id: str
    problem_title: str
    problem_description: str
    category: str = Field(..., description="e.g., 'Sliding Window', 'Two Pointers', 'Arrays'")
    user_code: str
    public_test_cases: List[TestCase]
    hint_level: int = Field(default=1, ge=1, le=3, description="Progressive hint depth (1=Subtle, 2=Conceptual, 3=Structural)")
    previous_hints: List[str] = Field(default_factory=list)

class TestExecutionResult(BaseModel):
    input: Any
    expected_output: Any
    actual_output: Optional[Any] = None
    passed: bool
    stderr: Optional[str] = None
    is_hidden: bool = False

class RoutingStepLog(BaseModel):
    step: str
    tier: str
    model_used: str
    reason: str
    prompt_tokens: int
    completion_tokens: int

class OrchestrationTelemetry(BaseModel):
    total_tokens: int
    estimated_cost_usd: float
    estimated_savings_percentage: float
    routing_decisions: List[RoutingStepLog]

class SwarmEvaluationResponse(BaseModel):
    all_passed: bool
    execution_status: str
    public_results: List[TestExecutionResult]
    hidden_results_summary: Dict[str, int]
    failed_edge_case_category: Optional[str] = None
    misconception_diagnosis: Optional[str] = None
    progressive_hint: str
    telemetry: OrchestrationTelemetry