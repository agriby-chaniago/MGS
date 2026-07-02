import { useEffect, useState } from "react";
import { createApiKey } from "../api/auth";
import { httpBaseUrl } from "../api/client";
import { deleteDataset, listDatasets } from "../api/datasets";
import type { Dataset } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { useToast } from "../context/ToastContext";
import { Button, ConfirmDialog, Logo, PlanBadge } from "./ui";

interface Props {
  onSelectDataset: (dataset: Dataset) => void;
  activeDatasetId: string | null;
  auditInProgress: boolean;
  refreshTrigger: number;
}

function UpgradePanel() {
  const { plan, upgrade } = useAuth();
  const [loading, setLoading] = useState<"pro" | "max" | null>(null);

  async function handleUpgrade(target: "pro" | "max") {
    setLoading(target);
    try {
      await upgrade(target);
    } finally {
      setLoading(null);
    }
  }

  if (plan === "max") return null;

  return (
    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <p className="mb-2 text-xs font-medium text-slate-400">
        Upgrade buat batas lebih besar, semua analyzer, dan PDF export.
      </p>
      <div className="flex gap-2">
        {plan === "free" && (
          <Button
            variant="secondary"
            className="flex-1 !py-1.5 text-xs"
            disabled={loading !== null}
            onClick={() => handleUpgrade("pro")}
          >
            {loading === "pro" ? "..." : "Upgrade ke Pro"}
          </Button>
        )}
        <Button
          variant="secondary"
          className="flex-1 !border-amber-500/30 !py-1.5 text-xs !text-amber-300"
          disabled={loading !== null}
          onClick={() => handleUpgrade("max")}
        >
          {loading === "max" ? "..." : "Upgrade ke Max"}
        </Button>
      </div>
    </div>
  );
}

