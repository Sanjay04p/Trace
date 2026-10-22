import { FormEvent, KeyboardEvent, UIEvent, useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  Check,
  ChevronDown,
  CircleHelp,
  Code2,
  Command,
  Gauge,
  GitBranch,
  MessageSquareText,
  PanelLeftClose,
  PanelLeftOpen,
  Pencil,
  Play,
  Plus,
  Send,
  ShieldCheck,
  Sparkles,
  TerminalSquare,
  X,
  Zap,
} from 'lucide-react'
import { problems } from './data/problems'
import CustomProblemForm from './components/CustomProblemForm'
import { useSessionState } from './hooks/useSessionState'
import { evaluateSubmission, sendChat } from './lib/api'
import { ChatMessage, Problem, SwarmEvaluationResponse, TelemetryLog } from './types'

const EMPTY_TELEMETRY: TelemetryLog = {
  totalTokens: 0,
  estimatedCostUsd: 0,
  estimatedSavingsPercentage: 0,
  routingDecisions: [],
}

function App() {
  const [selectedProblemId, setSelectedProblemId] = useSessionState('trace:selectedProblemId', problems[0].id)
  const [codeByProblem, setCodeByProblem] = useSessionState<Record<string, string>>('trace:codeByProblem', {})
  const [hintLevelByProblem, setHintLevelByProblem] = useSessionState<Record<string, number>>('trace:hintLevelByProblem', {})
  const [evaluationByProblem, setEvaluationByProblem] = useSessionState<Record<string, SwarmEvaluationResponse>>('trace:evaluationByProblem', {})
  const [chatHistoryByProblem, setChatHistoryByProblem] = useSessionState<Record<string, ChatMessage[]>>('trace:chatHistoryByProblem', {})
  const [telemetryLogByProblem, setTelemetryLogByProblem] = useSessionState<Record<string, TelemetryLog>>('trace:telemetryLogByProblem', {})
  const [customProblems, setCustomProblems] = useSessionState<Problem[]>('trace:customProblems', [])
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [customFormOpen, setCustomFormOpen] = useState(false)
  const [editingProblem, setEditingProblem] = useState<Problem | null>(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isHintLoading, setIsHintLoading] = useState(false)
  const [isChatSending, setIsChatSending] = useState(false)
  const [chatInput, setChatInput] = useState('')
  const [networkError, setNetworkError] = useState('')

  const allProblems = useMemo(() => [...problems, ...customProblems], [customProblems])
  const problem = allProblems.find((item) => item.id === selectedProblemId) ?? allProblems[0]
  const problemIndex = allProblems.findIndex((item) => item.id === problem.id)
  const code = codeByProblem[problem.id] ?? problem.starterCode
  const hintLevel = hintLevelByProblem[problem.id] ?? 1
  const evaluation = evaluationByProblem[problem.id]
  const chatHistory = chatHistoryByProblem[problem.id] ?? []
  const telemetry = telemetryLogByProblem[problem.id] ?? EMPTY_TELEMETRY

  const addTelemetry = (incoming: SwarmEvaluationResponse['telemetry']) => {
    setTelemetryLogByProblem((current) => {
      const previous = current[problem.id] ?? EMPTY_TELEMETRY
      return {
        ...current,
        [problem.id]: {
          totalTokens: previous.totalTokens + incoming.total_tokens,
          estimatedCostUsd: previous.estimatedCostUsd + incoming.estimated_cost_usd,
          estimatedSavingsPercentage: incoming.estimated_savings_percentage,
          routingDecisions: [...previous.routingDecisions, ...incoming.routing_decisions],
        },
      }
    })
  }

  const runEvaluation = async (requestedHintLevel: number, fromHintTab = false) => {
    setNetworkError('')
    setIsRunning(true)
    if (fromHintTab) setIsHintLoading(true)
    try {
      const result = await evaluateSubmission({
        problem,
        userCode: code,
        hintLevel: requestedHintLevel,
        previousHints: evaluation?.progressive_hint ? [evaluation.progressive_hint] : [],
      })
      setEvaluationByProblem((current) => ({ ...current, [problem.id]: result }))
      addTelemetry(result.telemetry)
    } catch (error) {
      setNetworkError(error instanceof Error ? error.message : 'The evaluation service is unavailable.')
    } finally {
      setIsRunning(false)
      setIsHintLoading(false)
    }
  }

  const handleHintLevelChange = (level: number) => {
    if (level === hintLevel && evaluation) return
    setHintLevelByProblem((current) => ({ ...current, [problem.id]: level }))
    void runEvaluation(level, true)
  }

  const handleChatSubmit = async (event: FormEvent) => {
    event.preventDefault()
    const message = chatInput.trim()
    if (!message || isChatSending || isHintLoading) return
    const userMessage: ChatMessage = { role: 'user', content: message, timestamp: new Date().toISOString() }
    const historyForRequest = chatHistory
    setChatInput('')
    setChatHistoryByProblem((current) => ({ ...current, [problem.id]: [...(current[problem.id] ?? []), userMessage] }))
    setNetworkError('')
    setIsChatSending(true)
    try {
      const result = await sendChat({
        problem,
        userCode: code,
        diagnosis: evaluation?.misconception_diagnosis,
        failedCategory: evaluation?.failed_edge_case_category,
        history: historyForRequest,
        message,
      })
      const assistantMessage: ChatMessage = {
        role: 'assistant',
        content: result.reply,
        timestamp: new Date().toISOString(),
        modelTier: result.telemetry.routing_decisions.at(-1)?.tier,
      }
      setChatHistoryByProblem((current) => ({ ...current, [problem.id]: [...(current[problem.id] ?? []), assistantMessage] }))
      addTelemetry(result.telemetry)
    } catch (error) {
      setNetworkError(error instanceof Error ? error.message : 'The mentor service is unavailable.')
    } finally {
      setIsChatSending(false)
    }
  }

  const handleSaveCustomProblem = (customProblem: Problem) => {
    setCustomProblems((current) => editingProblem ? current.map((item) => item.id === customProblem.id ? customProblem : item) : [...current, customProblem])
    setCodeByProblem((current) => ({ ...current, [customProblem.id]: customProblem.starterCode }))
    setEvaluationByProblem((current) => omitKey(current, customProblem.id))
    setChatHistoryByProblem((current) => omitKey(current, customProblem.id))
    setTelemetryLogByProblem((current) => omitKey(current, customProblem.id))
    setSelectedProblemId(customProblem.id)
    setCustomFormOpen(false)
    setEditingProblem(null)
    setNetworkError('')
  }

  const openNewProblemForm = () => {
    setEditingProblem(null)
    setCustomFormOpen(true)
  }

  const openEditProblemForm = (customProblem: Problem) => {
    setEditingProblem({ ...customProblem, starterCode: codeByProblem[customProblem.id] ?? customProblem.starterCode })
    setCustomFormOpen(true)
  }

  return (
    <div className="app-shell">
      <Sidebar open={sidebarOpen} problems={allProblems} customProblemIds={new Set(customProblems.map((item) => item.id))} selectedId={problem.id} onSelect={setSelectedProblemId} onAddCustom={openNewProblemForm} onEditCustom={openEditProblemForm} onToggle={() => setSidebarOpen((open) => !open)} />
      <div className="workbench">
        <Header problem={problem} sidebarOpen={sidebarOpen} isRunning={isRunning} onToggleSidebar={() => setSidebarOpen((open) => !open)} onRun={() => void runEvaluation(hintLevel)} />
        <main className="workbench-grid">
          <section className="workspace-column">
            <ProblemHeader problem={problem} index={problemIndex} total={allProblems.length} />
            <div className="editor-panel">
              <div className="panel-toolbar"><div className="toolbar-label"><Code2 size={15} /> solution.py</div><div className="toolbar-meta"><span className="status-dot emerald" /> Python 3.11 <span className="toolbar-divider" /> UTF-8</div></div>
              <CodeEditor value={code} onChange={(value) => setCodeByProblem((current) => ({ ...current, [problem.id]: value }))} />
              <div className="editor-footer"><div className="editor-hint"><Command size={14} /> Tab inserts 4 spaces <span className="toolbar-divider" /> <span className="mono">Ln {code.split('\n').length}, Col 1</span></div><span className="editor-run-note">Run &amp; Diagnose is in the header</span></div>
            </div>
            <TestsPanel problem={problem} evaluation={evaluation} />
          </section>
          <aside className="inspector-column">
            <SignalPanel evaluation={evaluation} isRunning={isRunning} networkError={networkError} />
            <HintPanel hintLevel={hintLevel} setHintLevel={handleHintLevelChange} evaluation={evaluation} isLoading={isHintLoading} />
            <ChatPanel history={chatHistory} input={chatInput} setInput={setChatInput} onSubmit={handleChatSubmit} isSending={isChatSending || isHintLoading} hintLoading={isHintLoading} />
            <TelemetryAccordion telemetry={telemetry} />
          </aside>
        </main>
      </div>
      {customFormOpen && <CustomProblemForm key={editingProblem?.id ?? 'new'} initialProblem={editingProblem} onClose={() => { setCustomFormOpen(false); setEditingProblem(null) }} onSave={handleSaveCustomProblem} />}
    </div>
  )
}

