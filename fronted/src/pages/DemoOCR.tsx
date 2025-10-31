import {useEffect, useMemo, useState} from 'react'
import FileUploader from '../components/FileUploader'
import {runOCR} from '../services/api'

/** ===== Demo assets ===== */
import ctznImg from '../assets/images/ctzn.png'
import passportImg from '../assets/images/passport.jpg'
import licenseImg from '../assets/images/license.jpg'
import voterImg from '../assets/images/voter_id.jpg'
import nationalIdImg from '../assets/images/national_id.jpg'

type TabKey = 'raw' | 'preview'

function CopyButton({text}: { text: string }) {
    const [copied, setCopied] = useState(false)

    async function onCopy() {
        try {
            await navigator.clipboard.writeText(text)
            setCopied(true)
            setTimeout(() => setCopied(false), 1200)
        } catch {
        }
    }

    return (
        <button
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-emerald-500 to-emerald-600 px-3 py-1.5 text-xs font-semibold text-white shadow hover:from-emerald-600 hover:to-emerald-700 transition"
            onClick={onCopy}
        >
            {copied ? '✅ Copied' : '📋 Copy'}
        </button>
    )
}

function DownloadButton({filename, data, mime}: { filename: string; data: string; mime: string }) {
    const href = useMemo(() => {
        const blob = new Blob([data], {type: mime})
        return URL.createObjectURL(blob)
    }, [data, mime])
    return (
        <a
            href={href}
            download={filename}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow hover:bg-slate-200 transition"
        >
            ⬇️ {filename}
        </a>
    )
}

/** For static assets (images) — direct link download */
function DownloadLink({href, filename}: { href: string; filename: string }) {
    return (
        <a
            href={href}
            download={filename}
            className="inline-flex items-center gap-2 rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-semibold text-slate-700 shadow hover:bg-slate-200 transition"
        >
            ⬇️ {filename}
        </a>
    )
}

/** Lightweight Markdown → HTML */
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
        .map(block => (/^\s*</.test(block.trim()) ? block : `<p>${block.trim().replace(/\n/g, '<br/>')}</p>`))
        .join('\n')

    const css = `
  <style>
    body { font-family: Inter, ui-sans-serif, system-ui; padding: 16px; color:#1f2937; }
    h1,h2,h3,h4,h5,h6 { margin: 1em 0 .5em; line-height:1.2; }
    p { margin: .6em 0; }
    a { color:#0ea5e9; text-decoration: none; }
    a:hover { text-decoration: underline; }
    ul { margin: .4em 0 .6em 1.2em; list-style: disc; }
    pre.md-pre { background:#0b1020; color:#e5e7eb; padding:12px; border-radius:12px; overflow:auto; }
    code.md-code { background:#f3f4f6; padding:.1rem .35rem; border-radius:.35rem; }
    table { border-collapse: collapse; width: 100%; margin: 12px 0; font-size: 14px; }
    th, td { border: 1px solid #e5e7eb; padding: 6px 8px; }
    th { background: #f9fafb; text-align: left; }
    img { max-width: 100%; border-radius: 6px; }
  </style>`
    return `<!doctype html><meta charset="utf-8"><title>Preview</title>${css}<article>${s}</article>`
}

/** Uploads gallery helpers */
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
    type.startsWith('image/') || /\.(png|jpe?g|gif|webp|bmp|tiff?)$/i.test(name)
const isPdf = (type: string, name: string) =>
    type === 'application/pdf' || /\.pdf$/i.test(name)
const formatBytes = (n: number) => {
    if (!n) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
    const i = Math.floor(Math.log(n) / Math.log(k))
    return `${(n / Math.pow(k, i)).toFixed(i ? 1 : 0)} ${sizes[i]}`
}

/** ===== Structured Document Demo Types & Templates ===== */
type DocType = 'CITIZENSHIP' | 'LICENSE' | 'VOTER_ID' | 'PASSPORT' | 'NATIONAL_ID'
type FieldDef = { field: string; type: string; description: string }
type DocTemplate = {
    title: string
    schema: FieldDef[]
    sampleJson: string
    sampleMd: string
    sampleCsv?: string
    sampleImage?: string
}

/* --- Extracted (hand-transcribed) values from your images --- */

