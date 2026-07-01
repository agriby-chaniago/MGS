import { useRef, useState, type DragEvent } from "react";
import { uploadDataset } from "../api/datasets";
import type { UploadResponse } from "../api/types";
import { Button, Card, Input } from "../components/ui";

interface Props {
  selected: UploadResponse | null;
  onUploaded: (data: UploadResponse) => void;
  onContinue: () => void;
}

export default function UploadPage({ selected, onUploaded, onContinue }: Props) {
  const fileRef = useRef<HTMLInputElement>(null);
  const [name, setName] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function pickFile(f: File) {
    setFile(f);
    setError(null);
  }

  function handleDrop(e: DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) pickFile(f);
  }

  async function handleUpload() {
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
      <div>
        <h1 className="mb-1 text-2xl font-semibold text-white">Dataset Terpilih</h1>
        <p className="mb-6 text-sm text-slate-400">Dataset sudah siap — lanjut ke tahap audit.</p>
        <Card className="p-6">
          <p className="text-lg font-medium text-white">{selected.name}</p>
          <div className="mt-3 flex gap-6 text-sm text-slate-400">
            <span>
              <span className="font-semibold text-slate-200">{selected.total_images}</span> gambar
            </span>
            <span>
              <span className="font-semibold text-slate-200">{selected.class_count}</span> kelas
            </span>
            <span>
              <span className="font-semibold text-slate-200">{selected.file_size_mb}</span> MB
            </span>
          </div>
        </Card>
        <Button onClick={onContinue} className="mt-6">
          Lanjut ke Audit →
        </Button>
      </div>
    );
  }

  return (
    <div>
      <h1 className="mb-1 text-2xl font-semibold text-white">Upload Dataset</h1>
      <p className="mb-6 text-sm text-slate-400">
        Format ZIP berisi subfolder per kelas (mis. <code className="text-slate-300">cats/</code>,{" "}
        <code className="text-slate-300">dogs/</code>).
      </p>

      <Input
        type="text"
        placeholder="Nama dataset (opsional)"
        value={name}
        onChange={(e) => setName(e.target.value)}
        className="mb-4"
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center gap-2 rounded-2xl border-2 border-dashed px-6 py-14 text-center transition ${
          dragOver ? "border-violet-500 bg-violet-500/10" : "border-slate-700 hover:border-slate-600"
        }`}
      >
        <input
          type="file"
          accept=".zip"
          ref={fileRef}
          className="hidden"
          onChange={(e) => e.target.files?.[0] && pickFile(e.target.files[0])}
        />
        {file ? (
          <>
            <p className="font-medium text-white">{file.name}</p>
            <p className="text-sm text-slate-500">{(file.size / (1024 * 1024)).toFixed(1)} MB — klik buat ganti</p>
          </>
        ) : (
          <>
            <p className="font-medium text-slate-300">Tarik file ZIP ke sini, atau klik buat pilih</p>
            <p className="text-sm text-slate-500">Maksimum ukuran tergantung paket kamu</p>
          </>
        )}
      </div>

      {error && <p className="mt-4 text-sm text-rose-400">{error}</p>}

      <Button onClick={handleUpload} disabled={uploading || !file} className="mt-6">
        {uploading ? "Mengunggah..." : "Upload"}
      </Button>
    </div>
  );
}