function Sidebar({ open, problems: problemList, customProblemIds, selectedId, onSelect, onAddCustom, onEditCustom, onToggle }: { open: boolean; problems: Problem[]; customProblemIds: Set<string>; selectedId: string; onSelect: (id: string) => void; onAddCustom: () => void; onEditCustom: (problem: Problem) => void; onToggle: () => void }) {
  return (
    <aside className={`sidebar ${open ? 'expanded' : 'mini'}`} aria-expanded={open}>
      <div className="brand-row"><button className="brand-logo-area" onClick={onToggle} aria-label={open ? 'Collapse sidebar' : 'Open sidebar'}><span className="brand-mark">T</span><PanelLeftOpen className="brand-hover-toggle" size={18} /></button><span className="brand-name">Trace</span><span className="brand-version">BETA</span>{open && <button className="brand-collapse-toggle" onClick={onToggle} aria-label="Collapse sidebar"><PanelLeftClose size={16} /></button>}</div>
      <div className="sidebar-workspace"><span className="workspace-kicker">WORKSPACE</span><button className="workspace-select">Algorithm Lab <ChevronDown size={14} /></button></div>
      <div className="problem-nav"><div className="nav-heading"><span>PROBLEMS</span><span className="problem-count">{problemList.length}</span></div><div className="problem-list">{problemList.map((item, index) => <div className="problem-item-wrap" key={item.id}><button title={item.title} aria-label={`Open ${item.title}`} className={`problem-item ${item.id === selectedId ? 'selected' : ''}`} onClick={() => onSelect(item.id)}><span className={`problem-index ${item.id === selectedId ? 'active' : ''}`}>{String(index + 1).padStart(2, '0')}</span><span className="problem-copy"><span className="problem-title">{item.title}</span><span className="problem-meta"><span className={`difficulty ${item.difficulty.toLowerCase()}`}>{item.difficulty}</span><span>{item.category}</span></span></span>{item.id === 'longest-substring' && <Check size={14} className="problem-check" />}</button>{customProblemIds.has(item.id) && <button className="problem-edit-button" onClick={() => onEditCustom(item)} aria-label={`Edit ${item.title}`} title="Edit custom problem"><Pencil size={13} /></button>}</div>)}</div><button className="add-problem-button" onClick={onAddCustom}><Plus size={15} /><span>Add custom problem</span></button></div>
      <div className="sidebar-bottom"><div className="connection-row"><span className="status-dot emerald" /><span>Sandbox connected</span><span className="connection-latency">42ms</span></div><div className="build-row"><GitBranch size={14} /> main <span className="build-separator">·</span> trace-0.1</div></div>
    </aside>
  )
}

