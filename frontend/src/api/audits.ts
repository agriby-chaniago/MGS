import { apiClient } from "./client";
import type { Audit, StandardResponse } from "./types";

export async function createAudit(datasetId: string, force = false): Promise<Audit> {
  const res = await apiClient.post<StandardResponse<Audit>>("/api/v1/audits", {
    dataset_id: datasetId,
    force,
  });
  return res.data.data;
}

export async function getAudit(auditId: string): Promise<Audit> {
  const res = await apiClient.get<StandardResponse<Audit>>(`/api/v1/audits/${auditId}`);
  return res.data.data;
}

export async function retryAudit(auditId: string): Promise<Audit> {
  const res = await apiClient.post<StandardResponse<Audit>>(`/api/v1/audits/${auditId}/retry`);
  return res.data.data;
}