/* 1) Citizenship (older Nepali card; Kapilvastu; Siddhartha Gautam) */
function citizenshipTemplate(): DocTemplate {
    const schema: FieldDef[] = [
        {field: 'full_name', type: 'string', description: 'Name as on card (Devanagari + Romanized)'},
        {field: 'district', type: 'string', description: 'District'},
        {field: 'issuing_office', type: 'string', description: 'Issuing Office'},
        {field: 'citizenship_number', type: 'string|null', description: 'Serial/Number if visible'},
        {field: 'gender', type: 'string|null', description: 'Gender (if marked)'},
        {field: 'date_of_birth_bs', type: 'string|null', description: 'DOB (BS) if present'},
        {field: 'date_of_birth_ad', type: 'string|null', description: 'DOB (AD) if present'},
        {field: 'place_of_birth', type: 'string|null', description: 'Place of Birth (if legible)'},
    ]

    const sample = {
        full_name: 'सिद्धार्थ गौतम (Siddhartha Gautam)',
        district: 'रुपन्देही (Rupandehi)',
        issuing_office: 'जिल्ला प्रशासन कार्यालय, रुपन्देही (District Administration Office, Rupandehi)',
        citizenship_number: '0001',               // low confidence per notes
        gender: null,                             // not provided
        date_of_birth_bs: 'साल ५६३ महिना १ गते (अस्पष्ट)', // from dob_text_np
        date_of_birth_ad: null,                   // calendar unspecified; AD not given
        place_of_birth: 'लुम्बिनी, रुपन्देही'            // from birthplace_np
    }

    const sampleMd =
        `# Citizenship — Extract (from sample image)
**Full Name:** ${sample.full_name}

| Field | Value |
|---|---|
| District | ${sample.district} |
| Issuing Office | ${sample.issuing_office} |
| Citizenship No. | ${sample.citizenship_number ?? '—'} |
| Gender | ${sample.gender ?? '—'} |
| DOB (BS) | ${sample.date_of_birth_bs ?? '—'} |
| DOB (AD) | ${sample.date_of_birth_ad ?? '—'} |
| Place of Birth | ${sample.place_of_birth ?? '—'} |`

    const sampleCsv =
        `full_name,district,issuing_office,citizenship_number,gender,date_of_birth_bs,date_of_birth_ad,place_of_birth
"${sample.full_name}","${sample.district}","${sample.issuing_office}","${sample.citizenship_number}","${sample.gender ?? ''}","${sample.date_of_birth_bs ?? ''}","${sample.date_of_birth_ad ?? ''}","${sample.place_of_birth ?? ''}"`

    return {
        title: 'Citizenship',
        schema,
        sampleJson: JSON.stringify(sample, null, 2),
        sampleMd,
        sampleCsv,
        sampleImage: ctznImg as unknown as string
    }
}

/* 2) Passport (clear English text) */
function passportTemplate(): DocTemplate {
    const schema: FieldDef[] = [
        {field: 'passport_number', type: 'string', description: 'Passport No.'},
        {field: 'surname', type: 'string', description: 'Family name'},
        {field: 'given_names', type: 'string', description: 'Given names'},
        {field: 'nationality', type: 'string', description: 'Nationality'},
        {field: 'date_of_birth', type: 'string (DD MMM YYYY)', description: 'Date of birth'},
        {field: 'sex', type: 'string', description: 'Sex'},
        {field: 'date_of_issue', type: 'string (DD MMM YYYY)', description: 'Issue date'},
        {field: 'date_of_expiry', type: 'string (DD MMM YYYY)', description: 'Expiry date'},
        {field: 'citizenship_number', type: 'string', description: 'Citizenship No.'},
        {field: 'place_of_birth', type: 'string', description: 'Place of birth'},
        {field: 'issuing_authority', type: 'string', description: 'Issuing authority'},
        {field: 'mrz_line1', type: 'string', description: 'MRZ line 1'},
        {field: 'mrz_line2', type: 'string', description: 'MRZ line 2'},
    ]

    const sample = {
        passport_number: '06327084',
        surname: 'GAJUREL',
        given_names: 'DINESH',
        nationality: 'NEPALESE',
        date_of_birth: '02 AUG 1982',
        sex: 'M',
        date_of_issue: '18 FEB 2013',
        date_of_expiry: '17 FEB 2023',
        citizenship_number: '6961-4538',
        place_of_birth: 'KATHMANDU',
        issuing_authority: 'MOFA, DEPARTMENT OF PASSPORT',
        mrz_line1: 'P<NPLGAJUREL<<DINESH<<<<<<<<<<<<<<<<<<',
        mrz_line2: '06327084<4NPL8208020M230217769614538<<<<44'
    }

    const sampleMd =
        `# Passport — Extract (from sample image)

**Name:** ${sample.given_names} ${sample.surname}  
**Passport No.:** ${sample.passport_number}

| Field | Value |
|---|---|
| Nationality | ${sample.nationality} |
| Sex | ${sample.sex} |
| Date of Birth | ${sample.date_of_birth} |
| Date of Issue | ${sample.date_of_issue} |
| Date of Expiry | ${sample.date_of_expiry} |
| Place of Birth | ${sample.place_of_birth} |
| Citizenship No. | ${sample.citizenship_number} |
| Issuing Authority | ${sample.issuing_authority} |

**MRZ**  
\`${sample.mrz_line1}\`  
\`${sample.mrz_line2}\``

    return {
        title: 'Passport',
        schema,
        sampleJson: JSON.stringify(sample, null, 2),
        sampleMd,
        sampleImage: passportImg as unknown as string
    }
}