function Header({ problem, sidebarOpen, isRunning, onToggleSidebar, onRun }: { problem: Problem; sidebarOpen: boolean; isRunning: boolean; onToggleSidebar: () => void; onRun: () => void }) {
  return <header className="topbar"><div className="topbar-left"><button className="sidebar-toggle" onClick={onToggleSidebar} aria-label={sidebarOpen ? 'Collapse problem sidebar' : 'Open problem sidebar'}>{sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeftOpen size={18} />}</button><div className="breadcrumb"><span>Algorithm Lab</span><span className="breadcrumb-separator">/</span><strong>{problem.title}</strong></div></div><button className="header-run-button" onClick={onRun} disabled={isRunning}>{isRunning ? <><span className="spinner" /> Tracing</> : <><Play size={15} fill="currentColor" /> Run &amp; Diagnose</>}</button></header>
}

function ProblemHeader({ problem, index, total }: { problem: Problem; index: number; total: number }) {
  return <div className="problem-header"><div><div className="eyebrow"><span className="problem-chip">{problem.category}</span><span className={`difficulty ${problem.difficulty.toLowerCase()}`}>{problem.difficulty}</span><span className="eyebrow-separator">·</span><span>Problem {String(index + 1).padStart(2, '0')} of {String(total).padStart(2, '0')}</span></div><h1>{problem.title}</h1><p>{problem.description}</p></div><div className="objective-card"><span className="objective-label">TRACE OBJECTIVE</span><span className="objective-value"><ShieldCheck size={15} /> Find the invariant</span></div></div>
}

