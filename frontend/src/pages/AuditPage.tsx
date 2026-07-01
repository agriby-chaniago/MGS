import { useEffect, useRef, useState } from "react";
import { createAudit, getAudit, retryAudit } from "../api/audits";
import { wsBaseUrl } from "../api/client";
import type { Audit } from "../api/types";

interface Props {
  datasetId: string;
  onCompleted: (auditId: string) => void;
}

type AnalyzerStatus = "waiting" | "completed" | "failed";

export default function AuditPage({ datasetId, onCompleted }: Props) {
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

  const analyzerLabel = (status: AnalyzerStatus | undefined) =>
    status === "completed" ? "SELESAI" : status === "failed" ? "GAGAL" : "MENUNGGU";

  return (
    <div className="step-panel">
      <h2>Step 2 — Audit</h2>
      {!audit && (
        <>
          <label>
            <input type="checkbox" checked={force} onChange={(e) => setForce(e.target.checked)} />
            Force re-audit (abaikan cache)
          </label>
          {error && <p className="error">{error}</p>}
          <button onClick={handleCreate}>Buat Audit</button>
        </>
      )}
      {audit && (
        <>
          <p>Status: {audit.status}</p>
          {audit.cached && <p className="notice">Menggunakan hasil audit sebelumnya (cached).</p>}
          {error && <p className="error">{error}</p>}
          <table>
            <thead>
              <tr>
                <th>Analyzer</th>
                <th>Status (live)</th>
              </tr>
            </thead>
            <tbody>
              {audit.requested_analyzers.map((a) => (
                <tr key={a}>
                  <td>{a}</td>
                  <td>{analyzerLabel(analyzerStatuses[a])}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {audit.status === "failed" && (
            <>
              <p className="error">{audit.error_message}</p>
              <button onClick={handleRetry}>Coba Lagi</button>
            </>
          )}
        </>
      )}
    </div>
  );
}
