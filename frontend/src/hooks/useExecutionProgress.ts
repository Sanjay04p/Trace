import { useEffect, useState } from 'react'

export const EXECUTION_STAGES = [
  'Initializing Token Factory Sandbox...',
  'Routing to Nemotron Nano: Generating adversarial edge cases...',
  'Executing learner code across public & hidden test suite...',
  'Routing to Nemotron Super: Analyzing execution failure traces...',
  'Synthesizing Socratic mentor response...',
] as const

export function useExecutionProgress(isEvaluating: boolean) {
  const [stageIndex, setStageIndex] = useState(0)

  useEffect(() => {
    if (!isEvaluating) {
      setStageIndex(0)
      return
    }

    setStageIndex(0)
    const timer = window.setInterval(() => {
      setStageIndex((current) => (current + 1) % EXECUTION_STAGES.length)
    }, 1800)

    return () => window.clearInterval(timer)
  }, [isEvaluating])

  return isEvaluating ? EXECUTION_STAGES[stageIndex] : 'Idle'
}