function CodeEditor({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const lineNumbersRef = useRef<HTMLDivElement>(null)
  const lineCount = Math.max(value.split('\n').length, 1)
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== 'Tab') return
    event.preventDefault()
    const target = event.currentTarget
    const start = target.selectionStart
    const end = target.selectionEnd
    onChange(`${value.slice(0, start)}    ${value.slice(end)}`)
    requestAnimationFrame(() => { target.selectionStart = start + 4; target.selectionEnd = start + 4 })
  }
  const handleScroll = (event: UIEvent<HTMLTextAreaElement>) => {
    if (lineNumbersRef.current) lineNumbersRef.current.scrollTop = event.currentTarget.scrollTop
  }
  return <div className="editor-body"><div ref={lineNumbersRef} className="line-numbers" aria-hidden="true">{Array.from({ length: lineCount }, (_, index) => <span key={index}>{String(index + 1).padStart(2, '0')}</span>)}</div><textarea ref={textareaRef} value={value} onChange={(event) => onChange(event.target.value)} onKeyDown={handleKeyDown} onScroll={handleScroll} spellCheck={false} aria-label="Python solution editor" /></div>
}

function TestsPanel({ problem, evaluation }: { problem: Problem; evaluation?: SwarmEvaluationResponse }) {
  const visibleResults = evaluation?.public_results ?? problem.tests.map((test) => ({ ...test, passed: false, actual_output: undefined }))
  return <section className="tests-panel"><div className="section-heading"><div className="section-title"><TerminalSquare size={15} /> PUBLIC TESTS <span className="count-pill">{visibleResults.length}</span></div><span className="section-status">{evaluation ? `${evaluation.public_results.filter((test) => test.passed).length}/${visibleResults.length} passed` : 'Awaiting execution'}</span></div><div className="test-list">{visibleResults.map((test, index) => <div className="test-row" key={`${String(test.input)}-${index}`}><span className={`test-state ${test.passed ? 'passed' : evaluation ? 'failed' : 'pending'}`}>{test.passed ? <Check size={13} /> : evaluation ? <X size={13} /> : <span />}</span><span className="test-name">case_{String(index + 1).padStart(2, '0')}</span><span className="test-input mono">in {formatValue(test.input)}</span><span className="test-output mono">{evaluation ? `out ${formatValue(test.actual_output)}` : `expected ${formatValue(test.expected_output)}`}</span><span className="test-time mono">{evaluation ? '12ms' : '—'}</span></div>)}</div></section>
}

function SignalPanel({ evaluation, isRunning, networkError }: { evaluation?: SwarmEvaluationResponse; isRunning: boolean; networkError: string }) {
  const status = isRunning ? 'EXECUTING' : evaluation ? (evaluation.all_passed ? 'PASSED' : 'ATTENTION') : 'READY'
  const statusClass = isRunning ? 'running' : evaluation?.all_passed ? 'passed' : evaluation ? 'warning' : 'ready'
  return <section className={`signal-panel ${statusClass}`}><div className="signal-header"><span className="signal-label"><span className="signal-pulse" /> SWARM SIGNAL</span><span className="signal-status">{status}</span></div>{networkError ? <div className="error-box"><AlertCircle size={15} /><span>{networkError}<small>Start the FastAPI service on port 8000 to evaluate.</small></span></div> : evaluation ? <><div className="signal-summary"><span className="signal-number">{evaluation.all_passed ? '✓' : `${evaluation.hidden_results_summary.failed}`}</span><span className="signal-summary-copy">{evaluation.all_passed ? 'All public and hidden cases passed.' : 'hidden edge cases need inspection.'}</span></div><div className="signal-grid"><Metric label="Public" value={`${evaluation.public_results.filter((test) => test.passed).length}/${evaluation.public_results.length}`} accent="emerald" /><Metric label="Hidden" value={`${evaluation.hidden_results_summary.passed}/${evaluation.hidden_results_summary.total}`} accent={evaluation.hidden_results_summary.failed ? 'amber' : 'emerald'} /><Metric label="Runtime" value={evaluation.execution_status} accent="zinc" /></div></> : <div className="empty-signal"><span className="empty-icon"><Zap size={17} /></span><div><strong>Ready for a trace.</strong><span>Run your code to generate adversarial cases and a diagnosis.</span></div></div>}</section>
}

