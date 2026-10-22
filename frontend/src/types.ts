export type Problem = {
  id: string
  title: string
  category: string
  difficulty: 'EASY' | 'MEDIUM' | 'HARD'
  description: string
  starterCode: string
  tests: TestCase[]
}

export type TestCase = {
  input: unknown
  expected_output: unknown
}

export type TestExecutionResult = TestCase & {
  actual_output?: unknown
  passed: boolean
  stderr?: string | null
  is_hidden?: boolean
}

export type RoutingStepLog = {
  step: string
  tier: string
  model_used: string
  reason: string
  prompt_tokens: number
  completion_tokens: number
}

export type Telemetry = {
  total_tokens: number
  estimated_cost_usd: number
  estimated_savings_percentage: number
  routing_decisions: RoutingStepLog[]
}

export type SwarmEvaluationResponse = {
  all_passed: boolean
  execution_status: string
  public_results: TestExecutionResult[]
  hidden_results_summary: { total: number; passed: number; failed: number }
  failed_edge_case_category?: string | null
  misconception_diagnosis?: string | null
  progressive_hint: string
  telemetry: Telemetry
}

export type ChatMessage = {
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  modelTier?: string
}

export type TelemetryLog = {
  totalTokens: number
  estimatedCostUsd: number
  estimatedSavingsPercentage: number
  routingDecisions: RoutingStepLog[]
}
