import {useState} from 'react'
import {useLocation, useNavigate} from 'react-router-dom'
import {useAuth} from '../auth/auth-context'

export default function Login() {
    const {login} = useAuth()
    const [email, setEmail] = useState('admin@demo.dev')
    const [password, setPassword] = useState('Pass@123')
    const [error, setError] = useState<string | null>(null)
    const navigate = useNavigate()
    const location = useLocation() as any

    async function onSubmit(e: React.FormEvent) {
        e.preventDefault()
        setError(null)
        const ok = await login(email, password)
        if (ok) {
            const dest = location.state?.from?.pathname || '/dashboard'
            navigate(dest, {replace: true})
        } else {
            setError('Invalid credentials. Use admin@demo.dev / Pass@123')
        }
    }

    return (
        <section className="relative min-h-[100svh] flex items-center justify-center overflow-hidden">
            {/* === Animated OCR Background (more visible) === */}
            <div className="absolute inset-0 -z-10">
                {/* soft gradient wash */}
                <div
                    className="absolute inset-0 bg-gradient-to-br from-emerald-200/30 via-emerald-100/40 to-white animate-[bgShift_12s_ease-in-out_infinite]"/>

                {/* dot matrix layer (OCR pixels) — slightly stronger */}
                <div
                    className="absolute inset-0 opacity-60"
                    style={{
                        backgroundImage:
                            'radial-gradient(rgba(16,185,129,0.18) 1px, transparent 1px)',
                        backgroundSize: '16px 16px',
                        backgroundPosition: '0 0',
                    }}
                />

                {/* horizontal scanlines */}
                <div
                    className="absolute inset-0 opacity-[0.12]"
                    style={{
                        backgroundImage:
                            'repeating-linear-gradient(180deg, rgba(0,0,0,.35) 0, rgba(0,0,0,.35) 1px, transparent 1px, transparent 6px)',
                    }}
                />

                {/* sweeping scanner bar */}
                <div
                    className="absolute left-0 right-0 h-24 -top-24 bg-gradient-to-b from-emerald-400/60 via-emerald-400/25 to-transparent blur-xl animate-[sweep_4.2s_linear_infinite]"/>

                {/* BIG center watermark — clearly visible but not overpowering */}
                <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <span
              className="
              text-[20vw] leading-none font-black tracking-[0.2em]
              text-transparent bg-clip-text
              bg-gradient-to-br from-emerald-600 via-teal-500 to-sky-500
              drop-shadow-[0_10px_30px_rgba(16,185,129,0.35)]
              select-none opacity-30
              [text-shadow:0_2px_20px_rgba(16,185,129,0.25)]
            "
              style={{letterSpacing: '0.08em'}}
              aria-hidden
          >
            OCR
          </span>
                </div>

                {/* floating OCR/LLM badges — stronger opacity & glow */}
                <div className="absolute inset-0 pointer-events-none">
                    <div
                        className="
              absolute top-16 left-12 text-emerald-700/70 text-4xl
              font-extrabold tracking-widest
              drop-shadow-[0_2px_8px_rgba(16,185,129,0.45)]
              animate-[float1_10s_ease-in-out_infinite]
            "
                    >
                        [ OCR ]
                    </div>
                    <div
                        className="
              absolute bottom-20 right-16 text-emerald-700/60 text-4xl
              font-extrabold tracking-widest
              drop-shadow-[0_2px_8px_rgba(16,185,129,0.45)]
              animate-[float2_12s_ease-in-out_infinite]
            "
                    >
                        <span className="pr-2">LLM</span>{'{TEXT}'}
                    </div>
                </div>
            </div>

            {/* === Centered Glass Card === */}
            <div className="w-full max-w-md px-4">
                <div className="backdrop-blur-xl bg-white/75 border border-white/70 shadow-2xl rounded-2xl p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-xl font-extrabold">Sign in</h2>
                        <span
                            className="inline-flex items-center gap-2 text-xs font-semibold text-emerald-700/90 bg-emerald-50 border border-emerald-200 rounded-full px-3 py-1">
              <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"/>
              Secure OCR Access
            </span>
                    </div>

                    <form onSubmit={onSubmit} className="space-y-4">
                        <div>
                            <label className="label">Email</label>
                            <input
                                className="input"
                                value={email}
                                onChange={e => setEmail(e.target.value)}
                                autoComplete="username"
                                inputMode="email"
                            />
                        </div>
                        <div>
                            <label className="label">Password</label>
                            <input
                                type="password"
                                className="input"
                                value={password}
                                onChange={e => setPassword(e.target.value)}
                                autoComplete="current-password"
                            />
                            <p className="text-[11px] text-gray-500 mt-1">
                                Hint: admin@demo.dev / Pass@123
                            </p>
                        </div>

                        {error && (
                            <div className="text-red-600 text-sm bg-red-50 border border-red-200 rounded-xl px-3 py-2">
                                {error}
                            </div>
                        )}

                        <button className="btn w-full" type="submit">
                            Login
                        </button>
                    </form>
                </div>
            </div>

            {/* keyframes */}
            <style>{`
        @keyframes bgShift {
          0% { transform: translate3d(0,0,0) }
          50% { transform: translate3d(0,-2%,0) }
          100% { transform: translate3d(0,0,0) }
        }
        @keyframes sweep {
          0% { transform: translateY(-30%); opacity: .9; }
          50% { transform: translateY(120vh); opacity: .7; }
          100% { transform: translateY(120vh); opacity: 0; }
        }
        @keyframes float1 {
          0%,100% { transform: translateY(0) translateX(0) rotate(0deg); }
          50% { transform: translateY(8px) translateX(3px) rotate(-1deg); }
        }
        @keyframes float2 {
          0%,100% { transform: translateY(0) translateX(0) rotate(0deg); }
          50% { transform: translateY(-10px) translateX(-6px) rotate(1deg); }
        }
      `}</style>
        </section>
    )
}