function HintPanel({ hintLevel, setHintLevel, evaluation, isLoading }: { hintLevel: number; setHintLevel: (level: number) => void; evaluation?: SwarmEvaluationResponse; isLoading: boolean }) {
  return <section className="inspector-panel hint-panel"><div className="section-heading"><div className="section-title"><CircleHelp size={15} /> SOCRATIC HINT</div><span className="hint-depth">DEPTH {hintLevel}/3</span></div><div className="hint-levels">{[1, 2, 3].map((level) => <button key={level} className={hintLevel === level ? 'active' : ''} onClick={() => setHintLevel(level)} disabled={isLoading}><span>0{level}</span><small>{level === 1 ? 'Prompt' : level === 2 ? 'Invariant' : 'Trace'}</small></button>)}</div><div className={`hint-copy ${evaluation && !isLoading ? '' : 'muted'}`}>{isLoading ? <span className="hint-loading"><span className="spinner" /> Re-running the sandbox for a deeper hint…</span> : evaluation?.progressive_hint ?? 'Choose a hint depth, then run the sandbox to generate a Socratic response.'}</div>{evaluation?.failed_edge_case_category && !isLoading && <div className="diagnosis-tag"><AlertCircle size={13} /> {evaluation.failed_edge_case_category}</div>}</section>
}

function ChatPanel({ history, input, setInput, onSubmit, isSending, hintLoading }: { history: ChatMessage[]; input: string; setInput: (value: string) => void; onSubmit: (event: FormEvent) => void; isSending: boolean; hintLoading: boolean }) {
  return <section className="chat-panel"><div className="section-heading"><div className="section-title"><MessageSquareText size={15} /> SOCRATIC MENTOR</div><span className="chat-count">{hintLoading ? 'Generating hint' : history.length ? `${history.length} turns` : 'Context-aware'}</span></div><div className="chat-thread">{history.length === 0 && !hintLoading ? <div className="chat-empty"><Sparkles size={16} /><span>Ask about the diagnosis, invariant, or complexity.</span></div> : history.slice(-4).map((message, index) => <div className={`chat-message ${message.role}`} key={`${message.timestamp}-${index}`}><span className="message-role">{message.role === 'user' ? 'YOU' : 'TRACE'}</span><p>{message.content}</p></div>)}{isSending && <div className="chat-message assistant"><span className="message-role">TRACE</span><p className="typing"><i /><i /><i /></p></div>}</div><form className="chat-form" onSubmit={onSubmit}><input value={input} onChange={(event) => setInput(event.target.value)} placeholder="Ask a follow-up question…" disabled={isSending} /><button type="submit" aria-label="Send follow-up" disabled={!input.trim() || isSending}><Send size={15} /></button></form></section>
}

function TelemetryAccordion({ telemetry }: { telemetry: TelemetryLog }) {
  return <details className="telemetry-accordion"><summary><span><Gauge size={15} /> Model Orchestration Telemetry</span><span className="telemetry-summary-meta mono">{telemetry.totalTokens.toLocaleString()} tokens <ChevronDown size={14} /></span></summary><div className="telemetry-content"><div className="telemetry-stats"><div><span className="telemetry-value mono">{telemetry.totalTokens.toLocaleString()}</span><span className="telemetry-label">TOKENS</span></div><div><span className="telemetry-value mono">${telemetry.estimatedCostUsd.toFixed(4)}</span><span className="telemetry-label">EST. COST</span></div><div><span className="telemetry-value mono emerald-text">{telemetry.estimatedSavingsPercentage.toFixed(1)}%</span><span className="telemetry-label">SAVED</span></div></div><div className="routing-list">{(telemetry.routingDecisions.length ? telemetry.routingDecisions.slice(-3).reverse() : [{ step: 'awaiting_execution', tier: '—', model_used: 'No route yet', reason: 'Run an evaluation to inspect model routing.', prompt_tokens: 0, completion_tokens: 0 }]).map((route, index) => <div className="route-row" key={`${route.step}-${index}`}><span className="route-line" /><div className="route-copy"><span>{labelForStep(route.step)}</span><small className="mono">{route.tier} · {route.model_used.split('/').at(-1)}</small></div><span className="route-tokens mono">{route.prompt_tokens + route.completion_tokens || '—'}</span></div>)}</div></div></details>
}

