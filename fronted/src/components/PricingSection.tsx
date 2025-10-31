// src/components/PricingSection.tsx
import {useState} from "react"
import OrgContactModal from "./OrgContactModal"
import {FaCheck} from "react-icons/fa"

export default function PricingSection() {
    const [openOrg, setOpenOrg] = useState(false)

    return (
        <section id="pricing" className="mt-16">
            {/* Header */}
            <div className="text-center">
                <div
                    className="inline-flex items-center gap-2 rounded-full border bg-white px-3 py-1 text-xs font-semibold text-emerald-700 shadow-sm">
                    Simple pricing
                </div>
                <h2 className="mt-3 text-3xl md:text-4xl font-black tracking-tight">
                    Pricing that scales with you
                </h2>
                <p className="mt-2 text-slate-600">
                    All plans include <span className="font-semibold">OCR Extraction</span>,{" "}
                    <span className="font-semibold">OCR Correction (LLM)</span>, and the{" "}
                    <span className="font-semibold">Chatbot</span>.
                </p>
            </div>

            {/* Plans */}
            <div className="mt-8 grid md:grid-cols-3 gap-6">
                {/* Basic */}
                <div className="card p-6 flex flex-col">
                    <div className="text-sm font-semibold text-emerald-700">Basic</div>
                    <div className="mt-2 text-4xl font-black">
                        $0<span className="text-base font-semibold text-slate-500"> /mo</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-500">Best for trying things out.</div>
                    <ul className="mt-4 space-y-2 text-sm">
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>OCR Extraction: up to 100 pages/mo</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>OCR Correction: up to 50 pages/mo</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>Chatbot: 200 questions/mo</span>
                        </li>
                    </ul>
                    <div className="mt-6">
                        <a href="/login" className="btn w-full">Get started</a>
                    </div>
                </div>

                {/* Premium */}
                <div className="card p-6 border-emerald-300 shadow-lg shadow-emerald-200/40 flex flex-col">
                    <div className="text-sm font-semibold text-emerald-700">Premium</div>
                    <div className="mt-2 text-4xl font-black">
                        $49<span className="text-base font-semibold text-slate-500"> /mo</span>
                    </div>
                    <div className="mt-1 text-sm text-slate-500">For startups & teams.</div>
                    <ul className="mt-4 space-y-2 text-sm">
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>OCR Extraction: 5,000 pages/mo</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>OCR Correction: 2,500 pages/mo</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>Chatbot: 5,000 questions/mo</span>
                        </li>
                    </ul>
                    <div className="mt-6 grid grid-cols-1 gap-2">
                        <a href="/login" className="btn w-full">Upgrade</a>
                    </div>
                </div>

                {/* Organization */}
                <div className="card p-6 flex flex-col">
                    <div className="text-sm font-semibold text-emerald-700">Organization</div>
                    <div className="mt-2 text-4xl font-black">Custom</div>
                    <div className="mt-1 text-sm text-slate-500">For scale, security & support.</div>
                    <ul className="mt-4 space-y-2 text-sm">
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>Unlimited volumes (by contract)</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>On-prem / VPC, SSO (Okta/Google)</span>
                        </li>
                        <li className="flex gap-2">
                            <FaCheck className="mt-1 text-emerald-600"/>
                            <span>Dedicated support & SLA</span>
                        </li>
                    </ul>
                    <div className="mt-6">
                        <button className="btn w-full" onClick={() => setOpenOrg(true)}>
                            Contact sales
                        </button>
                    </div>
                </div>
            </div>

            {/* Modals */}
            <OrgContactModal open={openOrg} onClose={() => setOpenOrg(false)}/>
        </section>
    )
}
