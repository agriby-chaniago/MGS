import { useEffect, useRef, useState } from "react";
import { createAudit, getAudit, retryAudit } from "../api/audits";
import { wsBaseUrl } from "../api/client";
import type { Audit } from "../api/types";
import { BackLink, Button, Card, StatusBadge } from "../components/ui";

interface Props {
  datasetId: string;
  onCompleted: (auditId: string) => void;
  onBack: () => void;
}

type AnalyzerStatus = "waiting" | "completed" | "failed";

const analyzerIcon: Record<AnalyzerStatus, string> = {
  completed: "✓",
  failed: "✕",
  waiting: "…",
};

export default function AuditPage({ datasetId, onCompleted, onBack }: Props) {
  const [audit, setAudit] = useState<Audit | null>(null);
  const [force, setForce] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [analyzerStatuses, setAnalyzerStatuses] = useState<Record<string, AnalyzerStatus>>({});
  const wsRef = useRef<WebSocket | null>(null);

  function closeSocket() {
    wsRef.current?.close();
    wsRef.current = null;
  }

  function watchProgress(auditId: string, analyzers: string[]) {
    setAnalyzerStatuses(Object.fromEntries(analyzers.map((a) => [a, "waiting"])));

    const token = localStorage.getItem("mgs_token");
    const ws = new WebSocket(`${wsBaseUrl()}/ws/audits/${auditId}?token=${token}`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.type === "snapshot") {
        // Sent immediately on connect — covers the case where the audit
        // already finished before this WS handshake completed (trivial
        // for a tiny/cached dataset), since there's no event replay.
        setAnalyzerStatuses((prev) => ({ ...prev, ...msg.analyzer_statuses }));
        if (msg.audit_status === "completed") {
          closeSocket();
          onCompleted(auditId);
        } else if (msg.audit_status === "failed") {
          closeSocket();
          getAudit(auditId).then(setAudit);
        }
      } else if (msg.type === "analyzer_update") {
        setAnalyzerStatuses((prev) => ({ ...prev, [msg.analyzer_type]: msg.status }));
      } else if (msg.type === "audit_completed") {
        closeSocket();
        if (msg.status === "completed") {
          onCompleted(auditId);
        } else {
          // Refetch to get the error_message for display.
          getAudit(auditId).then(setAudit);
        }
      }
    };

    ws.onerror = () => {
      // Falls back to nothing further here — a dropped WS connection mid-
      // audit is an accepted demo-scope limitation (see plan Workstream C's
      // Known Limitations: no reconnect/polling fallback).
      setError("Koneksi live progress terputus.");
    };
  }

  async function handleCreate() {
    setError(null);
    try {
      const created = await createAudit(datasetId, force);
      setAudit(created);
      if (created.status === "completed" || created.cached) {
        onCompleted(created.id);
        return;
      }
      watchProgress(created.id, created.requested_analyzers);
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail ?? "Gagal membuat audit.");
    }
  }

  async function handleRetry() {
    if (!audit) return;
    setError(null);
    try {
      const retried = await retryAudit(audit.id);
      setAudit(retried);
      watchProgress(retried.id, retried.requested_analyzers);
    } catch (e) {
      const detail = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(detail ?? "Retry gagal.");
    }
  }

  useEffect(() => closeSocket, []);

  return (
    <div>
      {/* Only safe to leave before an audit is actively running — once
          watchProgress starts, the Sidebar's auditInProgress lock also
          kicks in, so hiding this here keeps both consistent. */}
      {!audit && <BackLink onClick={onBack} label="Kembali ke Upload" />}
      <h1 className="mb-1 text-2xl font-semibold text-white">Audit</h1>
      <p className="mb-6 text-sm text-slate-400">Jalankan pemeriksaan otomatis untuk dataset ini.</p>

      {!audit && (
        <Card className="p-6">
          <label className="mb-4 flex items-center gap-2 text-sm text-slate-300">
            <input
              type="checkbox"
              checked={force}
              onChange={(e) => setForce(e.target.checked)}
              className="h-4 w-4 rounded border-slate-600 bg-slate-800 accent-violet-600"
            />
            Force re-audit (abaikan cache)
          </label>
          {error && <p className="mb-4 text-sm text-rose-400">{error}</p>}
          <Button onClick={handleCreate}>Buat Audit</Button>
        </Card>
      )}

      {audit && (
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-3">
            <StatusBadge status={audit.status} />
            {audit.cached && <span className="text-sm text-amber-400">Hasil dari cache</span>}
          </div>
          {error && <p className="text-sm text-rose-400">{error}</p>}

          <Card className="divide-y divide-slate-800">
            {audit.requested_analyzers.map((a) => {
              const status = analyzerStatuses[a] ?? "waiting";
              return (
                <div key={a} className="flex items-center justify-between px-5 py-3.5">
                  <span className="text-sm font-medium capitalize text-slate-200">{a}</span>
                  <span
                    className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${
                      status === "completed"
                        ? "bg-emerald-500/20 text-emerald-300"
                        : status === "failed"
                          ? "bg-rose-500/20 text-rose-300"
                          : "animate-pulse bg-slate-700 text-slate-400"
                    }`}
                  >
                    {analyzerIcon[status]}
                  </span>
                </div>
              );
            })}
          </Card>

          {audit.status === "failed" && (
            <div>
              <p className="mb-3 text-sm text-rose-400">{audit.error_message}</p>
              <Button variant="danger" onClick={handleRetry}>
                Coba Lagi
              </Button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
