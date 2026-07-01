import { apiClient } from "./client";
import type { ReportDetail, ReportSummary, StandardResponse } from "./types";

export async function getReport(auditId: string): Promise<ReportDetail> {
  const res = await apiClient.get<StandardResponse<ReportDetail>>(`/api/v1/reports/${auditId}`);
  return res.data.data;
}

export async function getSummary(auditId: string): Promise<ReportSummary> {
  const res = await apiClient.get<StandardResponse<ReportSummary>>(`/api/v1/reports/${auditId}/summary`);
  return res.data.data;
}

export async function downloadPdf(auditId: string): Promise<Blob> {
  const res = await apiClient.get(`/api/v1/reports/${auditId}/pdf`, { responseType: "blob" });
  return res.data;
}
