import {Link} from 'react-router-dom'
import {
    FaBolt,
    FaShieldAlt,
    FaLanguage,
    FaImage,
    FaComments,
    FaGithub
} from 'react-icons/fa'
import {
    FaArrowRight,
    FaWandMagicSparkles
} from 'react-icons/fa6'
import {useMemo} from "react";
import PricingSection from "../components/PricingSection";


/**
 * A love-at-first-sight Landing page:
 * - Aurora gradient + animated blobs + soft grain
 * - Clean hero with product badge, CTA trio
 * - Live “terminal” card that previews a curl request
 * - Feature grid with iconography
 * - 3-step timeline (Upload → OCR → Chat)
 * - Trust bar + tiny footer
 *
 * Pure Tailwind + a few inline keyframes. No extra libs beyond react-icons.
 */

export default function Landing() {
    const CURL = useMemo(
        () =>
            `curl -X POST https://api.example.com/ocr \\
  -H "Authorization: Bearer <API_KEY>" \\
  -H "Content-Type: application/json" \\
  -d '{
    "fileBase64": "<...>",
    "language": "AUTO_DETECT",
    "documentType": "IMAGE",
    "provider": "MISTRAL:ocr-latest",
    "prompt": "Return Markdown with headings and tables."
  }'`,
        []
    )

    return (
        <section className="relative min-h-[100svh] overflow-hidden">
            {/* === BACKGROUND ART === */}
            <div className="pointer-events-none absolute inset-0 -z-50">
                {/* Aurora */}
                <div
                    className="absolute inset-0"
                    style={{
                        background:
                            'conic-gradient(from 200deg at 50% 50%, #22c55e, #06b6d4, #8b5cf6, #22c55e)',
                        filter: 'saturate(1.05) brightness(1.06)',
                        animation: 'huerotate 22s linear infinite'
                    }}
                />
                {/* Soft blobs */}
                <div
                    className="absolute -top-40 left-1/2 h-[80vmin] w-[80vmin] -translate-x-1/2 rounded-full bg-emerald-300/25 blur-[100px]"/>
                <div
                    className="absolute -bottom-40 right-10 h-[60vmin] w-[60vmin] rounded-full bg-cyan-300/25 blur-[90px]"/>
                <div
                    className="absolute top-1/3 -left-10 h-[55vmin] w-[55vmin] rounded-full bg-violet-400/25 blur-[90px]"/>
                {/* Dot grid + grain */}
                <div
                    className="absolute inset-0 opacity-25 mix-blend-overlay"
                    style={{
                        backgroundImage:
                            'radial-gradient(rgba(255,255,255,0.16) 1px, transparent 1px)',
                        backgroundSize: '16px 16px'
                    }}
                />
                <div
                    className="absolute inset-0 opacity-[0.06]"
                    style={{
                        backgroundImage:
                            'repeating-linear-gradient(180deg, rgba(0,0,0,.45) 0, rgba(0,0,0,.45) 1px, transparent 1px, transparent 7px)'
                    }}
                />
            </div>

            <div className="max-w-7xl mx-auto px-4 py-12 md:py-16">
                {/* === HERO === */}
                <div className="relative grid lg:grid-cols-2 gap-8 items-center">
                    {/* Left: Copy */}
                    <div className="order-2 lg:order-1">
                        <div
                            className="inline-flex items-center gap-2 rounded-full border border-white/50 bg-white/70 backdrop-blur px-3 py-1 text-xs font-semibold text-emerald-700 shadow-sm">
                            <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"/>
                            LLM-Powered OCR
                        </div>

                        <h1 className="mt-4 text-4xl md:text-5xl font-black tracking-tight text-slate-900 leading-tight">
                            Visionary <span className="text-emerald-600">AI</span> OCR Studio
                        </h1>

                        <p className="mt-3 text-slate-600 max-w-2xl">
                            Extract structured data from PDFs and images—tables, forms, letters, receipts/invoices,
                            recipes, and more. Refine with AI, then chat with your docs. Deploy in-house or in the
                            cloud—all in a fast, extensible React/Vite studio.
                        </p>


                        {/* Badges */}
                        <div className="mt-5 flex flex-wrap gap-3">
                            <span className="badge"><FaBolt className="mr-2"/> Blazing Fast</span>
                            <span className="badge"><FaShieldAlt className="mr-2"/> Privacy-first</span>
                            <span className="badge">
                              <FaLanguage className="mr-2"/>
                              Multilingual (Nepali/English, etc.)
                            </span>
                            <span className="badge"><FaLanguage className="mr-2"/> 100+ languages</span>
                            <span className="badge"><FaImage className="mr-2"/> PDF / Image</span>
                        </div>

                        {/* CTAs */}
                        <div className="mt-6 flex flex-wrap gap-3">
                            <Link to="/demo" className="btn inline-flex items-center gap-2">
                                Try Demo <FaArrowRight/>
                            </Link>
                            <Link to="/login" className="btn-outline">
                                Go to Dashboard
                            </Link>
                            <Link to="/docs" className="btn-ghost">
                                Read Docs
                            </Link>
                        </div>
                    </div>

                    {/* Right: Visual / Terminal */}
                    <div className="order-1 lg:order-2">
                        <div className="relative">
                            {/* floating logo card */}
                            <div className="absolute -top-6 -left-4 rotate-[-3deg] hidden md:block">
                                <div
                                    className="rounded-2xl border border-white/60 bg-white/80 backdrop-blur px-4 py-3 shadow-lg">
                                    <div className="flex items-center gap-3">
                                        <img
                                            src="/src/assets/images/logo.png"
                                            alt="logo"
                                            className="h-8 w-8 rounded-xl"
                                        />
                                        <div className="text-sm font-bold text-slate-700">Visionary AI</div>
                                    </div>
                                </div>
                            </div>

                            {/* terminal card */}
                            <div
                                className="rounded-2xl border border-white/60 bg-white/80 backdrop-blur shadow-[0_30px_120px_rgba(16,185,129,0.20)]">
                                <div className="px-4 py-2 flex items-center gap-2 border-b">
                                    <span className="h-2.5 w-2.5 rounded-full bg-red-400"/>
                                    <span className="h-2.5 w-2.5 rounded-full bg-yellow-400"/>
                                    <span className="h-2.5 w-2.5 rounded-full bg-green-400"/>
                                    <span className="ml-2 text-xs text-slate-500">curl — demo</span>
                                </div>
                                <pre
                                    className="p-4 text-xs md:text-sm leading-relaxed overflow-auto whitespace-pre-wrap bg-slate-900 text-slate-100 rounded-b-2xl">
{CURL}
                </pre>
                            </div>

                            {/* shimmer sweep */}
                            <div
                                className="pointer-events-none absolute inset-x-10 -bottom-6 h-16 bg-gradient-to-b from-emerald-300/30 via-emerald-300/10 to-transparent blur-xl animate-[sweep_6s_linear_infinite]"/>
                        </div>
                    </div>
                </div>

                {/* === FEATURES === */}
                <div className="mt-14 grid md:grid-cols-3 gap-6">
                    {[
                        {
                            title: 'Generic OCR',
                            desc: 'Turn scans into structured data across formats — tables, forms, letters, and receipts — with clean Markdown when you want it.',
                            icon: <FaWandMagicSparkles className="text-emerald-600"/>
                        },
                        {
                            title: 'LLM Correction',
                            desc: 'Refine structure, fix OCR noise, and normalize fields using your chosen LLM.',
                            icon: <FaWandMagicSparkles className="text-emerald-600"/>
                        },
                        {
                            title: 'Chat with Docs',
                            desc: 'Ask questions about the extracted text. Get answers with citations & context.',
                            icon: <FaComments className="text-emerald-600"/>
                        }
                    ].map((f, i) => (
                        <div key={i} className="card p-6 hover:shadow-xl transition-shadow">
                            <div className="text-2xl">{f.icon}</div>
                            <div className="mt-3 font-bold">{f.title}</div>
                            <div className="text-sm text-slate-600">{f.desc}</div>
                        </div>
                    ))}
                </div>

                {/* === TIMELINE === */}
                <div className="mt-14 card p-6 md:p-8">
                    <h3 className="text-xl font-extrabold mb-4">How it works — in 3 steps</h3>
                    <ol className="relative border-s border-emerald-200 pl-6 space-y-6">
                        <li className="relative">
                            <span className="absolute -left-[11px] top-1.5 h-5 w-5 rounded-full"></span>
                            <div className="font-bold">Upload</div>
                            <p className="text-sm text-slate-600">
                                Drag & drop PDFs or images. We support common formats and multi-page files.
                            </p>
                        </li>
                        <li className="relative">
                            <span className="absolute -left-[11px] top-1.5 h-5 w-5 rounded-full"></span>
                            <div className="font-bold">Extract</div>
                            <p className="text-sm text-slate-600">
                                Run OCR with your selected provider/model. Optionally apply an LLM correction pass.
                            </p>
                        </li>
                        <li className="relative">
                            <span className="absolute -left-[11px] top-1.5 h-5 w-5 rounded-full"></span>
                            <div className="font-bold">Ask</div>
                            <p className="text-sm text-slate-600">
                                Use the built-in chat to query your results. Summaries, fields, tables—instantly.
                            </p>
                        </li>
                    </ol>
                    <div className="mt-6 flex flex-wrap gap-3">
                        <Link to="/demo" className="btn">Try the Demo</Link>
                        <Link to="/login" className="btn-outline">Go to Dashboard</Link>
                        <a
                            href="https://github.com/your-org/your-repo"
                            target="_blank"
                            rel="noreferrer"
                            className="btn-ghost inline-flex items-center gap-2"
                        >
                            <FaGithub/> Star on GitHub
                        </a>
                    </div>
                </div>

                {/* === TRUST BAR === */}
                <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-4 items-center opacity-80">
                    {['Mistral', 'Gemini', 'Ollama', 'VLLM'].map((n, i) => (
                        <div
                            key={i}
                            className="rounded-xl border border-white/60 bg-white/70 backdrop-blur px-4 py-3 text-center text-sm font-semibold text-slate-600"
                        >
                            {n} Ready
                        </div>
                    ))}
                </div>

                <div className="max-w-7xl mx-auto px-4">
                    <PricingSection/>
                </div>
                {/* === FOOTER MINI === */}
                <footer className="mt-10 text-center text-xs text-slate-500">
                    © {new Date().getFullYear()} Visionary AI. Built with ❤️ for intelligent document workflows.
                </footer>
            </div>

            {/* Keyframes */}
            <style>{`
        @keyframes huerotate { 0% { filter: hue-rotate(0deg) } 100% { filter: hue-rotate(360deg) } }
        @keyframes sweep {
          0% { transform: translateY(0); opacity: .9; }
          70% { transform: translateY(-30px); opacity: .6; }
          100% { transform: translateY(0); opacity: .9; }
        }
        @media (prefers-reduced-motion: reduce) {
          * { animation: none !important; }
        }
      `}</style>
        </section>
    )
}