/* 3) Driving License (many labels; visible values only) */
function licenseTemplate(): DocTemplate {
    const schema: FieldDef[] = [
        {field: 'blood_group', type: 'string|null', description: 'B.G.'},
        {field: 'address', type: 'string|null', description: 'Printed address'},
        {field: 'license_office', type: 'string|null', description: 'License Office'},
        {field: 'date_of_issue', type: 'string|null (DD-MM-YYYY)', description: 'D.O.I.'},
        {field: 'date_of_expiry', type: 'string|null (DD-MM-YYYY)', description: 'D.O.E.'},
        {field: 'category', type: 'string|null', description: 'Vehicle categories'},
        {field: 'dl_number', type: 'string|null', description: 'D.L. No. (not legible on sample)'},
        {field: 'name', type: 'string|null', description: 'Holder name (redacted on sample)'},
    ]

    const sample = {
        blood_group: 'O+',
        address: 'Yachhen - 6, Bhaktapur, Bagmati, Nepal',
        license_office: 'Government of Nepal',
        date_of_issue: '20-08-2017',
        date_of_expiry: '19-08-2022',
        category: 'K',
        dl_number: '02-06-00273515',
        name: 'Pushpa Das Napit'
    }

    const sampleMd =
        `# Driving License — Extract (from sample image)

| Field | Value |
|---|---|
| Blood Group | ${sample.blood_group} |
| Address | ${sample.address} |
| License Office | ${sample.license_office} |
| D.O.I. | ${sample.date_of_issue} |
| D.O.E. | ${sample.date_of_expiry} |
| Category | ${sample.category} |
| D.L. No. | ${sample.dl_number ?? '—'} |
| Name | ${sample.name ?? '—'} |`

    return {
        title: 'License',
        schema,
        sampleJson: JSON.stringify(sample, null, 2),
        sampleMd,
        sampleImage: licenseImg as unknown as string
    }
}

/* 4) Voter ID (some text blurred; use visible Nepali fields) */
function voterIdTemplate(): DocTemplate {
    const schema: FieldDef[] = [
        {field: 'voter_number', type: 'string|null', description: 'मतदाता नम्बर (blurred on sample)'},
        {field: 'name', type: 'string|null', description: 'नामथर (blurred on sample)'},
        {field: 'dob_bs', type: 'string', description: 'जन्म मिति (BS)'},
        {field: 'gender', type: 'string', description: 'लिङ्ग'},
        {field: 'district', type: 'string', description: 'जिल्ला'},
        {field: 'address', type: 'string', description: 'ठेगाना'},
        {field: 'polling_station', type: 'string', description: 'मतदान स्थल'},
    ]

    const sample = {
        voter_number: '१०५४०५७९ (10540579)',
        name: 'धुंधला (Blurred)',
        dob_bs: '२०३०-०५-०४ (2030-05-04)',
        gender: 'महिला (Female)',
        district: 'डोल्पा (Dolpa)',
        address: 'त्रिपुरासुन्दरी नगरपालिका-१०, डोल्पा (Tripurasundari Municipality-10, Dolpa)',
        polling_station: 'जनप्रभा उ.मा.वि. (Janprabha U. Ma. Vi.)'
    }

    const sampleMd =
        `# Voter ID — Extract (from sample image)

| Field | Value |
|---|---|
| मतदाता नम्बर (Voter No.) | ${sample.voter_number ?? '—'} |
| नामथर (Name) | ${sample.name ?? '—'} |
| जन्म मिति (BS) | ${sample.dob_bs} |
| लिङ्ग (Gender) | ${sample.gender} |
| जिल्ला (District) | ${sample.district} |
| ठेगाना (Address) | ${sample.address} |
| मतदान स्थल (Polling Station) | ${sample.polling_station} |`

    return {
        title: 'Voter ID',
        schema,
        sampleJson: JSON.stringify(sample, null, 2),
        sampleMd,
        sampleImage: voterImg as unknown as string
    }
}

/* 5) National ID (clear fields) */
function nationalIdTemplate(): DocTemplate {
    const schema: FieldDef[] = [
        {field: 'nationality', type: 'string', description: 'Nationality'},
        {field: 'sex', type: 'string', description: 'Sex'},
        {field: 'surname', type: 'string', description: 'Surname'},
        {field: 'given_name', type: 'string', description: 'Given name'},
        {field: 'nin', type: 'string', description: 'National ID number (printed left of chip)'},
        {field: 'dob', type: 'string (YYYY-MM-DD)', description: 'Date of birth'},
        {field: 'mother_name', type: 'string', description: "Mother's name"},
        {field: 'father_name', type: 'string', description: "Father's name"},
        {field: 'date_of_issue', type: 'string (DD-MM-YYYY)', description: 'Date of issue'},
    ]

    const sample = {
        nationality: 'Nepalese',
        sex: 'F',
        surname: 'Koirala Pokhrel',
        given_name: 'Bhagawati Kumari',
        nin: '023-456-2130',
        dob: '1978-02-05',
        mother_name: 'Sati Kumari Pokhrel',
        father_name: 'Bishnu Prasad Pokhrel',
        date_of_issue: '01-01-2017'
    }

    const sampleMd =
        `# National ID — Extract (from sample image)

**Name:** ${sample.given_name} ${sample.surname}

| Field | Value |
|---|---|
| Nationality | ${sample.nationality} |
| Sex | ${sample.sex} |
| NIN | ${sample.nin} |
| Date of Birth | ${sample.dob} |
| Mother's Name | ${sample.mother_name} |
| Father's Name | ${sample.father_name} |
| Date of Issue | ${sample.date_of_issue} |`

    return {
        title: 'National ID',
        schema,
        sampleJson: JSON.stringify(sample, null, 2),
        sampleMd,
        sampleImage: nationalIdImg as unknown as string
    }
}

