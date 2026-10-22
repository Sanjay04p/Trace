import { ChatMessage, ImportedProblem, Problem, SwarmEvaluationResponse, Telemetry } from '../types'

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '')

export async function importProblem(query: string): Promise<ImportedProblem> {
  const response = await fetch(`${API_BASE_URL}/api/v1/swarm/import?query=${encodeURIComponent(query)}`, {
    method: 'GET',
    headers: { Accept: 'application/json' },
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as ImportedProblem
}

type EvaluatePayload = {
  problem: Problem
  userCode: string
  hintLevel: number
  previousHints: string[]
}

export async function evaluateSubmission({ problem, userCode, hintLevel, previousHints }: EvaluatePayload) {
  const response = await fetch(`${API_BASE_URL}/api/v1/swarm/evaluate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      problem_id: problem.id,
      problem_title: problem.title,
      problem_description: problem.description,
      category: problem.category,
      user_code: userCode,
      public_test_cases: problem.tests,
      hint_level: hintLevel,
      previous_hints: previousHints,
    }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as SwarmEvaluationResponse
}

export async function sendChat({
  problem,
  userCode,
  diagnosis,
  failedCategory,
  history,
  message,
}: {
  problem: Problem
  userCode: string
  diagnosis?: string | null
  failedCategory?: string | null
  history: ChatMessage[]
  message: string
}): Promise<{ reply: string; telemetry: Telemetry }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/swarm/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    body: JSON.stringify({
      problem_title: problem.title,
      problem_description: problem.description,
      category: problem.category,
      user_code: userCode,
      misconception_diagnosis: diagnosis,
      failed_edge_case_category: failedCategory,
      chat_history: history.map(({ role, content }) => ({ role, content })),
      user_message: message,
    }),
  })
  if (!response.ok) throw new Error(await readError(response))
  return (await response.json()) as { reply: string; telemetry: Telemetry }
}

async function readError(response: Response) {
  try {
    const data = (await response.json()) as { detail?: string }
    return data.detail || `Request failed with status ${response.status}`
  } catch {
    return `Request failed with status ${response.status}`
  }
}
