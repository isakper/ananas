import { useState } from 'react'
import type { FormEvent } from 'react'

interface InvoiceUploadPanelProps {
  isUploading: boolean
  onUpload: (files: File[]) => Promise<void>
}

export function InvoiceUploadPanel({
  isUploading,
  onUpload,
}: InvoiceUploadPanelProps) {
  const [selectedFiles, setSelectedFiles] = useState<File[]>([])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (selectedFiles.length === 0) {
      return
    }
    await onUpload(selectedFiles)
  }

  return (
    <section className="card upload-panel">
      <h2>Invoice Upload</h2>
      <form className="upload-form" onSubmit={(event) => void handleSubmit(event)}>
        <label className="field-label" htmlFor="invoice-file">
          PDF files
        </label>
        <input
          id="invoice-file"
          accept="application/pdf,.pdf"
          type="file"
          multiple
          onChange={(event) => {
            const files = event.target.files
            if (files === null) {
              setSelectedFiles([])
              return
            }
            setSelectedFiles(Array.from(files))
          }}
        />
        {selectedFiles.length > 0 ? (
          <p className="small-muted">{selectedFiles.length} file(s) selected</p>
        ) : null}
        <div className="button-row">
          <button disabled={selectedFiles.length === 0 || isUploading} type="submit">
            {isUploading ? 'Uploading...' : 'Upload selected'}
          </button>
        </div>
      </form>
    </section>
  )
}
