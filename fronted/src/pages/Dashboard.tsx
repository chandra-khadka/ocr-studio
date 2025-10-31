import {useEffect, useMemo, useState} from 'react'
import FileUploader from '../components/FileUploader'
import ModelSelector from '../components/ModelSelector'
import PromptEditor from '../components/PromptEditor'
import ChatPanel from '../components/ChatPanel'
import {
  runCorrection,
  runOCR,
  runOCRPremium,
  listOCRModels,
  listCorrectionModels,
} from '../services/api'
import {
  DocumentFormat,
  DocumentType,
  Language,
  OCRProvider,
  CorrectionProvider
} from '../types/enums'
import SummaryBar from '../components/SummaryBar'

// --- Markdown → HTML (lightweight preview) ---
function mdToHtml(md: string) {
  let s = md.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  s = s.replace(/```([\s\S]*?)```/g, (_m, p1) => `<pre class="md-pre"><code>${p1}</code></pre>`)
  s = s.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>')
  s = s.replace(/^###### (.*)$/gm, '<h6>$1</h6>')
  s = s.replace(/^##### (.*)$/gm, '<h5>$1</h5>')
  s = s.replace(/^#### (.*)$/gm, '<h4>$1</h4>')
  s = s.replace(/^### (.*)$/gm, '<h3>$1</h3>')
  s = s.replace(/^## (.*)$/gm, '<h2>$1</h2>')
  s = s.replace(/^# (.*)$/gm, '<h1>$1</h1>')
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/\*([^*]+)\*/g, '<em>$1</em>')
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
  s = s.replace(/^(?:-|\*) (.*)$/gm, '<li>$1</li>')
  s = s.replace(/(<li>[\s\S]*?<\/li>)/g, '<ul>$1</ul>')
  s = s
      .split(/\n{2,}/)
      .map(b => (/^\s*</.test(b.trim()) ? b : `<p>${b.trim().replace(/\n/g, '<br/>')}</p>`))
      .join('\n')

  const css = `
  <style>
    body { font-family: ui-sans-serif, system-ui, Inter, Roboto, Arial; padding: 16px; color:#1f2937; }
    h1,h2,h3,h4,h5,h6 { margin: 1em 0 .5em; line-height:1.2; }
    p { margin: .6em 0; }
    a { color:#0ea5e9; text-decoration: none; }
    a:hover { text-decoration: underline; }
    ul { margin: .4em 0 .6em 1.2em; list-style: disc; }
    pre.md-pre { background:#0b1020; color:#e5e7eb; padding:12px; border-radius:12px; overflow:auto; border:1px solid #e5e7eb1a;}
    code.md-code { background:#f3f4f6; padding:.1rem .35rem; border-radius:.35rem; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
    th, td { border: 1px solid #e5e7eb; padding: 6px 8px; vertical-align: top; }
    th { background: #f9fafb; text-align: left; }
    hr { border: none; border-top: 1px solid #e5e7eb; margin: 16px 0; }
    img { max-width: 100%; border-radius: 8px; }
    ins.diff-add { background: #d1fae5; text-decoration: none; }
    del.diff-del { background: #fee2e2; text-decoration: line-through; }
  </style>
  `
  return `<!doctype html><meta charset="utf-8"><title>Preview</title>${css}<article>${s}</article>`
}

// ---- Simple word-level diff (LCS) ----
type DiffToken = { text: string; type: 'eq' | 'add' | 'del' }
function diffWords(a: string, b: string): DiffToken[] {
  const A = a.trim().split(/\s+/), B = b.trim().split(/\s+/)
  const n = A.length, m = B.length
  const dp = Array.from({length: n + 1}, () => Array(m + 1).fill(0))
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1])
    }
  }
  const out: DiffToken[] = []
  let i = 0, j = 0
  while (i < n && j < m) {
    if (A[i] === B[j]) { out.push({text: A[i], type: 'eq'}); i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) { out.push({text: A[i], type: 'del'}); i++; }
    else { out.push({text: B[j], type: 'add'}); j++; }
  }
  while (i < n) { out.push({text: A[i], type: 'del'}); i++; }
  while (j < m) { out.push({text: B[j], type: 'add'}); j++; }
  return out
}

function DiffView({original, corrected}: { original: string; corrected: string }) {
  const tokens = useMemo(() => diffWords(original, corrected), [original, corrected])
  return (
    <div className="prose max-w-none">
      <div className="text-xs text-slate-500 mb-2">Differences (word-level)</div>
      <div className="rounded-2xl border border-gray-200 bg-white p-4 text-sm leading-7">
        {tokens.map((t, idx) => {
          if (t.type === 'eq') return <span key={idx}>{t.text} </span>
          if (t.type === 'add') return <ins key={idx} className="diff-add">{t.text} </ins>
          return <del key={idx} className="diff-del">{t.text} </del>
        })}
      </div>

      <div className="grid md:grid-cols-2 gap-4 mt-4">
        <div className="rounded-2xl border border-gray-200 bg-gray-50 p-3">
          <div className="text-xs font-semibold text-slate-600 mb-2">Original OCR</div>
          <pre className="whitespace-pre-wrap text-[13px]">{original || '—'}</pre>
        </div>
        <div className="rounded-2xl border border-gray-200 bg-emerald-50 p-3">
          <div className="text-xs font-semibold text-emerald-700 mb-2">Corrected</div>
          <pre className="whitespace-pre-wrap text-[13px]">{corrected || '—'}</pre>
        </div>
      </div>
    </div>
  )
}

// --- Utility: strip ``` fences and leading "markdown\n" from LLM output ---
function cleanMarkdownFence(s: string): string {
  if (!s) return s
  let t = s.trim()
  // remove triple backtick opening with optional language
  t = t.replace(/^```(?:[a-z0-9_-]+)?\s*/i, '')
  // remove trailing triple backticks
  t = t.replace(/\s*```$/i, '')
  // remove leading "markdown\n" or "md\n"
  t = t.replace(/^(?:markdown|md)\s*\n/i, '')
  return t.trim()
}

// --- Structured Data view (pretty table + JSON copy/download) ---
function StructuredView({data, meta}: { data: Record<string, any>, meta?: any }) {
  if (!data) return null

  const rows = Object.entries(data)

  const jsonPretty = useMemo(() => JSON.stringify(data, null, 2), [data])

  const copyJson = async () => {
    try { await navigator.clipboard.writeText(jsonPretty) } catch {}
  }

  const downloadJson = () => {
    const blob = new Blob([jsonPretty], {type: 'application/json'})
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'structured_data.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-4">
      {/* KV Table */}
      <div className="rounded-2xl border border-emerald-100 overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-emerald-50">
            <tr>
              <th className="text-left px-3 py-2 w-56">Field</th>
              <th className="text-left px-3 py-2">Value</th>
            </tr>
          </thead>
          <tbody>
          {rows.map(([k, v]) => (
            <tr key={k} className="border-t">
              <td className="px-3 py-2 font-medium text-slate-700">{k}</td>
              <td className="px-3 py-2 text-slate-800">
                {v === null || v === undefined || v === '' ? <span className="text-slate-400">—</span>
                  : typeof v === 'object' ? <pre className="whitespace-pre-wrap">{JSON.stringify(v, null, 2)}</pre>
                  : String(v)}
              </td>
            </tr>
          ))}
          </tbody>
        </table>
      </div>

      {/* JSON panel */}
      <div className="rounded-2xl border border-slate-200 bg-white">
        <div className="flex items-center justify-between px-3 py-2 border-b">
          <div className="text-xs font-semibold text-slate-600">structured_data.json</div>
          <div className="flex items-center gap-2">
            <button className="text-xs px-2 py-1 rounded-md border bg-white hover:bg-slate-50" onClick={copyJson} type="button">Copy</button>
            <button className="text-xs px-2 py-1 rounded-md border bg-white hover:bg-slate-50" onClick={downloadJson} type="button">Download</button>
          </div>
        </div>
        <pre className="p-3 text-xs overflow-auto max-h-[50vh]">{jsonPretty}</pre>
      </div>

      {/* Meta (if provided) */}
      {meta && (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
          <div className="text-xs font-semibold text-slate-700 mb-2">Meta</div>
          <div className="grid sm:grid-cols-2 gap-2 text-sm">
            <div><span className="text-slate-500">ocr_provider:</span> <span className="font-medium">{meta.ocr_provider ?? '—'}</span></div>
            <div><span className="text-slate-500">correction_provider:</span> <span className="font-medium">{meta.correction_provider ?? '—'}</span></div>
            <div><span className="text-slate-500">document_type:</span> <span className="font-medium">{meta.document_type ?? '—'}</span></div>
            <div><span className="text-slate-500">language_detected:</span> <span className="font-medium">{meta.language_detected ?? '—'}</span></div>
            <div><span className="text-slate-500">confidence:</span> <span className="font-medium">{meta.confidence ?? '—'}</span></div>
          </div>
        </div>
      )}
    </div>
  )
}

type TabKey = 'ocr' | 'corrected' | 'structured' | 'diff' | 'preview'

// --- Uploads gallery helpers ---
type UploadedFile = {
  id: string
  name: string
  url: string
  b64: string
  type: string
  size: number
  uploadedAt: number
}
const isImage = (type: string, name: string) =>
  (type && type.startsWith('image/')) || /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(name)
const isPdf = (type: string, name: string) =>
  type === 'application/pdf' || /\.pdf$/i.test(name)
const formatBytes = (n: number) => {
  if (!n) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.min(Math.floor(Math.log(n) / Math.log(k)), sizes.length - 1)
  return `${(n / Math.pow(k, i)).toFixed(i ? 1 : 0)} ${sizes[i]}`
}

// ===== Progress steps =====
const OCR_STEPS = [
  'Detecting layout…',
  'Auto-detecting language…',
  'Enhancing contrast…',
  'Segmenting lines…',
  'Recognizing text…',
  'Reconstructing tables…',
  'Building Markdown…'
] as const

const CORR_STEPS = [
  'Tokenizing text…',
  'Fixing OCR artifacts…',
  'Normalizing whitespace…',
  'Standardizing dates & numbers…',
  'Correcting spelling…',
  'Applying style/prompt…',
  'Rendering Markdown…'
] as const

type ProgressMode = 'idle' | 'ocr' | 'premium' | 'correction'

export default function Dashboard() {
  // Dynamic models for the selected providers
  const [models, setModels] = useState<{ ocr: string[]; correction: string[] }>({ocr: [], correction: []})

  // Configuration state
  const [language, setLanguage] = useState(Language.ENGLISH)
  const [documentType, setDocumentType] = useState(DocumentType.GENERAL)
  const [documentFormat, setDocumentFormat] = useState(DocumentFormat.STANDARD)
  const [ocrProvider, setOcrProvider] = useState<OCRProvider>(OCRProvider.MISTRAL)
  const [correctionProvider, setCorrectionProvider] =
    useState<CorrectionProvider>(CorrectionProvider.GEMINI)

  const [selectedOCRModel, setSelectedOCRModel] = useState('')
  const [selectedCorrectionModel, setSelectedCorrectionModel] = useState('')
  const [prompt, setPrompt] = useState('')

  // Current selection (kept in sync with gallery)
  const [fileName, setFileName] = useState('')
  const [fileB64, setFileB64] = useState('')

  const [ocrResult, setOcrResult] = useState('')
  const [corrected, setCorrected] = useState('')

  // New: structured + meta from premium API
  const [structured, setStructured] = useState<Record<string, any> | null>(null)
  const [meta, setMeta] = useState<any>(null)

  // Loading states
  const [loading, setLoading] = useState(false)          // OCR (basic or premium)
  const [correcting, setCorrecting] = useState(false)    // Correction

  // UI tabs
  const [tab, setTab] = useState<TabKey>('ocr')

  // ===== uploads gallery =====
  const [uploads, setUploads] = useState<UploadedFile[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const selected = uploads.find(u => u.id === selectedId) || null

  // Preview modal state
  const [showPreview, setShowPreview] = useState(false)
  const [zoom, setZoom] = useState(100)
  const [rotation, setRotation] = useState(0)
  const [invert, setInvert] = useState(false)
  const isRotatedPortrait = ((rotation % 180) !== 0)

  // ===== progress UI state =====
  const [progress, setProgress] = useState(0) // 0..100
  const [progressMode, setProgressMode] = useState<ProgressMode>('idle')

  const activeSteps = progressMode === 'correction' ? CORR_STEPS : OCR_STEPS
  const currentStep = Math.min(Math.floor((progress / 100) * activeSteps.length), activeSteps.length - 1)

  // Simulate smooth progress while loading/correcting
  useEffect(() => {
    const running = (loading || correcting)
    if (!running) return
    setProgress(0)
    const id = setInterval(() => {
      setProgress(p => Math.min(96, p + 4 + Math.random() * 6 - (p > 70 ? 3 : 0)))
    }, 180)
    return () => clearInterval(id)
  }, [loading, correcting])

  // When a run finishes, complete to 100 and then reset
  useEffect(() => {
    const running = (loading || correcting)
    if (running) return
    if (progressMode === 'idle') return
    setProgress(100)
    const t1 = setTimeout(() => setProgressMode('idle'), 400)
    const t2 = setTimeout(() => setProgress(0), 800)
    return () => { clearTimeout(t1); clearTimeout(t2) }
  }, [loading, correcting, progressMode])

  // ==== Provider-aware model loading ====
  useEffect(() => {
    (async () => {
      const [ocr, corr] = await Promise.all([
        listOCRModels(ocrProvider),
        listCorrectionModels(correctionProvider as unknown as CorrectionProvider),
      ])
      setModels({ocr, correction: corr})
      setSelectedOCRModel(ocr[0] || '')
      setSelectedCorrectionModel(corr[0] || '')
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // run once

  useEffect(() => {
    (async () => {
      const ocr = await listOCRModels(ocrProvider)
      setModels(prev => ({...prev, ocr}))
      if (!ocr.includes(selectedOCRModel)) setSelectedOCRModel(ocr[0] || '')
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ocrProvider])

  useEffect(() => {
    (async () => {
      const corr = await listCorrectionModels(correctionProvider as unknown as CorrectionProvider)
      setModels(prev => ({...prev, correction: corr}))
      if (!corr.includes(selectedCorrectionModel)) setSelectedCorrectionModel(corr[0] || '')
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [correctionProvider])

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => uploads.forEach(u => URL.revokeObjectURL(u.url))
  }, [uploads])

  // === Handle new file (adds to gallery + selects it) ===
  function onFile(file: File, b64: string) {
    setOcrResult('')
    setCorrected('')
    setStructured(null)
    setMeta(null)
    setTab('ocr')

    const id = `${Date.now()}_${Math.random().toString(36).slice(2)}`
    const url = URL.createObjectURL(file)
    const entry: UploadedFile = {
      id,
      name: file.name,
      url,
      b64,
      type: file.type || '',
      size: file.size || 0,
      uploadedAt: Date.now()
    }
    setUploads(prev => [entry, ...prev])
    setSelectedId(id)

    setFileName(file.name)
    setFileB64(b64)
  }

  // Select from gallery
  function selectUpload(u: UploadedFile) {
    setSelectedId(u.id)
    setFileName(u.name)
    setFileB64(u.b64)
    setOcrResult('')
    setCorrected('')
    setStructured(null)
    setMeta(null)
    setTab('ocr')
  }

  // Remove one upload
  function removeUpload(id: string) {
    setUploads(prev => {
      const victim = prev.find(u => u.id === id)
      if (victim) URL.revokeObjectURL(victim.url)
      const next = prev.filter(u => u.id !== id)

      if (selectedId === id) {
        setSelectedId(next[0]?.id ?? null)
        if (next[0]) {
          setFileName(next[0].name)
          setFileB64(next[0].b64)
        } else {
          setFileName('')
          setFileB64('')
          setOcrResult('')
          setCorrected('')
          setStructured(null)
          setMeta(null)
        }
      }
      return next
    })
  }

  // Clear all uploads
  function clearUploads() {
    uploads.forEach(u => URL.revokeObjectURL(u.url))
    setUploads([])
    setSelectedId(null)
    setFileName('')
    setFileB64('')
    setOcrResult('')
    setCorrected('')
    setStructured(null)
    setMeta(null)
    setTab('ocr')
  }

  async function doOCR() {
    if (!fileB64) return
    setProgressMode('ocr')
    setLoading(true)
    try {
      const res = await runOCR({
        fileName,
        fileBase64: fileB64,
        language,
        documentType,
        provider: `${ocrProvider}:${selectedOCRModel}`,
        prompt
      } as any)
      setOcrResult(res.text || '')
      setStructured(null)
      setMeta(null)
      setTab('ocr')
    } finally {
      setLoading(false)
    }
  }

  // ---- Premium OCR call ----
  async function doOCRPremium() {
    if (!fileB64) return
    setProgressMode('premium')
    setLoading(true)
    try {
      const res = await runOCRPremium({
        base64_image: fileB64,
        ocr_provider: String(ocrProvider),
        correction_provider: String(correctionProvider),
        document_type: String(documentType),
        document_format: String(documentFormat),
        language: String(language),
        enable_json_parsing: true,
        use_segmentation: false,
        max_pdf_pages: 5,
        pdf_dpi: 300,
        custom_prompt: prompt,
        provider_config: {
          ocr_model: selectedOCRModel,
          correction_model: selectedCorrectionModel
        }
      })
      // Only show OCR result; DO NOT auto-populate corrected
      setOcrResult((res?.text ?? '') as string)
      setStructured((res?.structured_data ?? null) as any)
      setMeta(res?.meta ?? null)
      setCorrected('')
      setTab('ocr')
    } finally {
      setLoading(false)
    }
  }

  async function doCorrection() {
    if (!ocrResult) return
    setProgressMode('correction')
    setCorrecting(true)
    try {
      const res = await runCorrection({
        text: ocrResult,
        model: `${correctionProvider}:${selectedCorrectionModel}`,
        prompt
      })
      const raw = (res.corrected ?? res.text ?? '') as string
      const cleaned = cleanMarkdownFence(raw)
      setCorrected(cleaned)
      // When structured_data exists, keep tabs at 'ocr'/'structured' but show diff below;
      // still, landing on 'diff' is convenient:
      setTab('diff')
    } finally {
      setCorrecting(false)
    }
  }

  function resetAll() {
    uploads.forEach(u => URL.revokeObjectURL(u.url))
    setUploads([])
    setSelectedId(null)

    setFileName('')
    setFileB64('')
    setOcrResult('')
    setCorrected('')
    setStructured(null)
    setMeta(null)
    setTab('ocr')

    setShowPreview(false)
    setZoom(100)
    setRotation(0)
    setInvert(false)
  }

  const htmlPreview = useMemo(() => {
    const text = corrected || ocrResult || ''
    return mdToHtml(text)
  }, [ocrResult, corrected])

  const hasCorrection = !!corrected
  const isBusy = loading || correcting

  return (
    <section className="relative min-h-[100svh] overflow-hidden">
      {/* === Background === */}
      <div className="pointer-events-none absolute inset-0 -z-50">
        <div
          className="absolute inset-0"
          style={{
            background:
              'conic-gradient(from 210deg at 60% 40%, #ecfdf5 0%, #ecfeff 22%, #f5f3ff 45%, #ecfdf5 100%)',
            filter: 'saturate(1.05) brightness(1.05)',
            animation: 'huerotate 28s linear infinite'
          }}
        />
        <div className="absolute -top-40 left-1/2 h-[80vmin] w-[80vmin] -translate-x-1/2 rounded-full bg-emerald-300/20 blur-[110px]"/>
        <div className="absolute bottom-[-25%] right-10 h-[60vmin] w-[60vmin] rounded-full bg-cyan-300/20 blur-[100px]"/>
        <div className="absolute top-1/3 -left-10 h-[55vmin] w-[55vmin] rounded-full bg-violet-400/15 blur-[90px]"/>
        <div
          className="absolute inset-0 opacity-20 mix-blend-overlay"
          style={{
            backgroundImage: 'radial-gradient(rgba(2,6,23,0.1) 1px, transparent 1px)',
            backgroundSize: '16px 16px'
          }}
        />
        <div
          className="absolute inset-0 opacity-[0.05]"
          style={{backgroundImage: 'repeating-linear-gradient(180deg, rgba(2,6,23,.35) 0, rgba(2,6,23,.35) 1px, transparent 1px, transparent 8px)'}}
        />
        <div
          className="absolute inset-x-0 top-10 h-24 bg-gradient-to-b from-emerald-300/40 via-emerald-300/20 to-transparent blur-2xl animate-[sweep_8s_linear_infinite]"/>
      </div>

      <div className="max-w-7xl mx-auto px-4 py-8">
        <SummaryBar
          language={language}
          documentType={documentType}
          ocrProvider={String(ocrProvider)}
          ocrModel={selectedOCRModel}
          correctionProvider={String(correctionProvider)}
          correctionModel={selectedCorrectionModel}
          fileName={fileName}
          onReset={resetAll}
          onRunOCR={doOCR}
          canRun={!!fileB64 && !loading}
          loading={loading}
        />

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {/* Config */}
            <div className="card p-6 bg-white/85 backdrop-blur border border-emerald-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold">Configuration</h3>
                <div className="text-xs text-gray-500">Select providers, models, and prompt</div>
              </div>
              <ModelSelector
                language={language} setLanguage={setLanguage}
                documentType={documentType} setDocumentType={setDocumentType}
                documentFormat={documentFormat} setDocumentFormat={setDocumentFormat}
                ocrProvider={ocrProvider} setOcrProvider={setOcrProvider}
                correctionProvider={correctionProvider} setCorrectionProvider={setCorrectionProvider}
                modelOptions={models}
                selectedOCRModel={selectedOCRModel} setSelectedOCRModel={setSelectedOCRModel}
                selectedCorrectionModel={selectedCorrectionModel}
                setSelectedCorrectionModel={setSelectedCorrectionModel}
              />
              <div className="mt-4">
                <PromptEditor
                  prompt={prompt}
                  setPrompt={setPrompt}
                  label="Custom Extraction Prompt"
                  placeholder="e.g., Extract header table and list of transactions as Markdown with a summary."
                />
              </div>
            </div>

            {/* Upload */}
            <div className="card p-6 bg-white/90 backdrop-blur border border-emerald-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="font-bold">Upload</h3>
                <div className="text-xs text-gray-500">PDF / PNG / JPG / JPEG / TIF / TIFF</div>
              </div>
              <FileUploader onSelect={onFile} accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"/>
              {fileName ? (
                <div className="mt-3 text-sm text-gray-600">
                  <span className="font-semibold">Selected:</span> {fileName}
                </div>
              ) : (
                <div className="mt-3 text-sm text-gray-500">Pick a file to enable OCR.</div>
              )}
              <div className="mt-4 flex flex-wrap gap-3">
                <button
                  className={`btn ${!fileB64 ? 'opacity-60 cursor-not-allowed' : ''} ${!isBusy && fileB64 ? 'shadow-[0_0_0_0_rgba(16,185,129,0.6)] animate-pulse-soft' : ''}`}
                  onClick={doOCRPremium}
                  disabled={!fileB64 || isBusy}
                  type="button"
                  title="Higher-quality pipeline with JSON awareness"
                >
                  {loading && progressMode !== 'idle' ? '⏳ Processing…' : '🚀 Run Premium OCR'}
                </button>
                <button
                  className="btn-outline"
                  onClick={doCorrection}
                  disabled={!ocrResult || isBusy}
                  type="button"
                >
                  {correcting ? '⏳ Correcting…' : '✨ Apply Correction'}
                </button>
                <button
                  className="btn-ghost"
                  type="button"
                  onClick={() => {
                    if (!selected) return
                    setShowPreview(true)
                    setZoom(100)
                    setRotation(0)
                    setInvert(false)
                  }}
                  disabled={!selected || isBusy}
                  title="Preview the selected document"
                >
                  👁 Preview
                </button>
              </div>

              {/* Mini progress (only while busy) */}
              {isBusy && (
                <div className="mt-6 text-xs text-gray-700">
                  <div className="mb-2 font-semibold">
                    {progressMode === 'correction' ? 'Correcting… ' : 'Processing… '}
                    {Math.max(1, Math.floor(progress))}%
                  </div>
                  <div className="h-1.5 bg-emerald-100 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 transition-[width] duration-200"
                      style={{width: `${progress}%`}}
                    />
                  </div>
                  <ul className="mt-3 space-y-1.5">
                    {activeSteps.map((s, i) => (
                      <li key={i} className="flex items-center gap-2">
                        <span
                          className={`inline-block h-2 w-2 rounded-full ${
                            i < currentStep ? 'bg-emerald-500' : i === currentStep ? 'bg-amber-400' : 'bg-slate-300'
                          }`}
                        />
                        <span className={`${i <= currentStep ? 'text-slate-700' : 'text-slate-400'}`}>{s}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Uploaded documents gallery */}
              {uploads.length > 0 && (
                <div className="mt-8">
                  <div className="mb-2 flex items-center justify-between">
                    <h4 className="font-semibold text-sm text-slate-800">Uploaded documents</h4>
                    <button
                      className="text-xs text-slate-500 hover:text-rose-600 underline underline-offset-2"
                      onClick={clearUploads}
                      type="button"
                      aria-label="Clear uploaded documents"
                    >
                      Clear all
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {uploads.map(u => {
                      const isSel = u.id === selectedId
                      return (
                        <div
                          key={u.id}
                          onClick={() => selectUpload(u)}
                          role="button"
                          tabIndex={0}
                          onKeyDown={(e) => (e.key === 'Enter' ? selectUpload(u) : undefined)}
                          className={`group relative flex gap-3 rounded-xl border p-3 bg-white/70 hover:bg-white transition cursor-pointer ${
                            isSel ? 'border-emerald-300 ring-2 ring-emerald-200' : 'border-slate-200'
                          }`}
                          title={u.name}
                          aria-current={isSel ? 'true' : 'false'}
                        >
                          <div className="shrink-0">
                            {isImage(u.type, u.name) ? (
                              <img src={u.url} alt={u.name}
                                   className="h-14 w-14 object-cover rounded-md border border-slate-200"/>
                            ) : isPdf(u.type, u.name) ? (
                              <div
                                className="h-14 w-14 rounded-md border border-slate-200 bg-rose-50 text-rose-600 flex items-center justify-center text-xs font-bold">
                                PDF
                              </div>
                            ) : (
                              <div
                                className="h-14 w-14 rounded-md border border-slate-200 bg-slate-50 text-slate-500 flex items-center justify-center text-xl">
                                📄
                              </div>
                            )}
                          </div>
                          <div className="min-w-0 flex-1">
                            <div className="text-sm font-semibold text-slate-800 truncate">{u.name}</div>
                            <div className="text-[11px] text-slate-500">
                              {formatBytes(u.size)} • {new Date(u.uploadedAt).toLocaleTimeString()}
                            </div>
                            {isSel && <div className="mt-1 text-[11px] text-emerald-700 font-medium">Selected</div>}
                          </div>
                          <div className="self-start flex items-center gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); window.open(u.url, '_blank', 'noopener,noreferrer') }}
                              className="text-[11px] px-2 py-1 rounded-md border bg-white hover:bg-slate-50"
                              type="button"
                            >
                              Open
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); removeUpload(u.id) }}
                              className="text-[11px] px-2 py-1 rounded-md border bg-white hover:bg-rose-50 hover:text-rose-600"
                              type="button"
                              aria-label={`Remove ${u.name}`}
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      )
                    })}
                  </div>
                </div>
              )}
            </div>

            {/* Output */}
            <div
              className="card p-0 overflow-hidden bg-white/90 backdrop-blur border border-emerald-100 relative"
              aria-busy={isBusy}
              aria-live="polite"
            >
              {/* Tabs */}
              <div className="flex items-center gap-2 border-b bg-white/60 px-4 pt-4">
                <button
                  className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                    tab === 'ocr' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary hover:bg-primary-light'
                  }`}
                  onClick={() => setTab('ocr')}
                  type="button"
                  disabled={!ocrResult || isBusy}
                  title={!ocrResult ? 'Run OCR to view' : 'Original OCR text'}
                >
                  Original
                </button>
                <button
                  className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                    tab === 'corrected' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary hover:bg-primary-light'
                  }`}
                  onClick={() => setTab('corrected')}
                  type="button"
                  disabled={!hasCorrection || isBusy}
                  title={!hasCorrection ? 'Apply Correction to view' : 'Corrected text'}
                >
                  Corrected
                </button>

                <button
                  className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                    tab === 'structured' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary hover:bg-primary-light'
                  }`}
                  onClick={() => setTab('structured')}
                  type="button"
                  disabled={!structured || isBusy}
                  title={!structured ? 'Available only when structured_data present' : 'Structured data (JSON)'}
                >
                  Structured Data
                </button>

                <button
                  className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                    tab === 'diff' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary hover:bg-primary-light'
                  }`}
                  onClick={() => setTab('diff')}
                  type="button"
                  disabled={!hasCorrection || isBusy}
                  title={!hasCorrection ? 'Apply Correction to view' : 'Word-level differences'}
                >
                  Diff
                </button>

                <button
                  className={`ml-auto px-3 py-2 rounded-t-xl text-sm font-semibold ${
                    tab === 'preview' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary hover:bg-primary-light'
                  }`}
                  onClick={() => setTab('preview')}
                  type="button"
                  title="HTML preview of the current best text"
                  disabled={isBusy}
                >
                  Preview
                </button>
              </div>

              {/* SCANNING OVERLAY */}
              <div
                className={`absolute inset-0 transition-opacity duration-300 ${isBusy ? 'opacity-100' : 'opacity-0 pointer-events-none'}`}
              >
                <div className="absolute inset-4 rounded-xl bg-white/92 border border-emerald-100 shadow-inner"/>
                <div
                  className="absolute inset-4 rounded-xl overflow-hidden"
                  style={{
                    backgroundImage:
                      'repeating-linear-gradient(180deg, rgba(2,6,23,0.05) 0, rgba(2,6,23,0.05) 1px, transparent 1px, transparent 8px)'
                  }}
                />
                <div className="absolute inset-4 rounded-xl overflow-hidden">
                  <div className="absolute left-0 right-0 h-24 -top-24 bg-gradient-to-b from-emerald-300/50 via-emerald-400/25 to-transparent blur-xl animate-[scanY_2.8s_linear_infinite]"/>
                </div>
                <div className="absolute inset-6 pointer-events-none">
                  <div className="h-8 w-8 border-t-4 border-l-4 border-emerald-400/70 rounded-tl-xl animate-[cornerDance_3s_ease-in-out_infinite]"/>
                  <div className="absolute top-0 right-0 h-8 w-8 border-t-4 border-r-4 border-emerald-400/70 rounded-tr-xl animate-[cornerDance_3s_ease-in-out_infinite_400ms]"/>
                  <div className="absolute bottom-0 left-0 h-8 w-8 border-b-4 border-l-4 border-emerald-400/70 rounded-bl-xl animate-[cornerDance_3s_ease-in-out_infinite_800ms]"/>
                  <div className="absolute bottom-0 right-0 h-8 w-8 border-b-4 border-r-4 border-emerald-400/70 rounded-br-xl animate-[cornerDance_3s_ease-in-out_infinite_1200ms]"/>
                </div>
                <div className="absolute left-8 right-8 bottom-8 space-y-2">
                  <div className="h-3 rounded bg-slate-200 animate-shimmer"/>
                  <div className="h-3 w-11/12 rounded bg-slate-200 animate-shimmer [animation-delay:120ms]"/>
                  <div className="h-3 w-10/12 rounded bg-slate-200 animate-shimmer [animation-delay:240ms]"/>
                </div>
              </div>

              {/* Body */}
              <div className="p-6 relative">
                {!ocrResult && !corrected && !structured ? (
                  <div className="text-gray-500">No output yet. Run OCR and/or apply correction.</div>
                ) : tab === 'ocr' ? (
                  <pre className="whitespace-pre-wrap text-sm bg-gray-50 border border-gray-200 rounded-2xl p-4 overflow-auto">
{ocrResult}
                  </pre>
                ) : tab === 'corrected' ? (
                  hasCorrection ? (
                    <pre className="whitespace-pre-wrap text-sm bg-emerald-50 border border-emerald-200 rounded-2xl p-4 overflow-auto">
{corrected}
                    </pre>
                  ) : (
                    <div className="text-gray-500">No corrected text yet. Click “Apply Correction”.</div>
                  )
                ) : tab === 'structured' ? (
                  structured ? (
                    <StructuredView data={structured as any} meta={meta}/>
                  ) : (
                    <div className="text-gray-500">No structured data was returned.</div>
                  )
                ) : tab === 'diff' ? (
                  hasCorrection ? (
                    <DiffView original={ocrResult} corrected={corrected}/>
                  ) : (
                    <div className="text-gray-500">No correction applied yet.</div>
                  )
                ) : (
                  <iframe
                    title="Markdown Preview"
                    className="w-full h-[60vh] border border-gray-200 rounded-2xl"
                    srcDoc={htmlPreview}
                  />
                )}
              </div>

              {/* If structured_data exists AND correction applied, also show the diff panel below (per your spec “diff in below”) */}
              {structured && hasCorrection && (
                <div className="px-6 pb-6">
                  <div className="h-px bg-slate-200 my-2" />
                  <DiffView original={ocrResult} corrected={corrected}/>
                </div>
              )}
            </div>
          </div>

          {/* Chat */}
          <div className="lg:col-span-1 lg:sticky lg:top-20 h-fit">
            <ChatPanel context={corrected || ocrResult}/>
          </div>
        </div>
      </div>

      {/* === PREVIEW MODAL (Rotate / Zoom / Invert) === */}
      {showPreview && selected && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40" role="dialog" aria-modal="true" aria-label="Document preview">
          <div className="relative w-full max-w-6xl h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
            {/* Toolbar */}
            <div className="flex items-center gap-3 px-4 py-3 border-b bg-white/80 backdrop-blur">
              <div className="font-semibold text-slate-800 truncate">{selected.name}</div>
              <div className="ml-auto flex items-center gap-2 text-sm">
                <button className="px-2 py-1 rounded-md border hover:bg-slate-50" onClick={() => setZoom(z => Math.max(25, z - 10))} type="button">−</button>
                <div className="w-40">
                  <input type="range" min={25} max={250} step={5} value={zoom} onChange={e => setZoom(parseInt(e.target.value))} className="w-full" aria-label="Zoom" />
                </div>
                <button className="px-2 py-1 rounded-md border hover:bg-slate-50" onClick={() => setZoom(z => Math.min(250, z + 10))} type="button">+</button>
                <span className="w-12 text-right text-slate-600">{zoom}%</span>
                <div className="h-6 w-px bg-slate-200 mx-1"/>
                <button className="px-2 py-1 rounded-md border hover:bg-slate-50" onClick={() => setRotation(r => (r - 90 + 360) % 360)} type="button" title="Rotate left">⟲</button>
                <button className="px-2 py-1 rounded-md border hover:bg-slate-50" onClick={() => setRotation(r => (r + 90) % 360)} type="button" title="Rotate right">⟳</button>
                <label className="ml-2 inline-flex items-center gap-2 text-slate-700">
                  <input type="checkbox" checked={invert} onChange={() => setInvert(v => !v)}/>
                  Invert
                </label>
                <a href={selected.url} target="_blank" rel="noreferrer" className="ml-2 px-2 py-1 rounded-md border hover:bg-slate-50">Open in new tab</a>
                <button className="ml-2 px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700" onClick={() => setShowPreview(false)} type="button">Close</button>
              </div>
            </div>

            {/* Canvas */}
            <div className="flex-1 overflow-auto bg-slate-50">
              <div className={`min-h-full w-full flex items-center justify-center p-6 ${invert ? 'invert' : ''}`}>
                {isImage(selected.type, selected.name) ? (
                  <img
                    src={selected.url}
                    alt={selected.name}
                    className="rounded-lg shadow border border-slate-200 max-w-none"
                    style={{ transform: `scale(${zoom / 100}) rotate(${rotation}deg)`, transformOrigin: 'center' }}
                  />
                ) : isPdf(selected.type, selected.name) ? (
                  <div className="rounded-lg shadow border border-slate-200 bg-white overflow-auto"
                       style={{ transform: `scale(${zoom / 100}) rotate(${rotation}deg)`, transformOrigin: 'center' }}>
                    <iframe title="PDF preview" src={selected.url} style={{ width: isRotatedPortrait ? '1200px' : '900px', height: isRotatedPortrait ? '900px' : '1200px', border: '0' }}/>
                  </div>
                ) : (
                  <div className="text-center text-slate-600">
                    <div className="text-5xl mb-4">📄</div>
                    <div className="font-semibold">{selected.name}</div>
                    <div className="text-sm text-slate-500 mt-1">Preview not available. Use “Open in new tab”.</div>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Keyframes */}
      <style>{`
        @keyframes huerotate { 0% { filter: hue-rotate(0deg) } 100% { filter: hue-rotate(360deg) } }
        @keyframes sweep { 0% { transform: translateY(0); opacity:.9; } 60% { transform: translateY(24px); opacity:.7; } 100% { transform: translateY(0); opacity:.9; }
        }
        @keyframes scanY { 0% { transform: translateY(-20%); opacity:.92 } 100% { transform: translateY(120%); opacity:.65 } }
        @keyframes shimmerKf { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        .animate-shimmer { background-image: linear-gradient(90deg, rgba(226,232,240,0.6) 25%, rgba(203,213,225,0.9) 37%, rgba(226,232,240,0.6) 63%); background-size: 400% 100%; animation: shimmerKf 1.6s infinite linear; }
        @keyframes pulseSoft { 0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.45) } 70% { box-shadow: 0 0 0 14px rgba(16,185,129,0) } 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0) } }
        .animate-pulse-soft { animation: pulseSoft 1.8s ease-out infinite; }
        @keyframes cornerDance { 0%,100% { transform: translate(0,0) } 50% { transform: translate(2px, -2px) } }
      `}</style>
    </section>
  )
}
