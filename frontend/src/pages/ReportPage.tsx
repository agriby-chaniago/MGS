import { useEffect, useState } from "react";
import { downloadPdf, getReport } from "../api/reports";
import type { ReportDetail } from "../api/types";
import { useAuth } from "../context/AuthContext";
import { BackLink, Button, Card, StatusBadge } from "../components/ui";

interface Props {
  auditId: string;
  onReset: () => void;
  onBack: () => void;
}

const gradeColor: Record<string, string> = {
  A: "text-emerald-400",
  B: "text-sky-400",
  C: "text-amber-400",
  D: "text-orange-400",
  F: "text-rose-400",
};

const COMPONENTS: { key: "I" | "U" | "D" | "Q"; label: string; desc: string; weight: number }[] = [
  { key: "I", label: "Integrity", desc: "1 − corruption rate", weight: 30 },
  { key: "U", label: "Uniqueness", desc: "1 − duplicate rate (pHash)", weight: 25 },
  { key: "D", label: "Distribution", desc: "1 − gini coefficient", weight: 25 },
  { key: "Q", label: "Quality", desc: "% gambar dalam ±1σ resolusi", weight: 20 },
];

function ScoreRing({ score, grade }: { score: number; grade: string }) {
  const pct = Math.round(score * 100);
  return (
    <div
      className="relative flex h-32 w-32 shrink-0 items-center justify-center rounded-full"
      style={{
        background: `conic-gradient(#8b5cf6 ${pct * 3.6}deg, #1e293b 0deg)`,
      }}
    >
      <div className="flex h-24 w-24 flex-col items-center justify-center rounded-full bg-slate-950">
        <span className="text-2xl font-bold text-white">{score.toFixed(2)}</span>
        <span className={`text-sm font-semibold ${gradeColor[grade] ?? "text-slate-300"}`}>
          Grade {grade}
        </span>
      </div>
    </div>
  );
}

export default function ReportPage({ auditId, onReset, onBack }: Props) {
  const { plan } = useAuth();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [pdfError, setPdfError] = useState(false);
  const [pdfLoading, setPdfLoading] = useState(false);

  useEffect(() => {
    getReport(auditId).then(setReport);
  }, [auditId]);

  async function handleDownloadPdf() {
    setPdfError(false);
    setPdfLoading(true);
    try {
      const blob = await downloadPdf(auditId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `report_${auditId}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setPdfError(true);
    } finally {
      setPdfLoading(false);
    }
  }

  if (!report) return <p className="text-sm text-slate-400">Memuat laporan...</p>;

  return (
    <div className="flex flex-col gap-6">
      <div>
        <BackLink onClick={onBack} label="Kembali ke Audit" />
        <h1 className="mb-1 text-2xl font-semibold text-white">Laporan</h1>
        <p className="text-sm text-slate-400">Ringkasan kualitas dataset dan hasil per-analyzer.</p>
      </div>

      <Card className="flex items-center gap-6 p-6">
        <ScoreRing score={report.health_score ?? 0} grade={report.grade ?? "-"} />
        <div className="flex-1">
          <p className="text-sm text-slate-400">Health Score</p>
          <p className="text-lg font-medium text-white">
            Dataset {(report.health_score ?? 0) >= 0.8 ? "siap dipakai" : "perlu diperbaiki"}
          </p>
        </div>
      </Card>

      {report.components && (
        <Card className="flex flex-col gap-4 p-6">
          {COMPONENTS.map(({ key, label, desc, weight }) => {
            const val = report.components![key];
            return (
              <div key={key}>
                <div className="mb-1 flex items-baseline justify-between">
                  <span className="text-sm font-medium text-slate-200">
                    {label} <span className="text-xs text-slate-500">bobot {weight}%</span>
                  </span>
                  <span className="text-sm font-semibold text-slate-300">{val.toFixed(2)}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-800">
                  <div
                    className="h-full rounded-full bg-gradient-to-r from-violet-500 to-fuchsia-500"
                    style={{ width: `${Math.max(0, Math.min(1, val)) * 100}%` }}
                  />
                </div>
                <p className="mt-1 text-xs text-slate-500">{desc}</p>
              </div>
            );
          })}
        </Card>
      )}

      <div className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Detail per-analyzer
        </h2>
        {report.analysis_results.map((r) => {
          const findings = r.result_payload.findings ?? [];
          return (
            <details key={r.analyzer_type} className="group rounded-xl border border-slate-800 bg-slate-900/60">
              <summary className="flex cursor-pointer list-none items-center justify-between px-5 py-3.5">
                <span className="text-sm font-medium capitalize text-slate-200">{r.analyzer_type}</span>
                <div className="flex items-center gap-3">
                  <StatusBadge status={r.status} />
                  <span className="text-slate-500 transition group-open:rotate-180">▾</span>
                </div>
              </summary>
              <div className="flex flex-col gap-3 border-t border-slate-800 px-5 py-4">
                {r.error_message && <p className="text-sm text-rose-400">{r.error_message}</p>}

                {Object.keys(r.result_payload.summary ?? {}).length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Summary
                    </p>
                    <pre className="overflow-x-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-400">
                      {JSON.stringify(r.result_payload.summary, null, 2)}
                    </pre>
                  </div>
                )}

                {findings.length > 0 && (
                  <div>
                    <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                      Findings ({findings.length} item{findings.length !== 1 ? "s" : ""})
                    </p>
                    <div className="max-h-64 overflow-y-auto rounded-lg bg-slate-950 p-3">
                      <ul className="flex flex-col gap-1 text-xs text-slate-400">
                        {findings.slice(0, 20).map((f, i) => (
                          <li key={i} className="border-b border-slate-900 pb-1 last:border-0">
                            {typeof f === "string" ? f : JSON.stringify(f)}
                          </li>
                        ))}
                      </ul>
                      {findings.length > 20 && (
                        <p className="mt-2 text-xs text-slate-600">
                          +{findings.length - 20} lagi (dipotong, lihat PDF buat daftar lengkap)
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </details>
          );
        })}
      </div>

      <div className="flex items-center gap-3">
        {plan === "free" ? (
          <p className="text-sm text-amber-400">Download PDF hanya untuk paket Pro/Max.</p>
        ) : (
          <Button onClick={handleDownloadPdf} disabled={pdfLoading}>
            {pdfLoading ? "Membuat PDF..." : "Download PDF"}
          </Button>
        )}
        <Button variant="secondary" onClick={onReset}>
          Dataset Baru
        </Button>
      </div>
      {pdfError && <p className="text-sm text-rose-400">Gagal mengunduh PDF.</p>}
    </div>
  );
}
