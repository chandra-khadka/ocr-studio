import {useEffect, useRef, useState} from 'react'
import {chat} from '../services/api'

type Msg = { role: 'user' | 'assistant'; content: string }

export default function ChatPanel({context}: { context?: string }) {
    const [history, setHistory] = useState<Msg[]>([])
    const [message, setMessage] = useState('')
    const [open, setOpen] = useState(true)
    const [sending, setSending] = useState(false)
    const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
    const listRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    const quickReplies = [
        'Devanagari to Roman English',
        'Summarize this document',
        'What is Your Price?',
        'Who Are you?',
    ]

    useEffect(() => {
        const el = listRef.current
        if (!el) return
        el.scrollTop = el.scrollHeight
    }, [history, open])

    useEffect(() => {
        function onKey(e: KeyboardEvent) {
            if (e.key === 'Escape') setOpen(false)
        }

        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [])

    async function send(msg?: string) {
        const m = (msg ?? message).trim()
        if (!m || sending) return
        setMessage('')
        setSending(true)
        setHistory(h => [...h, {role: 'user', content: m}])

        try {
            const res = await chat({message: m, context})
            setHistory(h => [...h, {role: 'assistant', content: res.reply}])
        } catch (e) {
            setHistory(h => [
                ...h,
                {role: 'assistant', content: 'Sorry, something went wrong. Please try again.'}
            ])
        } finally {
            setSending(false)
            inputRef.current?.focus()
        }
    }

    function clear() {
        setHistory([])
    }

    async function copyText(i: number, text: string) {
        try {
            await navigator.clipboard.writeText(text)
            setCopiedIdx(i)
            setTimeout(() => setCopiedIdx(null), 1000)
        } catch {/* ignore */
        }
    }

    function editToComposer(text: string) {
        setMessage(text)
        setOpen(true)
        requestAnimationFrame(() => inputRef.current?.focus())
    }

    return (
        <>
            {/* Floating Action Button (FAB) */}
            <button
                type="button"
                onClick={() => setOpen(o => !o)}
                className="fixed bottom-6 right-6 z-40 h-12 w-12 rounded-full bg-primary text-white shadow-lg shadow-emerald-300/40 hover:bg-primary-dark transition focus:outline-none focus:ring-4 focus:ring-emerald-300"
                aria-label={open ? 'Close chat' : 'Open chat'}
            >
                {open ? <span className="block text-xl leading-none">×</span> :
                    <span className="block text-lg leading-none">💬</span>}
            </button>

            {/* Sticky/Fixed Chat Panel (bottom-right) */}
            <div
                className={`fixed bottom-24 right-6 z-40 w-[92vw] max-w-md ${
                    open ? 'opacity-100 translate-y-0' : 'pointer-events-none opacity-0 translate-y-2'
                } transition-all duration-200`}
                role="dialog"
                aria-modal="false"
                aria-label="AI Document Chat"
            >
                <div
                    className="card p-4 h-[65vh] max-h-[70vh] flex flex-col border border-gray-100 bg-white/95 backdrop-blur-xl shadow-2xl rounded-2xl">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                            <div className="h-2.5 w-2.5 rounded-full bg-emerald-500 animate-pulse"/>
                            <h3 className="font-bold text-base">AI Document Chat</h3>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                className="text-xs text-gray-500 hover:text-primary underline-offset-2 hover:underline"
                                onClick={clear}
                                type="button"
                                title="Clear chat"
                            >
                                Clear
                            </button>
                            <button
                                className="text-gray-500 hover:text-gray-700"
                                onClick={() => setOpen(false)}
                                type="button"
                                title="Close"
                                aria-label="Close"
                            >
                                ×
                            </button>
                        </div>
                    </div>

                    {/* Stream hint */}
                    <p className="text-[11px] text-gray-500 mb-2">
                        Ask questions about the current OCR/corrected output. Context is attached automatically.
                    </p>

                    {/* Quick Replies */}
                    <div className="mb-3 -mt-1 flex flex-wrap gap-2">
                        {quickReplies.map((q) => (
                            <button
                                key={q}
                                type="button"
                                onClick={() => send(q)}
                                className="text-[11px] px-3 py-1 rounded-full border border-emerald-200 bg-white hover:bg-emerald-50 text-emerald-700 transition"
                                aria-label={`Quick reply: ${q}`}
                            >
                                {q}
                            </button>
                        ))}
                    </div>

                    {/* Messages */}
                    <div
                        ref={listRef}
                        className="flex-1 overflow-y-auto space-y-2 pr-1"
                        aria-live="polite"
                        aria-relevant="additions"
                    >
                        {history.length === 0 ? (
                            <div className="text-gray-500 text-center py-10">
                                Ask anything about your document to begin.
                            </div>
                        ) : (
                            history.map((m, i) => {
                                const isUser = m.role === 'user'
                                return (
                                    <div key={i} className={isUser ? 'text-right' : 'text-left'}>
                                        <div className="group inline-flex max-w-[85%] items-start gap-2">
                                            <div
                                                className={
                                                    isUser
                                                        ? 'inline-block bg-primary text-white px-3 py-2 rounded-2xl whitespace-pre-wrap'
                                                        : 'inline-block bg-gray-100 text-gray-800 px-3 py-2 rounded-2xl whitespace-pre-wrap'
                                                }
                                            >
                                                {m.content}
                                            </div>

                                            {/* Actions: Copy / Edit */}
                                            <div
                                                className="opacity-0 group-hover:opacity-100 transition-opacity flex gap-1 mt-1">
                                                <button
                                                    type="button"
                                                    onClick={() => copyText(i, m.content)}
                                                    className="text-[10px] px-2 py-1 rounded-md border bg-white hover:bg-slate-50 text-slate-600"
                                                    title={copiedIdx === i ? 'Copied!' : 'Copy'}
                                                    aria-label="Copy message"
                                                >
                                                    {copiedIdx === i ? 'Copied' : 'Copy'}
                                                </button>
                                                <button
                                                    type="button"
                                                    onClick={() => editToComposer(m.content)}
                                                    className="text-[10px] px-2 py-1 rounded-md border bg-white hover:bg-slate-50 text-slate-600"
                                                    title="Edit in composer"
                                                    aria-label="Edit message"
                                                >
                                                    Edit
                                                </button>
                                            </div>
                                        </div>
                                    </div>
                                )
                            })
                        )}
                        {sending && (
                            <div className="text-left">
                                <div
                                    className="inline-flex items-center gap-2 bg-gray-100 text-gray-800 px-3 py-2 rounded-2xl">
                                    <span
                                        className="inline-block h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:0ms]"/>
                                    <span
                                        className="inline-block h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:120ms]"/>
                                    <span
                                        className="inline-block h-2 w-2 rounded-full bg-gray-400 animate-bounce [animation-delay:240ms]"/>
                                </div>
                            </div>
                        )}
                    </div>

                    {/* Composer */}
                    <div className="mt-3 flex gap-2">
                        <input
                            ref={inputRef}
                            className="input flex-1"
                            placeholder="Type your question..."
                            value={message}
                            onChange={e => setMessage(e.target.value)}
                            onKeyDown={e => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                    e.preventDefault()
                                    send()
                                }
                            }}
                            aria-label="Message input"
                        />
                        <button className="btn" onClick={() => send()} type="button"
                                disabled={sending || !message.trim()}>
                            {sending ? 'Sending…' : 'Send'}
                        </button>
                    </div>
                </div>
            </div>
        </>
    )
}
