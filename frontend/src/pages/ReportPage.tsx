import { useEffect, useState } from "react";
import { downloadPdf, getReport } from "../api/reports";
import type { ReportDetail } from "../api/types";
import { useAuth } from "../context/AuthContext";

interface Props {
  auditId: string;
  onReset: () => void;
}

export default function ReportPage({ auditId, onReset }: Props) {
  const { plan } = useAuth();
  const [report, setReport] = useState<ReportDetail | null>(null);
  const [pdfError, setPdfError] = useState(false);

  useEffect(() => {
    getReport(auditId).then(setReport);
  }, [auditId]);

  async function handleDownloadPdf() {
    setPdfError(false);
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
    }
  }

  if (!report) return <p>Memuat laporan...</p>;

  return (
    <div className="step-panel">
      <h2>Step 3 — Laporan</h2>
      <div className="health-score">
        <span className="score">{report.health_score?.toFixed(4) ?? "-"}</span>
        <span className="grade">Grade {report.grade ?? "-"}</span>
      </div>
      {report.components && (
        <ul className="components">
          <li>Integrity: {report.components.I.toFixed(2)}</li>
          <li>Uniqueness: {report.components.U.toFixed(2)}</li>
          <li>Distribution: {report.components.D.toFixed(2)}</li>
          <li>Quality: {report.components.Q.toFixed(2)}</li>
        </ul>
      )}

      {report.analysis_results.map((r) => (
        <details key={r.analyzer_type}>
          <summary>
            {r.analyzer_type} — {r.status}
          </summary>
          <pre>{JSON.stringify(r.result_payload.summary, null, 2)}</pre>
        </details>
      ))}

      {plan === "free" ? (
        <p className="notice">Download PDF hanya untuk paket Pro/Max.</p>
      ) : (
        <button onClick={handleDownloadPdf}>Download PDF</button>
      )}
      {pdfError && <p className="error">Gagal mengunduh PDF.</p>}

      <button onClick={onReset}>Dataset Baru</button>
    </div>
  );
}
