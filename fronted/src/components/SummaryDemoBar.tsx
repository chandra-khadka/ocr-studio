import {memo} from "react";
import {FiGlobe, FiFileText} from "react-icons/fi";
import {Link} from "react-router-dom";

type Props = {
    language: string;
    documentType: string;
    ocrProvider: string;
    ocrModel?: string;
    correctionProvider: string;
    correctionModel?: string;
    fileName?: string;
    onReset: () => void;
    onRunOCR: () => void;
    canRun: boolean;
    loading?: boolean;
};

const SummaryDemoBar = memo(function SummaryDemoBar({
                                                        language,
                                                        documentType,
                                                    }: Props) {
    return (
        <div className="sticky top-0 z-10 -mx-4 mb-6">
            <div className="mx-auto max-w-7xl px-4">
                <div className="mt-2 rounded-2xl border border-gray-100 bg-white/85 backdrop-blur shadow-sm">
                    {/* Divider */}
                    <div className="h-px w-full bg-gray-100"/>

                    {/* Bottom row: compact chips + CTA (mobile-first) */}
                    <div className="flex flex-wrap items-center gap-2 px-3 sm:px-4 py-2.5">
            <span
                className="inline-flex items-center gap-1.5 rounded-full bg-primary-light text-primary px-2.5 py-1 text-[11px] font-semibold">
              <FiGlobe className="opacity-80"/> {language}
            </span>

                        <span
                            className="inline-flex items-center gap-1.5 rounded-full bg-gray-50 text-gray-700 px-2.5 py-1 text-[11px] font-semibold">
              <FiFileText className="opacity-80"/> {documentType}
            </span>

                        {/* Button: full width on mobile, right-aligned on sm+ */}
                        <Link
                            to="/home"
                            title="Try Premium — OCR for faster retrieval"
                            aria-label="Try Premium — OCR for faster retrieval"
                            className="w-full sm:w-auto sm:ml-auto px-4 py-2 rounded-xl text-sm font-semibold bg-primary text-white hover:bg-primary-dark focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 shadow-md transition inline-flex flex-col leading-tight text-center"
                        >
                            <span className="text-sm font-semibold">Try Premium</span>
                            <span className="text-[10px] font-medium opacity-90 -mt-0.5">
                OCR for faster retrieval
              </span>
                        </Link>
                    </div>
                </div>
            </div>
        </div>
    );
});

export default SummaryDemoBar;
