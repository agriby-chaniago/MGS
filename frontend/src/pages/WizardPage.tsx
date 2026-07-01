import { useState } from "react";
import Sidebar from "../components/Sidebar";
import UploadPage from "./UploadPage";
import AuditPage from "./AuditPage";
import ReportPage from "./ReportPage";
import type { Dataset, UploadResponse } from "../api/types";

type Step = 1 | 2 | 3;

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
    <div className="wizard-layout">
      <Sidebar
        onSelectDataset={handleSelectFromSidebar}
        activeDatasetId={dataset?.dataset_id ?? null}
        auditInProgress={auditInProgress}
      />
      <main>
        {step === 1 && <UploadPage selected={dataset} onUploaded={handleUploaded} onContinue={() => setStep(2)} />}
        {step === 2 && dataset && (
          <AuditPage datasetId={dataset.dataset_id} onCompleted={handleAuditCompleted} />
        )}
        {step === 3 && auditId && <ReportPage auditId={auditId} onReset={handleReset} />}
      </main>
    </div>
  );
}