function getDocTemplate(docType: DocType): DocTemplate {
    if (docType === 'CITIZENSHIP') return citizenshipTemplate()
    if (docType === 'PASSPORT') return passportTemplate()
    if (docType === 'LICENSE') return licenseTemplate()
    if (docType === 'VOTER_ID') return voterIdTemplate()
    return nationalIdTemplate()
}

const DOC_TYPES: { img: string; emoji: string; label: string; key: DocType }[] = [
    {key: 'CITIZENSHIP', label: 'Citizenship', emoji: '🪪', img: ctznImg as unknown as string},
    {key: 'LICENSE', label: 'License', emoji: '🚗', img: licenseImg as unknown as string},
    {key: 'VOTER_ID', label: 'Voter ID', emoji: '🗳️', img: voterImg as unknown as string},
    {key: 'PASSPORT', label: 'Passport', emoji: '🛂', img: passportImg as unknown as string},
    {key: 'NATIONAL_ID', label: 'National ID', emoji: '🏛️', img: nationalIdImg as unknown as string},
]

export default function DemoOCR() {
    const [fileName, setFileName] = useState('')
    const [fileB64, setFileB64] = useState('')
    const [result, setResult] = useState('')
    const [loading, setLoading] = useState(false)
    const [tab, setTab] = useState<TabKey>('raw')

    // uploads gallery
    const [uploads, setUploads] = useState<UploadedFile[]>([])
    const [selectedId, setSelectedId] = useState<string | null>(null)

    // preview modal state
    const [showPreview, setShowPreview] = useState(false)
    const [zoom, setZoom] = useState(100) // %
    const [rotation, setRotation] = useState(0) // deg
    const [invert, setInvert] = useState(false)

    // Fancy scanning FX
    const [progress, setProgress] = useState(0)
    const STEPS = [
        'Detecting layout…',
        'Auto-detecting language…',
        'Enhancing contrast…',
        'Segmenting lines…',
        'Recognizing text…',
        'Reconstructing tables…',
        'Applying spell-check…',
        'Building Markdown…'
    ]

    // Structured demo modal
    const [showStructDemo, setShowStructDemo] = useState(false)
    const [demoDocType, setDemoDocType] = useState<DocType>('CITIZENSHIP')

    useEffect(() => {
        if (!loading) return
        setProgress(0)
        const id = setInterval(() => {
            setProgress(p => Math.min(99, p + 6 + Math.random() * 8))
        }, 180)
        return () => clearInterval(id)
    }, [loading])

    useEffect(() => {
        if (!loading && progress > 0) {
            const t = setTimeout(() => setProgress(0), 600)
            return () => clearTimeout(t)
        }
    }, [loading, progress])

    // Cleanup object URLs on unmount
    useEffect(() => {
        return () => uploads.forEach(u => URL.revokeObjectURL(u.url))
    }, [uploads])

    async function onFile(file: File, b64: string) {
        setFileName(file.name)
        setFileB64(b64)
        setResult('')
        setTab('raw')

        const id = `${Date.now()}_${Math.random().toString(36).slice(2)}`
        const url = URL.createObjectURL(file)
        const entry: UploadedFile = {
            id,
            name: file.name,
            url,
            b64: b64,
            type: file.type || '',
            size: file.size || 0,
            uploadedAt: Date.now(),
        }
        setUploads(prev => [entry, ...prev])
        setSelectedId(id)
    }

    async function doOCR() {
        if (!fileB64) return
        setLoading(true)
        try {
            const res = await runOCR({
                fileName,
                fileBase64: fileB64,
                language: 'AUTO_DETECT',
                documentType: 'STANDARD',
                provider: 'GEMINI:gemini-2.0-flash-001',
                prompt: 'Return Markdown with headings and tables when possible.'
            })
            setResult(res.text)
            setTab('preview')
        } finally {
            setLoading(false)
        }
    }

    const htmlPreview = useMemo(() => mdToHtml(result || ''), [result])
    const currentStep = Math.min(Math.floor((progress / 100) * STEPS.length), STEPS.length - 1)

    function selectUpload(u: UploadedFile) {
        setSelectedId(u.id)
        setFileName(u.name)
        setFileB64(u.b64)
        setResult('')
        setTab('raw')
    }

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
                    setResult('')
                }
            }
            return next
        })
    }

    function clearUploads() {
        uploads.forEach(u => URL.revokeObjectURL(u.url))
        setUploads([])
        setSelectedId(null)
        setFileName('')
        setFileB64('')
        setResult('')
    }

    const selected = uploads.find(u => u.id === selectedId) || null
    const demo = getDocTemplate(demoDocType)

    function mailtoHref() {
        const subject = `Structured OCR demo request - ${demo.title}`
        const body =
            `Hello Team,

I would like a demo of your Structured OCR for **${demo.title}**.

Use-case:
- Bulk extraction to JSON/CSV
- Validation rules & field mapping
- API integration with my system

Please contact me to schedule a session.

Thanks!`
        return `mailto:demo@yourcompany.dev?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`
    }

    // === helper for rotation-aware sizing (used for PDFs) ===
    const isRotatedPortrait = ((rotation % 180) !== 0)

    return (
        <section className="relative min-h-[100svh] overflow-hidden">
            {/* === Background (light, subtle) === */}
            <div className="absolute inset-0 -z-50">
                <div className="absolute inset-0 bg-gradient-to-br from-slate-50 via-white to-emerald-50"/>
                <div
                    className="absolute -top-40 left-1/2 h-[70vmin] w-[70vmin] -translate-x-1/2 rounded-full bg-emerald-200/20 blur-[100px]"/>
                <div
                    className="absolute bottom-[-20%] right-10 h-[60vmin] w-[60vmin] rounded-full bg-cyan-200/20 blur-[100px]"/>
                <div
                    className="absolute inset-0 opacity-20"
                    style={{
                        backgroundImage: 'radial-gradient(rgba(0,0,0,0.06) 1px, transparent 1px)',
                        backgroundSize: '16px 16px'
                    }}
                />
            </div>

            <div className="max-w-6xl mx-auto px-4 py-12">
                {/* Floating Badge */}
                <div className="mb-8 flex justify-center">
          <span
              className="inline-flex items-center gap-2 rounded-full border border-emerald-300 bg-white/70 backdrop-blur px-4 py-1.5 text-sm font-semibold text-emerald-700 shadow">
            ✨ OCR Demo Playground
          </span>
                </div>

                <div className="grid md:grid-cols-2 gap-8">
                    {/* Upload Card */}
                    <div className="card p-6 border border-slate-200 bg-white/90 backdrop-blur relative">
                        <h3 className="font-bold mb-3 text-lg">Upload & Run OCR</h3>
                        <FileUploader onSelect={onFile} accept=".pdf,.png,.jpg,.jpeg,.tif,.tiff"/>
                        {fileName && (
                            <div className="mt-3 text-sm text-gray-600">
                                <span className="font-semibold">Selected:</span> {fileName}
                            </div>
                        )}

                        <div className="mt-5 flex flex-wrap gap-3">
                            <button
                                className={`btn ${!fileB64 ? 'opacity-60 cursor-not-allowed' : ''} ${
                                    !loading && fileB64 ? 'shadow-[0_0_0_0_rgba(16,185,129,0.6)] animate-pulse-soft' : ''
                                }`}
                                onClick={doOCR}
                                disabled={!fileB64 || loading}
                            >
                                {loading ? '⏳ Scanning…' : '⚡ Run OCR'}
                            </button>

                            {/* Preview button */}
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
                                disabled={!selected}
                                title="Preview the selected document"
                            >
                                👁 Preview
                            </button>

                            {result && !loading && (
                                <>
                                    <CopyButton text={result}/>
                                    <DownloadButton filename="ocr.md" data={result} mime="text/markdown"/>
                                    <DownloadButton filename="preview.html" data={htmlPreview} mime="text/html"/>
                                </>
                            )}
                        </div>

                        {/* Subtle hint */}
                        {!result && !loading ? (
                            <p className="mt-6 text-xs text-gray-500">Tip: Upload a file to enable OCR actions.</p>
                        ) : null}

                        {/* Upload-side mini progress (only when loading) */}
                        {loading && (
                            <div className="mt-6 text-xs text-gray-600">
                                <div className="mb-2 font-semibold">Processing… {Math.max(1, Math.floor(progress))}%
                                </div>
                                <div className="h-1.5 bg-emerald-100 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-gradient-to-r from-emerald-400 via-cyan-400 to-violet-400 transition-[width] duration-200"
                                        style={{width: `${progress}%`}}
                                    />
                                </div>
                                <ul className="mt-3 space-y-1.5">
                                    {STEPS.map((s, i) => (
                                        <li key={i} className="flex items-center gap-2">
                      <span
                          className={`inline-block h-2 w-2 rounded-full ${
                              i < currentStep ? 'bg-emerald-500' : i === currentStep ? 'bg-amber-400' : 'bg-slate-300'
                          }`}
                      />
                                            <span
                                                className={`${i <= currentStep ? 'text-slate-700' : 'text-slate-400'}`}>{s}</span>
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
                                        const selected = u.id === selectedId
                                        return (
                                            <div
                                                key={u.id}
                                                onClick={() => selectUpload(u)}
                                                role="button"
                                                tabIndex={0}
                                                onKeyDown={(e) => (e.key === 'Enter' ? selectUpload(u) : undefined)}
                                                className={`group relative flex gap-3 rounded-xl border p-3 bg-white/70 hover:bg-white transition cursor-pointer ${
                                                    selected ? 'border-emerald-300 ring-2 ring-emerald-200' : 'border-slate-200'
                                                }`}
                                                title={u.name}
                                                aria-current={selected ? 'true' : 'false'}
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
                                                    <div
                                                        className="text-sm font-semibold text-slate-800 truncate">{u.name}</div>
                                                    <div className="text-[11px] text-slate-500">
                                                        {formatBytes(u.size)} • {new Date(u.uploadedAt).toLocaleTimeString()}
                                                    </div>
                                                    {selected && <div
                                                        className="mt-1 text-[11px] text-emerald-700 font-medium">Selected</div>}
                                                </div>
                                                <div className="self-start flex items-center gap-2">
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            window.open(u.url, '_blank', 'noopener,noreferrer')
                                                        }}
                                                        className="text-[11px] px-2 py-1 rounded-md border bg-white hover:bg-slate-50"
                                                        type="button"
                                                    >
                                                        Open
                                                    </button>
                                                    <button
                                                        onClick={(e) => {
                                                            e.stopPropagation()
                                                            removeUpload(u.id)
                                                        }}
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

                    {/* Output Card */}
                    <div
                        className="card p-0 border border-slate-200 bg-white/95 backdrop-blur overflow-hidden relative"
                        aria-busy={loading}
                        aria-live="polite"
                    >
                        {/* Tabs */}
                        <div className="flex items-center gap-2 border-b px-4 pt-3 bg-slate-50">
                            <button
                                className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                                    tab === 'raw' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary'
                                }`}
                                onClick={() => setTab('raw')}
                                disabled={loading}
                            >
                                📝 Raw Markdown
                            </button>
                            <button
                                className={`px-3 py-2 rounded-t-xl text-sm font-semibold ${
                                    tab === 'preview' ? 'bg-primary text-white' : 'text-gray-600 hover:text-primary'
                                }`}
                                onClick={() => setTab('preview')}
                                disabled={loading}
                            >
                                👀 Preview
                            </button>
                        </div>

                        {/* Content */}
                        <div className="p-6 relative">
                            {/* SCANNING OVERLAY */}
                            <div
                                className={`absolute inset-0 transition-opacity duration-300 ${
                                    loading ? 'opacity-100' : 'opacity-0 pointer-events-none'
                                }`}
                            >
                                <div
                                    className="absolute inset-4 rounded-xl bg-white/90 border border-emerald-100 shadow-inner"/>
                                <div
                                    className="absolute inset-4 rounded-xl overflow-hidden"
                                    style={{
                                        backgroundImage:
                                            'repeating-linear-gradient(180deg, rgba(2,6,23,0.06) 0, rgba(2,6,23,0.06) 1px, transparent 1px, transparent 8px)'
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

                            {/* Normal content */}
                            {!result && !loading ? (
                                <div className="text-gray-400 text-sm">OCR output will appear here.</div>
                            ) : tab === 'raw' ? (
                                <pre
                                    className="whitespace-pre-wrap text-sm bg-slate-900 text-slate-100 rounded-xl p-4 overflow-auto shadow-inner">
{result}
                </pre>
                            ) : (
                                <iframe
                                    title="Markdown Preview"
                                    className="w-full h-[60vh] border border-slate-200 rounded-xl shadow-inner"
                                    srcDoc={htmlPreview}
                                />
                            )}
                        </div>
                    </div>
                </div>

                {/* ===== Structured Document OCR DEMO Section ===== */}
                <div className="mt-14">
                    <div className="mb-4 flex items-center justify-between gap-3">
                        <h3 className="text-xl font-bold text-slate-800">
                            Want structured OCR for your documents?
                        </h3>
                        <button
                            className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-semibold hover:bg-emerald-700"
                            onClick={() => setShowStructDemo(true)}
                        >
                            💡 Request Structured OCR Demo
                        </button>
                    </div>
                    <p className="text-sm text-slate-600">
                        Click to preview sample formats and extraction output for <span className="font-medium">Citizenship, License, Voter&nbsp;ID, Passport,</span> and <span
                        className="font-medium">National&nbsp;ID</span>.
                        These examples show values **transcribed from your provided images**. Blurred/illegible fields
                        are set to <code>null</code>.
                    </p>

                    <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3">
                        {DOC_TYPES.map(d => (
                            <button
                                key={d.key}
                                onClick={() => {
                                    setDemoDocType(d.key);
                                    setShowStructDemo(true);
                                }}
                                className={`rounded-xl border p-2 text-left bg-white hover:bg-emerald-50 transition ${
                                    demoDocType === d.key ? 'border-emerald-300 ring-2 ring-emerald-200' : 'border-slate-200'
                                }`}
                            >
                                <div className="aspect-[16/10] w-full overflow-hidden rounded-lg border mb-2">
                                    <img src={d.img} alt={d.label} className="w-full h-full object-cover"/>
                                </div>
                                <div className="font-semibold text-slate-800">{d.emoji} {d.label}</div>
                                <div className="text-xs text-slate-500">Click to view sample extraction</div>
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            {/* PREVIEW MODAL */}
            {showPreview && selected && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Document preview"
                >
                    <div
                        className="relative w-full max-w-6xl h-[85vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                        {/* Toolbar */}
                        <div className="flex items-center gap-3 px-4 py-3 border-b bg-white/80 backdrop-blur">
                            <div className="font-semibold text-slate-800 truncate">{selected.name}</div>
                            <div className="ml-auto flex items-center gap-2 text-sm">
                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setZoom(z => Math.max(25, z - 10))}
                                    type="button"
                                >−
                                </button>
                                <div className="w-40">
                                    <input
                                        type="range"
                                        min={25}
                                        max={250}
                                        step={5}
                                        value={zoom}
                                        onChange={e => setZoom(parseInt(e.target.value))}
                                        className="w-full"
                                        aria-label="Zoom"
                                    />
                                </div>
                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setZoom(z => Math.min(250, z + 10))}
                                    type="button"
                                >+
                                </button>
                                <span className="w-12 text-right text-slate-600">{zoom}%</span>

                                <div className="h-6 w-px bg-slate-200 mx-1"/>

                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setRotation(r => (r - 90 + 360) % 360)}
                                    type="button"
                                    title="Rotate left"
                                >⟲
                                </button>
                                <button
                                    className="px-2 py-1 rounded-md border hover:bg-slate-50"
                                    onClick={() => setRotation(r => (r + 90) % 360)}
                                    type="button"
                                    title="Rotate right"
                                >⟳
                                </button>

                                <label className="ml-2 inline-flex items-center gap-2 text-slate-700">
                                    <input
                                        type="checkbox"
                                        checked={invert}
                                        onChange={() => setInvert(v => !v)}
                                    />
                                    Invert
                                </label>

                                <a
                                    href={selected.url}
                                    target="_blank"
                                    rel="noreferrer"
                                    className="ml-2 px-2 py-1 rounded-md border hover:bg-slate-50"
                                >
                                    Open in new tab
                                </a>

                                <button
                                    className="ml-2 px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                                    onClick={() => setShowPreview(false)}
                                    type="button"
                                >
                                    Close
                                </button>
                            </div>
                        </div>

                        {/* Canvas */}
                        <div className="flex-1 overflow-auto bg-slate-50">
                            <div
                                className={`min-h-full w-full flex items-center justify-center p-6 ${invert ? 'invert' : ''}`}>
                                {isImage(selected.type, selected.name) ? (
                                    <img
                                        src={selected.url}
                                        alt={selected.name}
                                        className="rounded-lg shadow border border-slate-200 max-w-none"
                                        style={{
                                            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                                            transformOrigin: 'center',
                                        }}
                                    />
                                ) : isPdf(selected.type, selected.name) ? (
                                    <div
                                        className="rounded-lg shadow border border-slate-200 bg-white overflow-auto"
                                        style={{
                                            transform: `scale(${zoom / 100}) rotate(${rotation}deg)`,
                                            transformOrigin: 'center',
                                        }}
                                    >
                                        {/* Use inline size so dimensions swap when rotated */}
                                        <iframe
                                            title="PDF preview"
                                            src={selected.url}
                                            style={{
                                                width: isRotatedPortrait ? '1200px' : '900px',
                                                height: isRotatedPortrait ? '900px' : '1200px',
                                                border: '0'
                                            }}
                                        />
                                    </div>
                                ) : (
                                    <div className="text-center text-slate-600">
                                        <div className="text-5xl mb-4">📄</div>
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

            {/* STRUCTURED DEMO MODAL */}
            {showStructDemo && (
                <div
                    className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40"
                    role="dialog"
                    aria-modal="true"
                    aria-label="Structured Document OCR Demo"
                >
                    <div
                        className="relative w-full max-w-6xl h-[88vh] bg-white rounded-2xl shadow-2xl overflow-hidden flex flex-col">
                        <div className="flex items-center gap-3 px-4 py-3 border-b bg-white/80 backdrop-blur">
                            <div className="font-semibold text-slate-800 truncate">Structured OCR Demo
                                — {demo.title}</div>
                            <div className="ml-auto flex items-center gap-2 text-sm">
                                <select
                                    value={demoDocType}
                                    onChange={e => setDemoDocType(e.target.value as DocType)}
                                    className="text-sm border rounded-md px-2 py-1 bg-white"
                                >
                                    {['CITIZENSHIP', 'PASSPORT', 'LICENSE', 'VOTER_ID', 'NATIONAL_ID'].map(key => {
                                        const meta = DOC_TYPES.find(d => d.key === key as DocType)!
                                        return <option key={meta.key}
                                                       value={meta.key}>{meta.emoji} {meta.label}</option>
                                    })}
                                </select>
                                <a
                                    href={mailtoHref()}
                                    className="px-3 py-1.5 rounded-md bg-emerald-600 text-white hover:bg-emerald-700"
                                >
                                    ✉️ Request demo
                                </a>
                                <button
                                    className="px-3 py-1.5 rounded-md border hover:bg-slate-50"
                                    onClick={() => setShowStructDemo(false)}
                                >
                                    Close
                                </button>
                            </div>
                        </div>

                        <div className="flex-1 grid md:grid-cols-2 gap-0 overflow-hidden">
                            {/* Left: Visual / Sample card */}
                            <div className="p-5 overflow-auto bg-slate-50">
                                <div className="rounded-xl border bg-white p-4 shadow-sm">
                                    <div className="mb-3 text-sm text-slate-600">
                                        Sample document (your provided image):
                                    </div>
                                    {demo.sampleImage ? (
                                        <img
                                            src={demo.sampleImage}
                                            alt={`${demo.title} sample`}
                                            className="w-full rounded-lg border"
                                        />
                                    ) : (
                                        <div
                                            className="w-full aspect-[16/9] rounded-lg border grid place-items-center text-slate-400">
                                            (No sample image)
                                        </div>
                                    )}
                                    <div className="mt-3 flex flex-wrap gap-2">
                                        {demo.sampleImage && (
                                            <DownloadLink
                                                href={demo.sampleImage}
                                                filename={`sample_${demo.title.toLowerCase().replace(/\s/g, '_')}.jpg`}
                                            />
                                        )}
                                        {'sampleCsv' in demo && (demo as any).sampleCsv ? (
                                            <DownloadButton
                                                filename={`sample_${demo.title.toLowerCase().replace(/\s/g, '_')}.csv`}
                                                data={(demo as any).sampleCsv} mime="text/csv"/>
                                        ) : null}
                                    </div>
                                </div>

                                <div className="mt-4 text-[11px] text-slate-500">
                                    Disclaimer: This section displays values hand-transcribed from the provided images
                                    for demo purposes; in production these would come from the OCR engine.
                                </div>
                            </div>

                            {/* Right: Schema + JSON/MD */}
                            <div className="p-5 overflow-auto">
                                <div className="rounded-xl border bg-white p-4 shadow-sm">
                                    <div className="font-semibold text-slate-800 mb-2">{demo.title} — Field Schema</div>
                                    <div className="overflow-auto">
                                        <table className="w-full text-sm">
                                            <thead>
                                            <tr>
                                                <th className="text-left px-2 py-1 border-b bg-slate-50">Field</th>
                                                <th className="text-left px-2 py-1 border-b bg-slate-50">Type</th>
                                                <th className="text-left px-2 py-1 border-b bg-slate-50">Description</th>
                                            </tr>
                                            </thead>
                                            <tbody>
                                            {demo.schema.map((f, i) => (
                                                <tr key={i} className="align-top">
                                                    <td className="px-2 py-1 border-b font-mono text-[12px]">{f.field}</td>
                                                    <td className="px-2 py-1 border-b text-sky-700">{f.type}</td>
                                                    <td className="px-2 py-1 border-b text-slate-600">{f.description}</td>
                                                </tr>
                                            ))}
                                            </tbody>
                                        </table>
                                    </div>
                                </div>

                                <div className="mt-4 grid grid-cols-1 gap-4">
                                    <div className="rounded-xl border bg-white p-4 shadow-sm">
                                        <div className="mb-2 font-semibold text-slate-800">Sample JSON</div>
                                        <pre
                                            className="text-xs bg-slate-900 text-slate-100 p-3 rounded-lg overflow-auto">
{demo.sampleJson}
                    </pre>
                                        <div className="mt-2">
                                            <DownloadButton
                                                filename={`sample_${demo.title.toLowerCase().replace(/\s/g, '_')}.json`}
                                                data={demo.sampleJson} mime="application/json"/>
                                        </div>
                                    </div>

                                    <div className="rounded-xl border bg-white p-4 shadow-sm">
                                        <div className="mb-2 font-semibold text-slate-800">Sample Markdown</div>
                                        <pre
                                            className="text-xs bg-slate-900 text-slate-100 p-3 rounded-lg overflow-auto">
{demo.sampleMd}
                    </pre>
                                        <div className="mt-2">
                                            <DownloadButton
                                                filename={`sample_${demo.title.toLowerCase().replace(/\s/g, '_')}.md`}
                                                data={demo.sampleMd} mime="text/markdown"/>
                                        </div>
                                    </div>
                                </div>

                                <div className="mt-4 flex flex-wrap gap-2">
                                    <a
                                        href={mailtoHref()}
                                        className="inline-flex items-center gap-2 rounded-lg bg-emerald-600 text-white px-4 py-2 text-sm font-semibold hover:bg-emerald-700"
                                    >
                                        🚀 Request a live demo
                                    </a>
                                    <span className="text-xs text-slate-500 self-center">Opens your email client with a prefilled message.</span>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Keyframes (scanning, shimmer, soft pulse) */}
            <style>{`
        @keyframes scanY {
          0% { transform: translateY(-20%); opacity:.92 }
          100% { transform: translateY(120%); opacity:.65 }
        }
        @keyframes shimmerKf {
          0% { background-position: -200% 0; }
          100% { background-position: 200% 0; }
        }
        .animate-shimmer {
          background-image: linear-gradient(90deg, rgba(226,232,240,0.6) 25%, rgba(203,213,225,0.9) 37%, rgba(226,232,240,0.6) 63%);
          background-size: 400% 100%;
          animation: shimmerKf 1.6s infinite linear;
        }
        @keyframes pulseSoft {
          0% { box-shadow: 0 0 0 0 rgba(16,185,129,0.45) }
          70% { box-shadow: 0 0 0 14px rgba(16,185,129,0) }
          100% { box-shadow: 0 0 0 0 rgba(16,185,129,0) }
        }
        .animate-pulse-soft { animation: pulseSoft 1.8s ease-out infinite; }
        @keyframes cornerDance {
          0%,100% { transform: translate(0,0) }
          50% { transform: translate(2px, -2px) }
        }
      `}</style>
        </section>
    )
}
