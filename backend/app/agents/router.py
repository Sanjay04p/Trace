from typing import Dict, Any, List, Tuple
from app.core.config import nebius_client, MODEL_TIERS, MODEL_PRICING_PER_1M

class OrchestrationDecision:
    def __init__(self, step: str, tier: str, model_id: str, reason: str):
        self.step = step
        self.tier = tier
        self.model_id = model_id
        self.reason = reason

class SwarmOrchestrator:
    """
    Intelligent Model Router & Token Optimization Tracker for AlgoMentor Swarm.
    Routes tasks across NVIDIA Nemotron tiers based on task complexity and sandbox failure signals.
    """
    def __init__(self):
        self.routing_log: List[Dict[str, Any]] = []
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.actual_cost_usd = 0.0
        self.baseline_ultra_cost_usd = 0.0

    @staticmethod
    def _has_simple_syntax_or_name_error(failed_tests: List[Dict[str, Any]]) -> bool:
        """Checks if failures are purely syntax/typo errors that don't need a 120B+ model."""
        simple_errors = ("SyntaxError", "IndentationError", "TabError", "NameError", "TypeError")
        for test in failed_tests:
            stderr = test.get("stderr") or ""
            if any(err in stderr for err in simple_errors):
                return True
        return False

    @staticmethod
    def _has_timeout_or_tle(failed_tests: List[Dict[str, Any]], execution_status: str) -> bool:
        """Checks if the learner wrote an infinite two-pointer loop or O(N^2) TLE."""
        if execution_status == "timeout":
            return True
        for test in failed_tests:
            stderr = (test.get("stderr") or "").lower()
            if "timeout" in stderr or "time limit" in stderr:
                return True
        return False

    def select_model(
        self,
        step: str,
        failed_tests: List[Dict[str, Any]] = None,
        hint_level: int = 1,
        execution_status: str = "completed"
    ) -> OrchestrationDecision:
        failed_tests = failed_tests or []

        # 1. Edge Case Generation -> Always NANO (Fast structured JSON generation)
        if step == "edge_case_generation":
            return OrchestrationDecision(
                step=step,
                tier="NANO",
                model_id=MODEL_TIERS["NANO"],
                reason="Structured JSON adversarial test generation routed to low-latency Nemotron Nano."
            )

        # 2. Misconception Diagnosis -> Dynamic based on failure complexity
        if step == "misconception_diagnosis":
            if self._has_simple_syntax_or_name_error(failed_tests):
                return OrchestrationDecision(
                    step=step,
                    tier="NANO",
                    model_id=MODEL_TIERS["NANO"],
                    reason="Detected syntax/runtime typo in stderr; bypassed heavy reasoning in favor of Nemotron Nano."
                )
            if self._has_timeout_or_tle(failed_tests, execution_status) or hint_level >= 3:
                return OrchestrationDecision(
                    step=step,
                    tier="ULTRA",
                    model_id=MODEL_TIERS["ULTRA"],
                    reason="Detected infinite loop/time-complexity bottleneck or repeated learner struggle; escalated to Nemotron Ultra."
                )
            return OrchestrationDecision(
                step=step,
                tier="SUPER",
                model_id=MODEL_TIERS["SUPER"],
                reason="Hidden edge-case logic failure detected; routed to Nemotron Super for deep algorithmic diagnosis."
            )

        # 3. Progressive Socratic Hint -> Scales with learner's requested hint_level
        if step == "progressive_hint":
            if hint_level == 1:
                return OrchestrationDecision(
                    step=step,
                    tier="NANO",
                    model_id=MODEL_TIERS["NANO"],
                    reason="Level 1 subtle Socratic question generated via fast Nemotron Nano."
                )
            elif hint_level == 2:
                return OrchestrationDecision(
                    step=step,
                    tier="SUPER",
                    model_id=MODEL_TIERS["SUPER"],
                    reason="Level 2 invariant guidance routed to Nemotron Super."
                )
            else:
                return OrchestrationDecision(
                    step=step,
                    tier="ULTRA",
                    model_id=MODEL_TIERS["ULTRA"],
                    reason="Level 3 structural state-trace walkthrough escalated to Nemotron Ultra."
                )

        # Default fallback
        return OrchestrationDecision(
            step=step,
            tier="SUPER",
            model_id=MODEL_TIERS["SUPER"],
            reason="Default balanced routing."
        )

    async def execute_llm_call(
        self,
        decision: OrchestrationDecision,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 400
    ) -> str:
        """Executes the Nebius Token Factory call and records token & cost telemetry."""
        response = await nebius_client.chat.completions.create(
            model=decision.model_id,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens
        )

        usage = response.usage
        p_tokens = usage.prompt_tokens if usage else 0
        c_tokens = usage.completion_tokens if usage else 0

        self.total_prompt_tokens += p_tokens
        self.total_completion_tokens += c_tokens

        # Calculate actual cost vs. running everything on ULTRA
        pricing = MODEL_PRICING_PER_1M.get(decision.model_id, {"input": 0.30, "output": 0.90})
        ultra_pricing = MODEL_PRICING_PER_1M[MODEL_TIERS["ULTRA"]]

        step_cost = (p_tokens / 1_000_000) * pricing["input"] + (c_tokens / 1_000_000) * pricing["output"]
        ultra_cost = (p_tokens / 1_000_000) * ultra_pricing["input"] + (c_tokens / 1_000_000) * ultra_pricing["output"]

        self.actual_cost_usd += step_cost
        self.baseline_ultra_cost_usd += ultra_cost

        self.routing_log.append({
            "step": decision.step,
            "tier": decision.tier,
            "model_used": decision.model_id,
            "reason": decision.reason,
            "prompt_tokens": p_tokens,
            "completion_tokens": c_tokens,
        })

        return response.choices[0].message.content.strip()

    def get_telemetry_summary(self) -> Dict[str, Any]:
        savings_pct = 0.0
        if self.baseline_ultra_cost_usd > 0:
            savings_pct = round(
                ((self.baseline_ultra_cost_usd - self.actual_cost_usd) / self.baseline_ultra_cost_usd) * 100, 1
            )
        return {
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "estimated_cost_usd": round(self.actual_cost_usd, 6),
            "estimated_savings_percentage": max(0.0, savings_pct),
            "routing_decisions": self.routing_log
        }