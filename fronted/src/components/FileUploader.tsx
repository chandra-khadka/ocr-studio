import { useState } from 'react'
import { toBase64 } from '../utils/file'

type Props = {
  onSelect: (file: File, base64: string) => void
  accept?: string
}

export default function FileUploader({ onSelect, accept }: Props) {
  const [dragOver, setDragOver] = useState(false)

  async function handleFiles(files: FileList | null) {
    if (!files || !files[0]) return
    const file = files[0]
    const b64 = await toBase64(file)
    onSelect(file, b64)
  }

  return (
    <div
      className={`border-2 border-dashed rounded-2xl p-8 bg-white ${dragOver ? 'border-primary' : 'border-gray-300'}`}
      onDragOver={e => { e.preventDefault(); setDragOver(true) }}
      onDragLeave={() => setDragOver(false)}
      onDrop={e => { e.preventDefault(); setDragOver(false); handleFiles(e.dataTransfer.files) }}
    >
      <div className="text-center text-gray-600">
        <p className="mb-2">Drag & drop a PDF/Image, or</p>
        <label className="btn cursor-pointer">
          Browse<input type="file" className="hidden" accept={accept} onChange={e => handleFiles(e.target.files)} />
        </label>
      </div>
    </div>
  )
}
