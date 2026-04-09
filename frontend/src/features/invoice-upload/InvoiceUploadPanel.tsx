import { useState } from 'react'
import type { FormEvent } from 'react'

interface InvoiceUploadPanelProps {
  canGenerate: boolean
  isGenerating: boolean
  isUploading: boolean
  onGenerate: () => Promise<void>
  onUpload: (file: File) => Promise<void>
}

export function InvoiceUploadPanel({
  canGenerate,
  isGenerating,
  isUploading,
  onGenerate,
  onUpload,
}: InvoiceUploadPanelProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (selectedFile === null) {
      return
    }
    await onUpload(selectedFile)
  }

  return (
    <section className="card upload-panel">
      <h2>Invoice Upload</h2>
      <form className="upload-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field-label" htmlFor="invoice-file">
          PDF file
        </label>
        <input
          id="invoice-file"
          accept="application/pdf,.pdf"
          type="file"
          onChange={(event) => {
            const nextFile = event.target.files?.[0] ?? null
            setSelectedFile(nextFile)
          }}
        />
        <div className="button-row">
          <button disabled={selectedFile === null || isUploading} type="submit">
            {isUploading ? 'Uploading...' : 'Upload invoice'}
          </button>
          <button
            className="button-secondary"
            disabled={!canGenerate || isGenerating}
            onClick={() => void onGenerate()}
            type="button"
          >
            {isGenerating ? 'Generating...' : 'Generate suggestion'}
          </button>
        </div>
      </form>
    </section>
  )
}
