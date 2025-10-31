import {memo} from 'react'
import {FiGlobe, FiFileText, FiCpu, FiCheckCircle, FiUploadCloud, FiRotateCcw, FiPlay} from 'react-icons/fi'
import clsx from 'clsx'
import {Link} from "react-router-dom";

type Props = {
    language: string
    documentType: string
    ocrProvider: string
    ocrModel?: string
    correctionProvider: string
    correctionModel?: string
    fileName?: string
    onReset: () => void
    onRunOCR: () => void
    canRun: boolean
    loading?: boolean
}

function truncate(name?: string, max = 38) {
    if (!name) return ''
    return name.length > max ? name.slice(0, max - 3) + '...' : name
}

const SummaryBar = memo(function SummaryBar({
                                                language,
                                                documentType,
                                                ocrProvider,
                                                ocrModel,
                                                correctionProvider,
                                                correctionModel,
                                                fileName,
                                                onReset,
                                                onRunOCR,
                                                canRun,
                                                loading
                                            }: Props) {
    return (
        <div className="sticky top-0 z-10 -mx-4 mb-6">
            <div className="mx-auto max-w-7xl px-4">
                <div className="mt-2 rounded-2xl border border-gray-100 bg-white/85 backdrop-blur shadow-sm">
                    {/* Top row: title + primary actions */}
                    <div className="flex flex-wrap items-center gap-3 px-4 py-3">
                        <div className="flex items-center gap-2 text-sm text-gray-500">
                            <span className="font-extrabold text-gray-900 text-base">Dashboard</span>
                            <span className="text-gray-300">/</span>
                            <span className="hidden sm:inline">Session</span>
                        </div>

                        <div className="ml-auto flex items-center gap-2">
                            <button
                                type="button"
                                onClick={onReset}
                                className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-1.5 text-xs font-semibold text-gray-700 hover:text-primary hover:border-primary transition"
                                title="Reset all selections"
                            >
                                <FiRotateCcw/> Reset
                            </button>
                            <button
                                type="button"
                                onClick={onRunOCR}
                                disabled={!canRun || loading}
                                className={clsx(
                                    'inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold transition shadow-sm',
                                    canRun && !loading
                                        ? 'bg-primary text-white hover:bg-primary-dark'
                                        : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                )}
                                title="Run OCR on the selected file"
                            >
                                {loading ? (
                                    <>
                                        <span
                                            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/70 border-t-transparent"/>
                                        Processing…
                                    </>
                                ) : (
                                    <>
                                        <FiPlay/> Run OCR
                                    </>
                                )}
                            </button>

                            <button
                                type="button"
                                onClick={onRunOCR}
                                disabled={!canRun || loading}
                                className={clsx(
                                    'inline-flex items-center gap-2 rounded-xl px-3 py-1.5 text-xs font-semibold transition shadow-sm',
                                    canRun && !loading
                                        ? 'bg-primary text-white hover:bg-primary-dark'
                                        : 'bg-gray-200 text-gray-500 cursor-not-allowed'
                                )}
                                title="Run OCR on the selected file"
                            >
                                {loading ? (
                                    <>
                                        <span
                                            className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white/70 border-t-transparent"/>
                                        Processing…
                                    </>
                                ) : (
                                    <>
                                        <Link
                                            to="/home"
                                            title="Go to detailed site"
                                            className={`px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 shadow-md transition`}
                                        >
                                            Premium →
                                        </Link>
                                    </>
                                )}
                            </button>
                        </div>
                    </div>

                    {/* Divider */}
                    <div className="h-px w-full bg-gray-100"/>

                    {/* Bottom row: compact chips */}
                    <div className="flex flex-wrap items-center gap-2 px-4 py-2.5">
            <span
                className="inline-flex items-center gap-1.5 rounded-full bg-primary-light text-primary px-2.5 py-1 text-[11px] font-semibold">
              <FiGlobe className="opacity-80"/> {language}
            </span>
                        <span
                            className="inline-flex items-center gap-1.5 rounded-full bg-gray-50 text-gray-700 px-2.5 py-1 text-[11px] font-semibold">
              <FiFileText className="opacity-80"/> {documentType}
            </span>
                        <span
                            className="inline-flex items-center gap-1.5 rounded-full bg-gray-50 text-gray-700 px-2.5 py-1 text-[11px] font-semibold">
              <FiCpu className="opacity-80"/> OCR:&nbsp;
                            <span className="font-bold">{ocrProvider}</span>
                            {ocrModel ? <span className="text-gray-500">/ {ocrModel}</span> : null}
            </span>
                        <span
                            className="inline-flex items-center gap-1.5 rounded-full bg-gray-50 text-gray-700 px-2.5 py-1 text-[11px] font-semibold">
              <FiCheckCircle className="opacity-80"/> Correction:&nbsp;
                            <span className="font-bold">{correctionProvider}</span>
                            {correctionModel ? <span className="text-gray-500">/ {correctionModel}</span> : null}
            </span>
                        {fileName ? (
                            <span
                                className="inline-flex items-center gap-1.5 rounded-full bg-white border border-gray-200 text-gray-700 px-2.5 py-1 text-[11px] font-semibold"
                                title={fileName}
                            >
                <FiUploadCloud className="opacity-80"/> {truncate(fileName)}
              </span>
                        ) : null}
                    </div>
                </div>
            </div>
        </div>
    )
})

export default SummaryBar
