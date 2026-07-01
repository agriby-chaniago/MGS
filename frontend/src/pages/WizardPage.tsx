import { useState } from "react";
import Sidebar from "../components/Sidebar";
import UploadPage from "./UploadPage";
import AuditPage from "./AuditPage";
import ReportPage from "./ReportPage";
import type { Dataset, UploadResponse } from "../api/types";

type Step = 1 | 2 | 3;

const STEPS: { id: Step; label: string }[] = [
  { id: 1, label: "Upload" },
  { id: 2, label: "Audit" },
  { id: 3, label: "Laporan" },
];

function StepIndicator({ step }: { step: Step }) {
  return (
    <div className="mb-8 flex items-center gap-2">
      {STEPS.map((s, i) => (
        <div key={s.id} className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <div
              className={`flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold transition ${
                s.id === step
                  ? "bg-violet-600 text-white"
                  : s.id < step
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-slate-800 text-slate-500"
              }`}
            >
              {s.id < step ? "✓" : s.id}
            </div>
            <span
              className={`text-sm font-medium ${s.id === step ? "text-white" : "text-slate-500"}`}
            >
              {s.label}
            </span>
          </div>
          {i < STEPS.length - 1 && <div className="mx-2 h-px w-8 bg-slate-800" />}
        </div>
      ))}
    </div>
  );
}

export default function WizardPage() {
  const [step, setStep] = useState<Step>(1);
  const [dataset, setDataset] = useState<UploadResponse | null>(null);
  const [auditId, setAuditId] = useState<string | null>(null);

  function handleUploaded(data: UploadResponse) {
    setDataset(data);
    setStep(2);
  }

  function handleSelectFromSidebar(d: Dataset) {
    setDataset({
      dataset_id: d.id,
      name: d.name,
      class_count: d.class_count,
      total_images: d.total_images,
      file_size_mb: d.file_size_mb,
      invalid_files: [],
    });
    setAuditId(null);
    setStep(2);
  }

  function handleAuditCompleted(id: string) {
    setAuditId(id);
    setStep(3);
  }

  function handleReset() {
    setDataset(null);
    setAuditId(null);
    setStep(1);
  }

  const auditInProgress = step === 2 && !auditId;

  return (
    <div className="flex min-h-screen bg-slate-950">
      <Sidebar
        onSelectDataset={handleSelectFromSidebar}
        activeDatasetId={dataset?.dataset_id ?? null}
        auditInProgress={auditInProgress}
      />
      <main className="flex-1 overflow-y-auto p-10">
        <div className="mx-auto max-w-3xl">
          <StepIndicator step={step} />
          {step === 1 && (
            <UploadPage selected={dataset} onUploaded={handleUploaded} onContinue={() => setStep(2)} />
          )}
          {step === 2 && dataset && (
            <AuditPage
              datasetId={dataset.dataset_id}
              onCompleted={handleAuditCompleted}
              onBack={() => setStep(1)}
            />
          )}
          {step === 3 && auditId && (
            <ReportPage auditId={auditId} onReset={handleReset} onBack={() => setStep(2)} />
          )}
        </div>
      </main>
    </div>
  );
}
