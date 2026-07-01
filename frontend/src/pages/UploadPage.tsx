import { useRef, useState } from "react";
import { uploadDataset } from "../api/datasets";
import type { UploadResponse } from "../api/types";

interface Props {
  selected: UploadResponse | null;
  onUploaded: (data: UploadResponse) => void;
  onContinue: () => void;
}

export default function UploadPage({ selected, onUploaded, onContinue }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleUpload() {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      const data = await uploadDataset(file, name || file.name.replace(/\.zip$/i, ""));
      onUploaded(data);
    } catch (e) {
      const status = (e as { response?: { status?: number; data?: { detail?: string } } }).response?.status;
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      if (status === 413) {
        setError(detail ?? "File terlalu besar untuk paket Anda. Upgrade paket untuk batas lebih besar.");
      } else {
        setError(detail ?? "Upload gagal.");
      }
    } finally {
      setUploading(false);
    }
  }

  if (selected) {
    return (
      <div className="step-panel">
        <h2>Step 1 — Dataset Terpilih</h2>
        <p>
          <strong>{selected.name}</strong> — {selected.total_images} gambar, {selected.class_count} kelas,{" "}
          {selected.file_size_mb}MB
        </p>
        <button onClick={onContinue}>Lanjut ke Audit →</button>
      </div>
    );
  }

  return (
    <div className="step-panel">
      <h2>Step 1 — Upload Dataset</h2>
      <input type="text" placeholder="Nama dataset (opsional)" value={name} onChange={(e) => setName(e.target.value)} />
      <input type="file" accept=".zip" ref={fileRef} />
      {error && <p className="error">{error}</p>}
      <button onClick={handleUpload} disabled={uploading}>
        {uploading ? "Mengunggah..." : "Upload"}
      </button>
    </div>
  );
}
