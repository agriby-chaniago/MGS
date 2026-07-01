import { apiClient } from "./client";
import type { Dataset, StandardResponse, UploadResponse } from "./types";

export async function listDatasets(): Promise<Dataset[]> {
  const res = await apiClient.get<StandardResponse<Dataset[]>>("/api/v1/datasets");
  return res.data.data;
}

export async function uploadDataset(file: File, name: string): Promise<UploadResponse> {
  const form = new FormData();
  form.append("file", file);
  form.append("name", name);
  const res = await apiClient.post<StandardResponse<UploadResponse>>(
    "/api/v1/datasets/upload",
    form,
    { headers: { "Content-Type": "multipart/form-data" } }
  );
  return res.data.data;
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await apiClient.delete(`/api/v1/datasets/${datasetId}`);
}
