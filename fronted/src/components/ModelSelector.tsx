import { DocumentFormat, DocumentType, Language, OCRProvider, CorrectionProvider } from '../types/enums'

type Props = {
  language: Language
  setLanguage: (v: Language) => void
  documentType: DocumentType
  setDocumentType: (v: DocumentType) => void
  documentFormat: DocumentFormat
  setDocumentFormat: (v: DocumentFormat) => void
  ocrProvider: OCRProvider
  setOcrProvider: (v: OCRProvider) => void
  correctionProvider: CorrectionProvider
  setCorrectionProvider: (v: CorrectionProvider) => void
  modelOptions: { ocr: string[], correction: string[] }
  selectedOCRModel: string
  setSelectedOCRModel: (m: string) => void
  selectedCorrectionModel: string
  setSelectedCorrectionModel: (m: string) => void
}

export default function ModelSelector(props: Props) {
  const {
    language, setLanguage,
    documentType, setDocumentType,
    documentFormat, setDocumentFormat,
    ocrProvider, setOcrProvider,
    correctionProvider, setCorrectionProvider,
    modelOptions, selectedOCRModel, setSelectedOCRModel,
    selectedCorrectionModel, setSelectedCorrectionModel
  } = props

  return (
    <div className="grid md:grid-cols-2 gap-4">
      <div>
        <label className="label">Language</label>
        <select className="select" value={language} onChange={e => setLanguage(e.target.value as any)}>
          {Object.values(Language).map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Document Type</label>
        <select className="select" value={documentType} onChange={e => setDocumentType(e.target.value as any)}>
          {Object.values(DocumentType).map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Document Format</label>
        <select className="select" value={documentFormat} onChange={e => setDocumentFormat(e.target.value as any)}>
          {Object.values(DocumentFormat).map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="label">OCR Provider</label>
        <select className="select" value={ocrProvider} onChange={e => setOcrProvider(e.target.value as any)}>
          {Object.values(OCRProvider).map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="label">OCR Model</label>
        <select className="select" value={selectedOCRModel} onChange={e => setSelectedOCRModel(e.target.value)}>
          {modelOptions.ocr.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Correction Provider</label>
        <select className="select" value={correctionProvider} onChange={e => setCorrectionProvider(e.target.value as any)}>
          {Object.values(CorrectionProvider).map(v => <option key={v} value={v}>{v}</option>)}
        </select>
      </div>
      <div>
        <label className="label">Correction Model</label>
        <select className="select" value={selectedCorrectionModel} onChange={e => setSelectedCorrectionModel(e.target.value)}>
          {modelOptions.correction.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>
    </div>
  )
}
