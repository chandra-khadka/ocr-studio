import {useEffect, useMemo, useState} from "react"
import {sendOrgInquiry} from "../services/api"

type Props = {
    open: boolean
    onClose: () => void
}

export default function OrgContactModal({open, onClose}: Props) {
    const [submitting, setSubmitting] = useState(false)
    const [ok, setOk] = useState<null | boolean>(null)

    const [orgName, setOrgName] = useState("")
    const [contactName, setContactName] = useState("")
    const [email, setEmail] = useState("")
    const [phone, setPhone] = useState("")
    const [teamSize, setTeamSize] = useState<string>("1-10")
    const [monthlyDocs, setMonthlyDocs] = useState<string>("0-1k")
    const [useCases, setUseCases] = useState<string[]>(["ocr-extraction"])
    const [message, setMessage] = useState("")

    // Simple focus trap: focus first field when opening
    useEffect(() => {
        if (!open) return
        setTimeout(() => {
            const el = document.getElementById("org-name") as HTMLInputElement | null
            el?.focus()
        }, 50)
    }, [open])

    function toggleUseCase(val: string) {
        setUseCases(prev => prev.includes(val) ? prev.filter(v => v !== val) : [...prev, val])
    }

    const mailtoHref = useMemo(() => {
        const to = "sales@visionary.ai" // <-- change if needed
        const subject = encodeURIComponent("Organization Plan Inquiry")
        const body = encodeURIComponent(
            `Organization: ${orgName}
Contact: ${contactName}
Email: ${email}
Phone: ${phone}
Team size: ${teamSize}
Monthly documents: ${monthlyDocs}
Use cases: ${useCases.join(", ")}
Message:
${message}`
        )
        return `mailto:${to}?subject=${subject}&body=${body}`
    }, [orgName, contactName, email, phone, teamSize, monthlyDocs, useCases, message])

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault()
        setSubmitting(true)
        setOk(null)
        try {
            const payload = {
                orgName, contactName, email, phone, teamSize, monthlyDocs,
                useCases, message, source: "pricing-organization-modal"
            }
            const res = await sendOrgInquiry(payload)
            if (res.ok) {
                setOk(true)
                // light reset
                setOrgName("");
                setContactName("");
                setEmail("");
                setPhone("");
                setTeamSize("1-10");
                setMonthlyDocs("0-1k");
                setUseCases(["ocr-extraction"]);
                setMessage("")
                setTimeout(onClose, 1000)
            } else {
                setOk(false)
                // Fallback: open mail client
                window.location.href = mailtoHref
            }
        } catch {
            setOk(false)
            window.location.href = mailtoHref
        } finally {
            setSubmitting(false)
        }
    }

    if (!open) return null

    return (
        <div className="fixed inset-0 z-[999] flex items-center justify-center">
            {/* Backdrop */}
            <div className="absolute inset-0 bg-black/40" onClick={onClose}/>
            {/* Dialog */}
            <div className="relative z-10 w-[min(720px,92vw)] rounded-2xl bg-white shadow-xl border p-6">
                <div className="flex items-center justify-between">
                    <h3 className="text-lg font-extrabold">Organization plan — contact sales</h3>
                    <button onClick={onClose} className="text-gray-500 hover:text-gray-700">✕</button>
                </div>

                <form className="mt-4 grid md:grid-cols-2 gap-4" onSubmit={onSubmit}>
                    <div className="md:col-span-2">
                        <label className="text-xs font-semibold">Organization</label>
                        <input id="org-name" required value={orgName} onChange={e => setOrgName(e.target.value)}
                               className="input" placeholder="Company / Organization name"/>
                    </div>

                    <div>
                        <label className="text-xs font-semibold">Contact person</label>
                        <input required value={contactName} onChange={e => setContactName(e.target.value)}
                               className="input" placeholder="Full name"/>
                    </div>
                    <div>
                        <label className="text-xs font-semibold">Work email</label>
                        <input type="email" required value={email} onChange={e => setEmail(e.target.value)}
                               className="input" placeholder="name@company.com"/>
                    </div>
                    <div>
                        <label className="text-xs font-semibold">Phone (optional)</label>
                        <input value={phone} onChange={e => setPhone(e.target.value)} className="input"
                               placeholder="+977 ..."/>
                    </div>
                    <div>
                        <label className="text-xs font-semibold">Team size</label>
                        <select value={teamSize} onChange={e => setTeamSize(e.target.value)} className="input">
                            <option>1-10</option>
                            <option>11-50</option>
                            <option>51-200</option>
                            <option>201-1000</option>
                            <option>1000+</option>
                        </select>
                    </div>
                    <div>
                        <label className="text-xs font-semibold">Monthly docs</label>
                        <select value={monthlyDocs} onChange={e => setMonthlyDocs(e.target.value)} className="input">
                            <option>0-1k</option>
                            <option>1k-10k</option>
                            <option>10k-100k</option>
                            <option>100k+</option>
                        </select>
                    </div>

                    <div className="md:col-span-2">
                        <label className="text-xs font-semibold">Use cases</label>
                        <div className="mt-2 flex flex-wrap gap-3 text-sm">
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={useCases.includes("ocr-extraction")}
                                       onChange={() => toggleUseCase("ocr-extraction")}/>
                                OCR extraction
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={useCases.includes("ocr-correction")}
                                       onChange={() => toggleUseCase("ocr-correction")}/>
                                OCR correction (LLM)
                            </label>
                            <label className="inline-flex items-center gap-2">
                                <input type="checkbox" checked={useCases.includes("chatbot")}
                                       onChange={() => toggleUseCase("chatbot")}/>
                                Chatbot over docs
                            </label>
                        </div>
                    </div>

                    <div className="md:col-span-2">
                        <label className="text-xs font-semibold">Message</label>
                        <textarea value={message} onChange={e => setMessage(e.target.value)}
                                  className="input h-28"
                                  placeholder="Tell us about your data types, compliance needs, expected volumes, timelines, etc."/>
                    </div>

                    <div className="md:col-span-2 flex items-center justify-between">
                        <div className="text-xs text-gray-500">
                            We’ll reply within 1 business day. By submitting, you agree to our terms & privacy.
                        </div>
                        <button className="btn" disabled={submitting}>
                            {submitting ? "Sending..." : "Send"}
                        </button>
                    </div>

                    {ok === true && <div className="md:col-span-2 text-emerald-700 text-sm">Thanks! We’ll be in touch
                        shortly.</div>}
                    {ok === false && (
                        <div className="md:col-span-2 text-amber-700 text-sm">
                            Couldn’t reach the API — opening your email client… If nothing happens, <a
                            className="underline" href={mailtoHref}>click here</a>.
                        </div>
                    )}
                </form>
            </div>
            <style>{`.input{width:100%;border-radius:0.75rem;border:1px solid rgb(229,231,235);padding:.625rem .75rem;background:white} .input:focus{outline:none;border-color:rgb(16,185,129);box-shadow:0 0 0 3px rgba(16,185,129,.15);}`}</style>
        </div>
    )
}
