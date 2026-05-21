import { useRef, useState } from 'react'

interface Props {
  partNumber: string
  onConfirm: (files: File[]) => void
  onCancel: () => void
}

export default function BoxUploadModal({ partNumber, onConfirm, onCancel }: Props) {
  const [files, setFiles] = useState<File[]>([])
  const [dragging, setDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function addFiles(incoming: FileList | null) {
    if (!incoming) return
    const next = [...files]
    for (const f of Array.from(incoming)) {
      if (!next.find(x => x.name === f.name && x.size === f.size)) next.push(f)
    }
    setFiles(next)
  }

  function removeFile(idx: number) {
    setFiles(prev => prev.filter((_, i) => i !== idx))
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragging(false)
    addFiles(e.dataTransfer.files)
  }

  const totalSize = files.reduce((s, f) => s + f.size, 0)
  function fmt(bytes: number) {
    if (bytes < 1024) return `${bytes} B`
    if (bytes < 1024 ** 2) return `${(bytes / 1024).toFixed(1)} KB`
    return `${(bytes / 1024 ** 2).toFixed(1)} MB`
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 1000,
      background: 'rgba(0,0,0,0.45)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }}>
      <div style={{
        background: '#fff', borderRadius: 10, padding: 28,
        width: 480, maxWidth: '95vw', boxShadow: '0 8px 32px rgba(0,0,0,0.18)',
      }}>
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
          <div>
            <div style={{ fontWeight: 700, fontSize: 15 }}>Create Box Folder</div>
            <div style={{ fontSize: 12, color: '#666', marginTop: 2 }}>
              {partNumber} — drag files to upload, or skip to create an empty folder
            </div>
          </div>
          <button
            onClick={onCancel}
            style={{ background: 'none', border: 'none', fontSize: 18, cursor: 'pointer', color: '#666', lineHeight: 1 }}
          >×</button>
        </div>

        {/* Drop zone */}
        <div
          onDragOver={e => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={onDrop}
          onClick={() => inputRef.current?.click()}
          style={{
            border: `2px dashed ${dragging ? '#0B0458' : '#c0c8d4'}`,
            borderRadius: 8,
            padding: '28px 16px',
            textAlign: 'center',
            cursor: 'pointer',
            background: dragging ? '#eef0ff' : '#f8f9fa',
            transition: 'all 0.15s',
            marginBottom: 14,
          }}
        >
          <div style={{ fontSize: 28, marginBottom: 6 }}>📁</div>
          <div style={{ fontSize: 13, color: '#444', fontWeight: 600 }}>
            {dragging ? 'Drop files here' : 'Drag & drop files, or click to browse'}
          </div>
          <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
            Drawings, specs, models — any file type
          </div>
        </div>
        <input
          ref={inputRef}
          type="file"
          multiple
          style={{ display: 'none' }}
          onChange={e => addFiles(e.target.files)}
        />

        {/* File list */}
        {files.length > 0 && (
          <div style={{
            border: '1px solid #e0e4ea', borderRadius: 6,
            marginBottom: 14, maxHeight: 180, overflowY: 'auto',
          }}>
            {files.map((f, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                padding: '5px 10px', borderBottom: i < files.length - 1 ? '1px solid #f0f0f0' : 'none',
                fontSize: 12,
              }}>
                <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginRight: 8 }}>
                  📄 {f.name}
                </span>
                <span style={{ color: '#888', whiteSpace: 'nowrap', marginRight: 8 }}>{fmt(f.size)}</span>
                <button
                  onClick={e => { e.stopPropagation(); removeFile(i) }}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#d93025', fontSize: 14, padding: '0 2px' }}
                >×</button>
              </div>
            ))}
            <div style={{ padding: '4px 10px', fontSize: 11, color: '#888', background: '#fafafa', borderTop: '1px solid #f0f0f0' }}>
              {files.length} file{files.length !== 1 ? 's' : ''} · {fmt(totalSize)} total
            </div>
          </div>
        )}

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={{ padding: '6px 14px', fontSize: 13 }}>
            Cancel
          </button>
          <button
            onClick={() => onConfirm([])}
            style={{ padding: '6px 14px', fontSize: 13, color: '#555' }}
          >
            Skip files — empty folder
          </button>
          <button
            className="primary"
            onClick={() => onConfirm(files)}
            style={{ padding: '6px 16px', fontSize: 13 }}
          >
            {files.length > 0 ? `Upload ${files.length} file${files.length !== 1 ? 's' : ''} + Create` : 'Create Folder'}
          </button>
        </div>
      </div>
    </div>
  )
}
