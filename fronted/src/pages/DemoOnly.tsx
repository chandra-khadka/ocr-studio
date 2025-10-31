import React, {useEffect, useMemo, useState} from "react";
import {Eye} from "lucide-react";

import FileUploader from "../components/FileUploader";
import {
    listCorrectionModels,
    listOCRModels,
    runCorrection,
    runOCRPremium,
} from "../services/api";
import {
    CorrectionProvider,
    DocumentFormat,
    DocumentType,
    Language,
    OCRProvider,
} from "../types/enums";
import SummaryDemoBar from "../components/SummaryDemoBar";

/* ================= Markdown → HTML (same lightweight preview) ================= */
function mdToHtml(md: string) {
    let s = (md ?? "").replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    s = s.replace(/```([\s\S]*?)```/g, (_m, p1) => `<pre class="md-pre"><code>${p1}</code></pre>`);
    s = s.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');
    s = s.replace(/^###### (.*)$/gm, "<h6>$1</h6>");
    s = s.replace(/^##### (.*)$/gm, "<h5>$1</h5>");
    s = s.replace(/^#### (.*)$/gm, "<h4>$1</h4>");
    s = s.replace(/^### (.*)$/gm, "<h3>$1</h3>");
    s = s.replace(/^## (.*)$/gm, "<h2>$1</h2>");
    s = s.replace(/^# (.*)$/gm, "<h1>$1</h1>");
    s = s.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    s = s.replace(/\*([^*]+)\*/g, "<em>$1</em>");
    s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
    s = s.replace(/^(?:-|\*) (.*)$/gm, "<li>$1</li>");
    s = s.replace(/(<li>[\s\S]*?<\/li>)/g, "<ul>$1</ul>");
    s = s
        .split(/\n{2,}/)
        .map((b) => (/^\s*</.test(b.trim()) ? b : `<p>${b.trim().replace(/\n/g, "<br/>")}</p>`))
        .join("\n");
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
  </style>`;
    return `<!doctype html><meta charset="utf-8"><title>Preview</title>${css}<article>${s}</article>`;
}

/* ================= Structured view (FIX: include this component) ================= */
function StructuredView({data, meta}: { data: Record<string, any>, meta?: any }) {
    if (!data) return null;
    const rows = Object.entries(data);
    const jsonPretty = useMemo(() => JSON.stringify(data, null, 2), [data]);

    const copyJson = async () => {
        try {
            await navigator.clipboard.writeText(jsonPretty);
        } catch {/* noop */
        }
    };
    const downloadJson = () => {
        const blob = new Blob([jsonPretty], {type: "application/json"});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = "structured_data.json";
        a.click();
        URL.revokeObjectURL(url);
    };

    return (
        <div className="space-y-4">
            <div className="rounded-2xl border border-emerald-100 overflow-x-auto">
                <table className="w-full text-sm min-w-[560px]">
                    <thead className="bg-emerald-50">
                    <tr>
                        <th className="text-left px-3 py-2 w-56">Field</th>
                        <th className="text-left px-3 py-2">Value</th>
                    </tr>
                    </thead>
                    <tbody>
                    {rows.map(([k, v]) => (
                        <tr key={k} className="border-t">
                            <td className="px-3 py-2 font-medium text-slate-700 break-words">{k}</td>
                            <td className="px-3 py-2 text-slate-800 break-words">
                                {v === null || v === undefined || v === "" ? (
                                    <span className="text-slate-400">—</span>
                                ) : typeof v === "object" ? (
                                    <pre className="whitespace-pre-wrap">{JSON.stringify(v, null, 2)}</pre>
                                ) : (
                                    String(v)
                                )}
                            </td>
                        </tr>
                    ))}
                    </tbody>
                </table>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white">
                <div className="flex items-center justify-between px-3 py-2 border-b">
                    <div className="text-xs font-semibold text-slate-600">structured_data.json</div>
                    <div className="flex items-center gap-2">
                        <button className="text-xs px-2 py-1 rounded-md border bg-white hover:bg-slate-50"
                                onClick={copyJson} type="button">
                            Copy
                        </button>
                        <button className="text-xs px-2 py-1 rounded-md border bg-white hover:bg-slate-50"
                                onClick={downloadJson} type="button">
                            Download
                        </button>
                    </div>
                </div>
                <pre className="p-3 text-xs overflow-auto max-h-[50vh]">{jsonPretty}</pre>
            </div>

            {meta && (
                <div className="rounded-2xl border border-slate-200 bg-slate-50 p-3">
                    <div className="text-xs font-semibold text-slate-700 mb-2">Meta</div>
                    <div className="grid sm:grid-cols-2 gap-2 text-sm">
                        <div><span className="text-slate-500">ocr_provider:</span> <span
                            className="font-medium">{meta.ocr_provider ?? "—"}</span></div>
                        <div><span className="text-slate-500">correction_provider:</span> <span
                            className="font-medium">{meta.correction_provider ?? "—"}</span></div>
                        <div><span className="text-slate-500">document_type:</span> <span
                            className="font-medium">{meta.document_type ?? "—"}</span></div>
                        <div><span className="text-slate-500">language_detected:</span> <span
                            className="font-medium">{meta.language_detected ?? "—"}</span></div>
                        <div><span className="text-slate-500">confidence:</span> <span
                            className="font-medium">{meta.confidence ?? "—"}</span></div>
                    </div>
                </div>
            )}
        </div>
    );
}

/* ================= Small utils ================= */
function cleanMarkdownFence(s: string): string {
    if (!s) return s;
    let t = s.trim();
    t = t.replace(/^```(?:[a-z0-9_-]+)?\s*/i, "");
    t = t.replace(/\s*```$/i, "");
    t = t.replace(/^(?:markdown|md)\s*\n/i, "");
    return t.trim();
}

type UploadedFile = {
    id: string;
    name: string;
    url: string;
    b64: string;
    type: string;
    size: number;
    uploadedAt: number;
};

const isImage = (type: string, name: string) =>
    (type && type.startsWith("image/")) || /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(name);
const isPdf = (type: string, name: string) => type === "application/pdf" || /\.pdf$/i.test(name);
const formatBytes = (n: number) => {
    if (!n) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.min(Math.floor(Math.log(n) / Math.log(k)), sizes.length - 1);
    return `${(n / Math.pow(k, i)).toFixed(i ? 1 : 0)} ${sizes[i]}`;
};

/* ================= Defaults ================= */
const DEFAULT_LANGUAGE = Language.ENGLISH;
const DEFAULT_DOC_TYPE = DocumentType.GENERAL;
const DEFAULT_DOC_FORMAT = DocumentFormat.STANDARD;
const DEFAULT_OCR_PROVIDER = OCRProvider.GEMINI;
const DEFAULT_CORR_PROVIDER = CorrectionProvider.GEMINI;
const DEFAULT_PROMPT =
    "Return clean Markdown. If tables are detected, render as Markdown tables. Summarize key fields at top.";

/* ================= Progress steps ================= */
const OCR_STEPS = [
    "Detecting layout…",
    "Auto-detecting language…",
    "Enhancing contrast…",
    "Segmenting lines…",
    "Recognizing text…",
    "Reconstructing tables…",
    "Building Markdown…",
] as const;
const CORR_STEPS = [
    "Tokenizing text…",
    "Fixing OCR artifacts…",
    "Normalizing whitespace…",
    "Standardizing dates & numbers…",
    "Correcting spelling…",
    "Applying style/prompt…",
    "Rendering Markdown…",
] as const;

type ProgressMode = "idle" | "premium" | "correction";
type TabKey = "result" | "structured" | "preview";
type RunKind = "general" | "nepali";

export default function DemoOnly() {
    // Fixed config (hidden from UI)
    const [language] = useState(DEFAULT_LANGUAGE);
    const [documentType, setDocumentType] = useState(DEFAULT_DOC_TYPE);
    const [documentFormat] = useState(DEFAULT_DOC_FORMAT);
    const [ocrProvider] = useState<OCRProvider>(DEFAULT_OCR_PROVIDER);
    const [correctionProvider] = useState<CorrectionProvider>(DEFAULT_CORR_PROVIDER);
    const [prompt] = useState(DEFAULT_PROMPT);

    // Models auto-populated for the chosen providers
    const [selectedOCRModel, setSelectedOCRModel] = useState("");
    const [selectedCorrectionModel, setSelectedCorrectionModel] = useState("");

    // File + outputs
    const [fileName, setFileName] = useState("");
    const [fileB64, setFileB64] = useState("");

    // Internals kept (but not shown): raw OCR and corrected
    const [ocrResult, setOcrResult] = useState("");
    const [corrected, setCorrected] = useState("");

    // What the UI shows as the OCR result (always corrected when available)
    const [finalText, setFinalText] = useState("");

    // Structured data (only for Nepali OCR per requirement)
    const [structured, setStructured] = useState<Record<string, any> | null>(null);
    const [meta, setMeta] = useState<any>(null);

    // Track last run type to control visibility of Structured Data tab
    const [lastRun, setLastRun] = useState<RunKind | null>(null);

    // UI state
    const [tab, setTab] = useState<TabKey>("result");
    const [uploads, setUploads] = useState<UploadedFile[]>([]);
    const [selectedId, setSelectedId] = useState<string | null>(null);
    const selected = uploads.find((u) => u.id === selectedId) || null;
    const [showPreview, setShowPreview] = useState(false);
    const [zoom, setZoom] = useState(100);
    const [rotation, setRotation] = useState(0);
    const [invert, setInvert] = useState(false);
    const isRotatedPortrait = rotation % 180 !== 0;

    // Progress
    const [loading, setLoading] = useState(false);
    const [correcting, setCorrecting] = useState(false);
    const [progress, setProgress] = useState(0);
    const [progressMode, setProgressMode] = useState<ProgressMode>("idle");
    const activeSteps = progressMode === "correction" ? CORR_STEPS : OCR_STEPS;
    const currentStep = Math.min(Math.floor((progress / 100) * activeSteps.length), activeSteps.length - 1);
    const isBusy = loading || correcting;

    // Load first available models for defaults
    useEffect(() => {
        (async () => {
            const [ocr, corr] = await Promise.all([
                listOCRModels(ocrProvider),
                listCorrectionModels(correctionProvider as unknown as CorrectionProvider),
            ]);
            setSelectedOCRModel(ocr[1] || ocr[0] || "");
            setSelectedCorrectionModel(corr[0] || "");
        })();
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []);

    // Smooth progress
    useEffect(() => {
        const running = loading || correcting;
        if (!running) return;
        setProgress(0);
        const id = setInterval(() => {
            setProgress((p) => Math.min(96, p + 4 + Math.random() * 6 - (p > 70 ? 3 : 0)));
        }, 180);
        return () => clearInterval(id);
    }, [loading, correcting]);

    useEffect(() => {
        const running = loading || correcting;
        if (running) return;
        if (progressMode === "idle") return;
        setProgress(100);
        const t1 = setTimeout(() => setProgressMode("idle"), 400);
        const t2 = setTimeout(() => setProgress(0), 800);
        return () => {
            clearTimeout(t1);
            clearTimeout(t2);
        };
    }, [loading, correcting, progressMode]);

    // Upload handlers
    function onFile(file: File, b64: string) {
        setOcrResult("");
        setCorrected("");
        setFinalText("");
        setStructured(null);
        setMeta(null);
        setLastRun(null);
        setTab("result");

        const id = `${Date.now()}_${Math.random().toString(36).slice(2)}`;
        const url = URL.createObjectURL(file);
        const entry: UploadedFile = {
            id,
            name: file.name,
            url,
            b64,
            type: file.type || "",
            size: file.size || 0,
            uploadedAt: Date.now(),
        };
        setUploads((prev) => [entry, ...prev]);
        setSelectedId(id);
        setFileName(file.name);
        setFileB64(b64);
    }

    function selectUpload(u: UploadedFile) {
        setSelectedId(u.id);
        setFileName(u.name);
        setFileB64(u.b64);
        setOcrResult("");
        setCorrected("");
        setFinalText("");
        setStructured(null);
        setMeta(null);
        setLastRun(null);
        setTab("result");
    }

    function removeUpload(id: string) {
        setUploads((prev) => {
            const victim = prev.find((u) => u.id === id);
            if (victim) URL.revokeObjectURL(victim.url);
            const next = prev.filter((u) => u.id !== id);
            if (selectedId === id) {
                setSelectedId(next[0]?.id ?? null);
                if (next[0]) {
                    setFileName(next[0].name);
                    setFileB64(next[0].b64);
                } else {
                    setFileName("");
                    setFileB64("");
                    setOcrResult("");
                    setCorrected("");
                    setFinalText("");
                    setStructured(null);
                    setMeta(null);
                    setLastRun(null);
                }
            }
            return next;
        });
    }

    function clearUploads() {
        uploads.forEach((u) => URL.revokeObjectURL(u.url));
        setUploads([]);
        setSelectedId(null);
        setFileName("");
        setFileB64("");
        setOcrResult("");
        setCorrected("");
        setFinalText("");
        setStructured(null);
        setMeta(null);
        setLastRun(null);
        setTab("result");
    }

    function resetAll() {
        uploads.forEach((u) => URL.revokeObjectURL(u.url));
        setUploads([]);
        setSelectedId(null);
        setFileName("");
        setFileB64("");
        setOcrResult("");
        setCorrected("");
        setFinalText("");
        setStructured(null);
        setMeta(null);
        setLastRun(null);
        setTab("result");
        setShowPreview(false);
        setZoom(100);
        setRotation(0);
        setInvert(false);
    }

    async function doCorrectionFromText(inputText: string, docType: DocumentType) {
        const source = (inputText || "").trim();
        if (!source) return "";

        setProgressMode("correction");
        setCorrecting(true);
        try {
            const res = await runCorrection({
                text: source,
                model: `${correctionProvider}:${selectedCorrectionModel}`,
                prompt,
                document_type: docType,   // 👈 pass document type here
            });
            const raw = (res.corrected ?? res.text ?? "") as string;
            const cleaned = cleanMarkdownFence(raw);
            setCorrected(cleaned);
            setFinalText(cleaned); // UI shows only this
            setTab("result");
            return cleaned;
        } finally {
            setCorrecting(false);
        }
    }


    // Actions
    async function doOCRPremium(
        overrideDocType?: DocumentType,
        runKind: RunKind = "general"
    ) {
        if (!fileB64) return;
        setProgressMode("premium");
        setLoading(true);
        try {
            const res = await runOCRPremium({
                base64_image: fileB64,
                ocr_provider: String(ocrProvider),
                correction_provider: String(correctionProvider),
                document_type: String(overrideDocType ?? documentType),
                document_format: String(documentFormat),
                language: String(language),
                enable_json_parsing: true,
                use_segmentation: false,
                max_pdf_pages: 5,
                pdf_dpi: 300,
                custom_prompt: prompt,
                provider_config: {
                    ocr_model: selectedOCRModel,
                    correction_model: selectedCorrectionModel,
                },
            });

            const ocrText = (res?.text ?? "") as string;
            setOcrResult(ocrText);
            setMeta(res?.meta ?? null);
            setLastRun(runKind);

            if (runKind === "nepali") {
                setStructured((res?.structured_data ?? null) as any);
            } else {
                setStructured(null);
            }

            setLoading(false);

            const correctedText = await doCorrectionFromText(
                ocrText,
                overrideDocType ?? documentType
            );

            if (!correctedText?.trim()) {
                setFinalText(ocrText || "");
            }
        } finally {
            setLoading(false);
        }
    }

// 🇳🇵 Nepali Government docs
    async function doOCRNepali() {
        if (!fileB64 || isBusy) return;
        setDocumentType(DocumentType.GOVERNMENT_DOCUMENT);
        await doOCRPremium(DocumentType.GOVERNMENT_DOCUMENT, "nepali");
    }


    const htmlPreview = useMemo(() => mdToHtml(finalText || ""), [finalText]);
    const hasAnyOutput = !!(finalText || (lastRun === "nepali" && structured));

    return (
        <section className="relative min-h-[100svh] overflow-hidden">
            {/* Background */}
            <div className="pointer-events-none absolute inset-0 -z-50">
                <div
                    className="absolute inset-0"
                    style={{
                        background:
                            "conic-gradient(from 210deg at 60% 40%, #ecfdf5 0%, #ecfeff 22%, #f5f3ff 45%, #ecfdf5 100%)",
                        filter: "saturate(1.05) brightness(1.05)",
                        animation: "huerotate 28s linear infinite",
                    }}
                />
                <div
                    className="absolute -top-40 left-1/2 h-[80vmin] w-[80vmin] -translate-x-1/2 rounded-full bg-emerald-300/20 blur-[110px]"/>
                <div
                    className="absolute bottom-[-25%] right-10 h-[60vmin] w-[60vmin] rounded-full bg-cyan-300/20 blur-[100px]"/>
                <div
                    className="absolute top-1/3 -left-10 h-[55vmin] w-[55vmin] rounded-full bg-violet-400/15 blur-[90px]"/>
                <div
                    className="absolute inset-0 opacity-20 mix-blend-overlay"
                    style={{
                        backgroundImage: "radial-gradient(rgba(2,6,23,0.1) 1px, transparent 1px)",
                        backgroundSize: "16px 16px",
                    }}
                />
                <div
                    className="absolute inset-0 opacity-[0.05]"
                    style={{
                        backgroundImage:
                            "repeating-linear-gradient(180deg, rgba(2,6,23,.35) 0, rgba(2,6,23,.35) 1px, transparent 1px, transparent 8px)",
                    }}
                />
                <div
                    className="absolute inset-x-0 top-10 h-24 bg-gradient-to-b from-emerald-300/40 via-emerald-300/20 to-transparent blur-2xl animate-[sweep_8s_linear_infinite]"/>
            </div>

            <div className="max-w-7xl mx-auto px-3 sm:px-4 py-6 sm:py-8">
                {/* Summary (read-only config) */}
                <SummaryDemoBar
                    language={language}
                    documentType={documentType}
                    ocrProvider={String(ocrProvider)}
                    ocrModel={selectedOCRModel}
                    correctionProvider={String(correctionProvider)}
                    correctionModel={selectedCorrectionModel}
                    fileName={fileName}
                    onReset={resetAll}
                    onRunOCR={() => doOCRPremium(undefined, "general")}
                    canRun={!!fileB64 && !loading}
                    loading={loading}
                />

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 sm:gap-6">
                    <div className="lg:col-span-2 space-y-6">
                        {/* Upload card only */}
                        <div className="card p-5 sm:p-6 bg-white/90 backdrop-blur border border-emerald-100">
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

                            <div className="mt-4 grid grid-cols-1 sm:flex sm:flex-wrap gap-3">
                                <button
                                    className={`btn w-full sm:w-auto ${!fileB64 ? "opacity-60 cursor-not-allowed" : ""} ${
                                        !isBusy && fileB64 ? "shadow-[0_0_0_0_rgba(16,185,129,0.6)] animate-pulse-soft" : ""
                                    }`}
                                    onClick={() => doOCRPremium(undefined, "general")}
                                    disabled={!fileB64 || isBusy}
                                    type="button"
                                    title="Extract any document in any language (auto-corrected)"
                                    aria-label="Run Premium OCR for any document in any language"
                                >
                  <span className="block text-sm font-semibold leading-5">
                    {loading ? "⏳ Processing…" : "Run OCR"}
                  </span>
                                    <span className="block text-[11px] leading-4 opacity-80">
                    &nbsp; Auto-corrected • Any language
                  </span>
                                </button>

                                {/* 🇳🇵 Nepali-docs button */}
                                <button
                                    className={`btn w-full sm:w-auto ${!fileB64 ? "opacity-60 cursor-not-allowed" : ""}`}
                                    onClick={doOCRNepali}
                                    disabled={!fileB64 || isBusy}
                                    type="button"
                                    title="Extract Nepali Government documents only (auto-corrected)"
                                    aria-label="Run OCR for Nepali Government documents only"
                                >
                                    <span className="block text-sm font-semibold leading-5">Nepali OCR</span>
                                    <span className="block text-[11px] leading-4 opacity-80">&nbsp; Govt docs • Auto-corrected</span>
                                </button>

                                {/* Apply Correction button intentionally removed from UI */}
                                <button
                                    type="button"
                                    disabled={!selected || isBusy}
                                    onClick={() => {
                                        if (!selected) return;
                                        setShowPreview(true);
                                        setZoom(100);
                                        setRotation(0);
                                        setInvert(false);
                                    }}
                                    title="Preview the selected document"
                                    className={`
                    inline-flex items-center justify-center gap-2
                    w-full sm:w-auto px-4 py-2.5
                    rounded-xl border border-slate-300
                    bg-white text-slate-700 font-medium text-sm
                    shadow-sm transition-all
                    hover:border-emerald-400 hover:text-emerald-700 hover:shadow-md
                    active:scale-[0.98] disabled:opacity-50 disabled:cursor-not-allowed
                  `}
                                >
                                    <span>👁Preview</span>
                                    <br/>
                                </button>
                            </div>

                            {/* (optional) Show current doc type */}
                            <div className="mt-2 text-xs text-slate-600">
                <span className="px-2 py-1 rounded-md border bg-white">
                  Current document type:&nbsp;
                    <span className="font-semibold">{String(documentType)}</span>
                </span>
                            </div>

                            {/* Mini progress */}
                            {(loading || correcting) && (
                                <div className="mt-6 text-xs text-gray-700">
                                    <div className="mb-2 font-semibold">
                                        {progressMode === "correction" ? "Correcting… " : "Processing… "}
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
                                i < currentStep ? "bg-emerald-500" : i === currentStep ? "bg-amber-400" : "bg-slate-300"
                            }`}
                        />
                                                <span
                                                    className={`${i <= currentStep ? "text-slate-700" : "text-slate-400"}`}>{s}</span>
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {/* Gallery */}
                            {uploads.length > 0 && (
                                <div className="mt-8">
                                    <div className="mb-2 flex items-center justify-between">
                                        <h4 className="font-semibold text-sm text-slate-800">Uploaded documents</h4>
                                        <button
                                            className="text-xs text-slate-500 hover:text-rose-600 underline underline-offset-2"
                                            onClick={clearUploads}
                                            type="button"
                                        >
                                            Clear all
                                        </button>
                                    </div>
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                                        {uploads.map((u) => {
                                            const isSel = u.id === selectedId;
                                            return (
                                                <div
                                                    key={u.id}
                                                    onClick={() => selectUpload(u)}
                                                    role="button"
                                                    tabIndex={0}
                                                    onKeyDown={(e) => (e.key === "Enter" ? selectUpload(u) : undefined)}
                                                    className={`group relative flex gap-3 rounded-xl border p-3 bg-white/70 hover:bg-white transition cursor-pointer ${
                                                        isSel ? "border-emerald-300 ring-2 ring-emerald-200" : "border-slate-200"
                                                    }`}
                                                    title={u.name}
                                                    aria-current={isSel ? "true" : "false"}
                                                >
                                                    <div className="shrink-0">
                                                        {isImage(u.type, u.name) ? (
                                                            <img
                                                                src={u.url}
                                                                alt={u.name}
                                                                className="h-14 w-14 object-cover rounded-md border border-slate-200"
                                                            />
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
                                                        <div
                                                            className="text-sm font-semibold text-slate-800 truncate">{u.name}</div>
                                                        <div className="text-[11px] text-slate-500">
                                                            {formatBytes(u.size)} • {new Date(u.uploadedAt).toLocaleTimeString()}
                                                        </div>
                                                        {isSel && <div
                                                            className="mt-1 text-[11px] text-emerald-700 font-medium">Selected</div>}
                                                    </div>
                                                    <div className="self-start flex items-center gap-2">
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                window.open(u.url, "_blank", "noopener,noreferrer");
                                                            }}
                                                            className="text-[11px] px-2 py-1 rounded-md border bg-white hover:bg-slate-50"
                                                            type="button"
                                                        >
                                                            Open
                                                        </button>
                                                        <button
                                                            onClick={(e) => {
                                                                e.stopPropagation();
                                                                removeUpload(u.id);
                                                            }}
                                                            className="text-[11px] px-2 py-1 rounded-md border bg-white hover:bg-rose-50 hover:text-rose-600"
                                                            type="button"
                                                            aria-label={`Remove ${u.name}`}
                                                        >
                                                            Remove
                                                        </button>
                                                    </div>
                                                </div>
                                            );
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
                            {/* Tabs: Result | (Structured if Nepali) | Preview */}
                            <div
                                className="flex items-center gap-2 border-b bg-white/60 px-3 sm:px-4 pt-4 overflow-x-auto">
                                <button
                                    className={`px-3 py-2 rounded-t-xl text-sm font-semibold whitespace-nowrap ${
                                        tab === "result" ? "bg-primary text-white" : "text-gray-600 hover:text-primary hover:bg-primary-light"
                                    }`}
                                    onClick={() => setTab("result")}
                                    type="button"
                                    disabled={!finalText || isBusy}
                                    title={!finalText ? "Run OCR to view" : "Auto-corrected OCR result"}
                                >
                                    Result
                                </button>

                                <button
                                    className={`ml-auto px-3 py-2 rounded-t-xl text-sm font-semibold whitespace-nowrap ${
                                        tab === "preview" ? "bg-primary text-white" : "text-gray-600 hover:text-primary hover:bg-primary-light"
                                    }`}
                                    onClick={() => setTab("preview")}
                                    type="button"
                                    title="HTML preview of the current result"
                                    disabled={isBusy}
                                >
                                    Preview
                                </button>
                            </div>

                            {/* Scanning overlay */}
                            <div
                                className={`absolute inset-0 transition-opacity duration-300 ${
                                    isBusy ? "opacity-100" : "opacity-0 pointer-events-none"
                                }`}
                            >
                                <div
                                    className="absolute inset-4 rounded-xl bg-white/92 border border-emerald-100 shadow-inner"/>
                                <div
                                    className="absolute inset-4 rounded-xl overflow-hidden"
                                    style={{
                                        backgroundImage:
                                            "repeating-linear-gradient(180deg, rgba(2,6,23,0.05) 0, rgba(2,6,23,0.05) 1px, transparent 1px, transparent 8px)",
                                    }}
                                />
                                <div className="absolute inset-4 rounded-xl overflow-hidden">
                                    <div
                                        className="absolute left-0 right-0 h-24 -top-24 bg-gradient-to-b from-emerald-300/50 via-emerald-400/25 to-transparent blur-xl animate-[scanY_2.8s_linear_infinite]"/>
                                </div>
                                <div className="absolute inset-6 pointer-events-none">
                                    <div
                                        className="h-8 w-8 border-t-4 border-l-4 border-emerald-400/70 rounded-tl-xl animate-[cornerDance_3s_ease-in-out_infinite]"/>
                                    <div
                                        className="absolute top-0 right-0 h-8 w-8 border-t-4 border-r-4 border-emerald-400/70 rounded-tr-xl animate-[cornerDance_3s_ease-in-out_infinite_400ms]"/>
                                    <div
                                        className="absolute bottom-0 left-0 h-8 w-8 border-b-4 border-l-4 border-emerald-400/70 rounded-bl-xl animate-[cornerDance_3s_ease-in-out_infinite_800ms]"/>
                                    <div
                                        className="absolute bottom-0 right-0 h-8 w-8 border-b-4 border-r-4 border-emerald-400/70 rounded-br-xl animate-[cornerDance_3s_ease-in-out_infinite_1200ms]"/>
                                </div>
                                <div className="absolute left-8 right-8 bottom-8 space-y-2">
                                    <div className="h-3 rounded bg-slate-200 animate-shimmer"/>
                                    <div
                                        className="h-3 w-11/12 rounded bg-slate-200 animate-shimmer [animation-delay:120ms]"/>
                                    <div
                                        className="h-3 w-10/12 rounded bg-slate-200 animate-shimmer [animation-delay:240ms]"/>
                                </div>
                            </div>

                            {/* Body */}
                            <div className="p-5 sm:p-6 relative">
                                {!hasAnyOutput ? (
                                    <div className="text-gray-500">No output yet. Upload a file and run Premium
                                        OCR.</div>
                                ) : tab === "result" ? (
                                    <pre
                                        className="whitespace-pre-wrap text-sm bg-emerald-50 border border-emerald-200 rounded-2xl p-4 overflow-auto">
                    {finalText}
                  </pre>
                                ) : tab === "structured" ? (
                                    structured ? (
                                        <StructuredView data={structured as any} meta={meta}/>
                                    ) : (
                                        <div className="text-gray-500">No structured data was returned.</div>
                                    )
                                ) : (
                                    <iframe
                                        title="Markdown Preview"
                                        className="w-full h-[60vh] border border-gray-200 rounded-2xl"
                                        srcDoc={htmlPreview}
                                    />
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Sidebar */}
                    <div className="lg:col-span-1">
                        <div className="card p-5 sm:p-6 bg-white/85 backdrop-blur border border-emerald-100">
                            <h3 className="font-bold mb-2">How it works</h3>
                            <ol className="list-decimal list-inside text-sm text-slate-700 space-y-1">
                                <li>Upload a PDF or image.</li>
                                <li>
                                    Click <span className="font-medium">Run Premium OCR</span> (or <span
                                    className="font-medium">Nepali OCR</span>) — the text is
                                    <span className="font-medium"> auto-corrected</span>.
                                </li>
                                <li>
                                    Structured Data appears only for <span className="font-medium">Nepali OCR</span>.
                                </li>
                                <li>Use tabs to view Result, Structured JSON (if Nepali), or Preview.</li>
                            </ol>
                        </div>
                    </div>
                </div>
            </div>

            {/* Preview Modal */}
            {showPreview && selected && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4 bg-black/40"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Document preview"
                >
                    <div
                        className="
              relative w-full h-[100svh] sm:h-[88vh]
              max-w-none sm:max-w-6xl
              bg-white rounded-none sm:rounded-2xl shadow-2xl
              overflow-hidden flex flex-col
            "
                    >
                        {/* Header / Controls */}
                        <div
                            className="flex flex-wrap items-center gap-2 sm:gap-3 px-2 sm:px-4 py-2 sm:py-3 border-b bg-white/80 backdrop-blur">
                            <div className="font-semibold text-slate-800 truncate max-w-[60%] sm:max-w-none">
                                {selected.name}
                            </div>

                            {/* Controls (wrap on mobile) */}
                            <div className="ml-auto flex flex-wrap items-center gap-2 sm:gap-2.5 text-sm">
                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setZoom((z) => Math.max(25, z - 10))}
                                    type="button"
                                    aria-label="Zoom out"
                                    title="Zoom out"
                                >
                                    −
                                </button>

                                <div className="w-24 xs:w-28 sm:w-40">
                                    <input
                                        type="range"
                                        min={25}
                                        max={250}
                                        step={5}
                                        value={zoom}
                                        onChange={(e) => setZoom(parseInt(e.target.value))}
                                        className="w-full"
                                        aria-label="Zoom"
                                    />
                                </div>

                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setZoom((z) => Math.min(250, z + 10))}
                                    type="button"
                                    aria-label="Zoom in"
                                    title="Zoom in"
                                >
                                    +
                                </button>

                                <span className="w-12 text-right text-slate-600 hidden xs:inline">{zoom}%</span>

                                <div className="hidden sm:block h-6 w-px bg-slate-200 mx-1"/>

                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setRotation((r) => (r - 90 + 360) % 360)}
                                    type="button"
                                    title="Rotate left"
                                    aria-label="Rotate left"
                                >
                                    ⟲
                                </button>
                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setRotation((r) => (r + 90) % 360)}
                                    type="button"
                                    title="Rotate right"
                                    aria-label="Rotate right"
                                >
                                    ⟳
                                </button>

                                <label className="inline-flex items-center gap-2 text-slate-700">
                                    <input type="checkbox" checked={invert} onChange={() => setInvert((v) => !v)}/>
                                    Invert
                                </label>

                                <a href={selected.url} target="_blank" rel="noreferrer"
                                   className="px-2 py-1 rounded-md border hover:bg-slate-50">
                                    Open in new tab
                                </a>

                                <button
                                    className="px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                                    onClick={() => setShowPreview(false)}
                                    type="button"
                                >
                                    Close
                                </button>
                            </div>
                        </div>

                        {/* Body */}
                        <div className="flex-1 overflow-auto bg-slate-50 overscroll-contain">
                            <div
                                className={`min-h-full w-full flex items-center justify-center p-3 sm:p-6 ${invert ? "invert" : ""}`}>
                                {isImage(selected.type, selected.name) ? (
                                    <img
                                        src={selected.url}
                                        alt={selected.name}
                                        className="rounded-lg shadow border border-slate-200 max-w-[92vw] sm:max-w-none"
                                        style={{
                                            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                                            transformOrigin: "center"
                                        }}
                                    />
                                ) : isPdf(selected.type, selected.name) ? (
                                    <div
                                        className="rounded-lg shadow border border-slate-200 bg-white overflow-auto w-[92vw] sm:w-[900px] h-[70vh] sm:h-[75vh]"
                                        style={{
                                            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                                            transformOrigin: "center"
                                        }}
                                    >
                                        <iframe title="PDF preview" src={selected.url} className="w-full h-full"
                                                style={{border: 0}}/>
                                    </div>
                                ) : (
                                    <div className="text-center text-slate-600 px-4">
                                        <div className="text-5xl mb-3">📄</div>
                                        <div className="font-semibold">{selected.name}</div>
                                        <div className="text-sm text-slate-500 mt-1">Preview not available. Use “Open in
                                            new tab”.
                                        </div>
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
        @keyframes sweep { 0% { transform: translateY(0); opacity:.9; } 60% { transform: translateY(24px); opacity:.7; } 100% { transform: translateY(0); opacity:.9; } }
        @keyframes scanY { 0% { transform: translateY(-20%); opacity:.92 } 100% { transform: translateY(120%); opacity:.65 } }
        @keyframes shimmerKf { 0% { background-position: -200% 0; } 100% { background-position: 200% 0; } }
        .animate-shimmer { background-image: linear-gradient(90deg, rgba(226,232,240,0.6) 25%, rgba(203,213,225,0.9) 37%, rgba(226,232,240,0.6) 63%); background-size: 400% 100%; animation: shimmerKf 1.6s infinite linear; }
        @keyframes pulseSoft { 0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.45) } 70% { box-shadow: 0 0 0 14px rgba(16,185,129,0) } 100% { box-shadow: 0 0 0 0 rgba(16,185,129,0) } }
        .animate-pulse-soft { animation: pulseSoft 1.8s ease-out infinite; }
        @keyframes cornerDance { 0%,100% { transform: translate(0,0) } 50% { transform: translate(2px, -2px) } }
      `}</style>
        </section>
    );
}