function CustomProblemModal({ initialProblem, onClose, onCreate }: { initialProblem: Problem | null; onClose: () => void; onCreate: (problem: Problem) => void }) {
  const [title, setTitle] = useState(initialProblem?.title ?? '')
  const [category, setCategory] = useState(initialProblem?.category ?? '')
  const [description, setDescription] = useState(initialProblem?.description ?? '')
  const [input, setInput] = useState(initialProblem?.tests[0] ? editableValue(initialProblem.tests[0].input) : '')
  const [expected, setExpected] = useState(initialProblem?.tests[0] ? editableValue(initialProblem.tests[0].expected_output) : '')
  const [code, setCode] = useState(initialProblem?.starterCode ?? '')
  const [error, setError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim() || !category.trim() || !description.trim() || !input.trim() || !expected.trim()) {
      setError('Title, category, description, input, and expected output are required.')
      return
    }
    onCreate({ id: initialProblem?.id ?? `${slugify(title)}-${Date.now()}`, title: title.trim(), category: category.trim(), difficulty: initialProblem?.difficulty ?? 'MEDIUM', description: description.trim(), starterCode: code, tests: [{ input: parseValue(input), expected_output: parseValue(expected) }] })
  }

  return <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="custom-problem-title"><form className="custom-problem-modal" onSubmit={handleSubmit}><div className="modal-header"><div><span className="eyebrow">CUSTOM WORKSPACE</span><h2 id="custom-problem-title">{initialProblem ? 'Edit custom problem' : 'Add a problem to Trace'}</h2></div><button type="button" className="modal-close" onClick={onClose} aria-label="Close custom problem form"><X size={17} /></button></div><div className="modal-grid"><label>Problem title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Merge overlapping intervals" autoFocus /></label><label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="e.g. Intervals" /></label><label className="full-width">Problem description<textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the algorithmic objective and expected return value." rows={3} /></label><label>Public test input<span className="field-hint">JSON or plain text</span><textarea value={input} onChange={(event) => setInput(event.target.value)} placeholder="[[1, 3], [2, 6]]" rows={2} /></label><label>Expected output<span className="field-hint">JSON or plain text</span><textarea value={expected} onChange={(event) => setExpected(event.target.value)} placeholder="[[1, 6]]" rows={2} /></label><label className="full-width">Starting code<span className="field-hint">Optional — you can also write it in the editor after creating.</span><textarea className="modal-code" value={code} onChange={(event) => setCode(event.target.value)} placeholder={'def solve(input_data):\n    pass'} rows={6} spellCheck={false} /></label></div>{error && <div className="modal-error"><AlertCircle size={14} /> {error}</div>}<div className="modal-footer"><span className="modal-note">Saved to this browser session</span><div><button type="button" className="modal-secondary" onClick={onClose}>Cancel</button><button type="submit" className="modal-primary">{initialProblem ? <><Pencil size={15} /> Save changes</> : <><Plus size={15} /> Create problem</>}</button></div></div></form></div>
}

function Metric({ label, value, accent }: { label: string; value: string; accent: string }) {
  return <div className="metric"><span className="metric-label">{label}</span><span className={`metric-value ${accent}-text`}>{value}</span></div>
}

function formatValue(value: unknown) {
  if (value === undefined) return '—'
  return typeof value === 'string' ? JSON.stringify(value) : JSON.stringify(value)
}

function labelForStep(step: string) {
  return step.replaceAll('_', ' ').replace(/\b\w/g, (character) => character.toUpperCase())
}

function parseValue(value: string) {
  try {
    return JSON.parse(value)
  } catch {
    return value
  }
}

function editableValue(value: unknown) {
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function omitKey<T extends object>(record: T, key: string): T {
  const next = { ...record }
  delete (next as Record<string, unknown>)[key]
  return next
}

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'custom-problem'
}

export default App
