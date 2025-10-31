type Props = {
  prompt: string
  setPrompt: (v: string) => void
  label?: string
  placeholder?: string
}
export default function PromptEditor({ prompt, setPrompt, label = 'Custom Extraction Prompt', placeholder }: Props) {
  return (
    <div>
      <label className="label">{label}</label>
      <textarea
        className="textarea"
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        placeholder={placeholder || "e.g., Extract title, dates, and table rows into Markdown."}
      />
    </div>
  )
}
