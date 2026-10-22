import { FormEvent, KeyboardEvent, useState } from 'react'
import { AlertCircle, Loader2, Pencil, Plus, X } from 'lucide-react'
import { importProblem } from '../lib/api'
import { Problem, TestCase } from '../types'

type CustomProblemFormProps = {
  initialProblem: Problem | null
  onClose: () => void
  onSave: (problem: Problem) => void
}

export default function CustomProblemForm({ initialProblem, onClose, onSave }: CustomProblemFormProps) {
  const [importQuery, setImportQuery] = useState('')
  const [isImporting, setIsImporting] = useState(false)
  const [importError, setImportError] = useState('')
  const [title, setTitle] = useState(initialProblem?.title ?? '')
  const [category, setCategory] = useState(initialProblem?.category ?? '')
  const [description, setDescription] = useState(initialProblem?.description ?? '')
  const [testsJson, setTestsJson] = useState(initialProblem ? JSON.stringify(initialProblem.tests, null, 2) : '')
  const [code, setCode] = useState(initialProblem?.starterCode ?? '')
  const [formError, setFormError] = useState('')

  const handleImport = async () => {
    const query = importQuery.trim()
    if (!query || isImporting) return
    setImportError('')
    setFormError('')
    setIsImporting(true)
    try {
      const imported = await importProblem(query)
      setTitle(imported.problem_title)
      setCategory(imported.category)
      setDescription(imported.problem_description)
      setTestsJson(JSON.stringify(imported.public_test_cases, null, 2))
      setCode('')
    } catch (error) {
      setImportError(error instanceof Error ? error.message : 'The problem importer is unavailable.')
    } finally {
      setIsImporting(false)
    }
  }

  const handleImportKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      void handleImport()
    }
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!title.trim() || !category.trim() || !description.trim() || !testsJson.trim()) {
      setFormError('Title, category, description, and at least one public test case are required.')
      return
    }
    let tests: TestCase[]
    try {
      const parsed = JSON.parse(testsJson) as unknown
      if (!Array.isArray(parsed) || parsed.length === 0 || !parsed.every(isTestCase)) throw new Error('invalid test case format')
      tests = parsed
    } catch {
      setFormError('Public test cases must be a JSON array of objects with input and expected_output fields.')
      return
    }
    onSave({
      id: initialProblem?.id ?? `${slugify(title)}-${Date.now()}`,
      title: title.trim(),
      category: category.trim(),
      difficulty: initialProblem?.difficulty ?? 'MEDIUM',
      description: description.trim(),
      starterCode: code,
      tests,
    })
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="custom-problem-title">
      <form className="custom-problem-modal" onSubmit={handleSubmit}>
        <div className="modal-header"><div><span className="eyebrow">CUSTOM WORKSPACE</span><h2 id="custom-problem-title">{initialProblem ? 'Edit custom problem' : 'Add a problem to Trace'}</h2></div><button type="button" className="modal-close" onClick={onClose} aria-label="Close custom problem form"><X size={17} /></button></div>
        <div className="smart-import">
          <div className="smart-import-label"><span>SMART IMPORT</span><small>Fill the workspace from a LeetCode problem</small></div>
          <div className="smart-import-row"><input value={importQuery} onChange={(event) => setImportQuery(event.target.value)} onKeyDown={handleImportKeyDown} placeholder="✨ Auto-Import Problem (e.g., LC 2 or 'Merge Intervals')" disabled={isImporting} aria-label="Auto-import problem" /><button type="button" className="smart-import-button" onClick={() => void handleImport()} disabled={!importQuery.trim() || isImporting}>{isImporting ? <><Loader2 size={15} className="animate-spin" /> Importing</> : 'Import'}</button></div>
          {importError && <div className="import-error"><AlertCircle size={14} /> {importError}</div>}
        </div>
        <div className="modal-grid">
          <label>Problem title<input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Merge overlapping intervals" autoFocus /></label>
          <label>Category<input value={category} onChange={(event) => setCategory(event.target.value)} placeholder="e.g. Intervals" /></label>
          <label className="full-width">Problem description<textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the algorithmic objective and expected return value." rows={3} /></label>
          <label className="full-width">Public test cases JSON<span className="field-hint">Array of {`{ input, expected_output }`} objects</span><textarea className="test-cases-json" value={testsJson} onChange={(event) => setTestsJson(event.target.value)} placeholder={'[\n  { "input": [2, 7, 11, 15], "expected_output": [0, 1] }\n]'} rows={6} spellCheck={false} /></label>
          <label className="full-width">Starting code<span className="field-hint">Optional — import intentionally leaves this empty so you can solve immediately.</span><textarea className="modal-code" value={code} onChange={(event) => setCode(event.target.value)} placeholder={'def solve(input_data):\n    pass'} rows={6} spellCheck={false} /></label>
        </div>
        {formError && <div className="modal-error"><AlertCircle size={14} /> {formError}</div>}
        <div className="modal-footer"><span className="modal-note">Saved to this browser session</span><div><button type="button" className="modal-secondary" onClick={onClose}>Cancel</button><button type="submit" className="modal-primary">{initialProblem ? <><Pencil size={15} /> Save changes</> : <><Plus size={15} /> Create problem</>}</button></div></div>
      </form>
    </div>
  )
}

function isTestCase(value: unknown): value is TestCase {
  return typeof value === 'object' && value !== null && 'input' in value && 'expected_output' in value
}

function slugify(value: string) {
  return value.toLowerCase().trim().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || 'custom-problem'
}