function ApiKeyPanel() {
  const { plan } = useAuth();
  const [loading, setLoading] = useState(false);
  const [key, setKey] = useState<string | null>(null);
  const [copiedField, setCopiedField] = useState<"key" | "command" | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Backend also enforces this (403 for free) — this check is purely so
  // free-tier users see "upgrade dulu" instead of a confusing API error.
  if (plan !== "pro" && plan !== "max") return null;

  const configureCommand = key ? `mgs configure --key ${key} --base-url ${httpBaseUrl()}` : "";

  async function handleGenerate() {
    setLoading(true);
    setError(null);
    setCopiedField(null);
    try {
      const res = await createApiKey();
      setKey(res.api_key);
    } catch {
      setError("Gagal generate API key.");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(field: "key" | "command", text: string) {
    await navigator.clipboard.writeText(text);
    setCopiedField(field);
    setTimeout(() => setCopiedField(null), 2000);
  }

  return (
    <div className="mt-4 rounded-xl border border-slate-800 bg-slate-950/60 p-3">
      <p className="mb-2 text-xs font-medium text-slate-400">
        API Key — buat akses lewat CLI (<code className="text-slate-300">mgs</code>) atau script.
      </p>

      {!key && (
        <Button
          variant="secondary"
          className="w-full !py-1.5 text-xs"
          disabled={loading}
          onClick={handleGenerate}
        >
          {loading ? "Generating..." : "Generate API Key"}
        </Button>
      )}

      {key && (
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-2">
            <code className="block break-all rounded-md bg-slate-900 px-2 py-1.5 text-[11px] text-emerald-300">
              {key}
            </code>
            <p className="text-[11px] text-amber-400">
              Simpan sekarang — key ini gak ditampilin lagi setelah ini.
            </p>
            <Button
              variant="secondary"
              className="w-full !py-1.5 text-xs"
              onClick={() => handleCopy("key", key)}
            >
              {copiedField === "key" ? "Tersalin ✓" : "Salin key"}
            </Button>
          </div>

          <div className="border-t border-slate-800 pt-3">
            <p className="mb-1.5 text-[11px] font-medium text-slate-400">
              Lalu di terminal (butuh{" "}
              <code className="text-slate-300">pip install -r cli/requirements.txt</code> sekali):
            </p>
            <code className="block break-all rounded-md bg-slate-900 px-2 py-1.5 text-[11px] text-slate-300">
              {configureCommand}
            </code>
            <Button
              variant="secondary"
              className="mt-2 w-full !py-1.5 text-xs"
              onClick={() => handleCopy("command", configureCommand)}
            >
              {copiedField === "command" ? "Tersalin ✓" : "Salin command"}
            </Button>
          </div>
        </div>
      )}
      {error && <p className="mt-2 text-xs text-rose-400">{error}</p>}
    </div>
  );
}

export default function Sidebar({ onSelectDataset, activeDatasetId, auditInProgress, refreshTrigger }: Props) {
  const { plan, logout } = useAuth();
  const { showToast } = useToast();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState(true);
  const [pendingDelete, setPendingDelete] = useState<Dataset | null>(null);

  async function refresh() {
    setLoading(true);
    try {
      setDatasets(await listDatasets());
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, [refreshTrigger]);

  async function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    setPendingDelete(null);
    try {
      await deleteDataset(target.id);
      await refresh();
      showToast(`"${target.name}" dihapus.`, "success");
    } catch {
      showToast(`Gagal menghapus "${target.name}".`, "error");
    }
  }

  return (
    <aside className="flex w-72 shrink-0 flex-col border-r border-slate-800 bg-slate-900/40 p-5">
      <Logo />

      <div className="mt-6 flex items-center justify-between">
        <PlanBadge plan={plan} />
        <Button variant="ghost" onClick={logout} className="!px-3 !py-1.5 text-xs">
          Logout
        </Button>
      </div>

      <UpgradePanel />
      <ApiKeyPanel />

      <h3 className="mt-8 mb-3 text-xs font-semibold uppercase tracking-wider text-slate-500">
        Riwayat Dataset
      </h3>

      {loading && <p className="text-sm text-slate-500">Memuat...</p>}
      {!loading && datasets.length === 0 && (
        <p className="text-sm text-slate-500">Belum ada dataset.</p>
      )}

      <ul className="flex flex-col gap-1.5">
        {datasets.map((d) => {
          const active = d.id === activeDatasetId;
          return (
            <li
              key={d.id}
              className={`group flex items-center gap-1 rounded-lg border px-1 transition ${
                active
                  ? "border-violet-500/40 bg-violet-500/10"
                  : "border-transparent hover:border-slate-700 hover:bg-slate-800/60"
              }`}
            >
              <button
                disabled={auditInProgress}
                onClick={() => onSelectDataset(d)}
                title={`${d.total_images} gambar`}
                className={`flex-1 truncate py-2 text-left text-sm disabled:cursor-not-allowed disabled:opacity-50 ${
                  active ? "font-medium text-violet-200" : "text-slate-300"
                }`}
              >
                {d.name}
                <span className="block text-xs text-slate-500">{d.total_images} gambar</span>
              </button>
              <button
                disabled={auditInProgress}
                onClick={() => setPendingDelete(d)}
                className="rounded-md p-1.5 text-slate-500 opacity-0 transition hover:bg-slate-700 hover:text-rose-400 group-hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-30"
                title="Hapus dataset"
              >
                🗑
              </button>
            </li>
          );
        })}
      </ul>

      <ConfirmDialog
        open={pendingDelete !== null}
        title="Hapus dataset?"
        message={
          pendingDelete
            ? `"${pendingDelete.name}" (${pendingDelete.total_images} gambar) akan dihapus permanen, termasuk file di storage. Gak bisa dibatalkan.`
            : ""
        }
        confirmLabel="Hapus"
        danger
        onConfirm={confirmDelete}
        onCancel={() => setPendingDelete(null)}
      />
    </aside>
  );
}
