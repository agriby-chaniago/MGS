export interface StandardResponse<T> {
  success: boolean;
  data: T;
  error: string | null;
  metadata: {
    service: string;
    version: string;
    timestamp: string;
  };
}

export type Plan = "free" | "pro" | "max";

export interface User {
  id: string;
  email: string;
  plan: Plan;
  created_at: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  plan: Plan;
}

export interface ApiKeyCreatedResponse {
  id: string;
  api_key: string;
  plan: Plan;
}

export interface Dataset {
  id: string;
  name: string;
  status: string;
  class_count: number;
  total_images: number;
  file_size_mb: number;
  created_at: string;
}

export interface UploadResponse {
  dataset_id: string;
  name: string;
  class_count: number;
  total_images: number;
  file_size_mb: number;
  invalid_files: string[];
  cached?: boolean;
}

export interface Audit {
  id: string;
  dataset_id: string;
  status: "pending" | "queued" | "processing" | "completed" | "failed";
  requested_analyzers: string[];
  created_at: string;
  completed_at: string | null;
  error_message: string | null;
  cached?: boolean;
}

export interface AnalysisResult {
  analyzer_type: string;
  status: string;
  result_payload: {
    findings: unknown[];
    summary: Record<string, unknown>;
    metrics: Record<string, unknown>;
  };
  error_message: string | null;
  completed_at: string | null;
}

export interface ReportSummary {
  audit_id: string;
  audit_status: string;
  health_score: number | null;
  grade: string | null;
  components: { I: number; U: number; D: number; Q: number } | null;
}

export interface ReportDetail extends ReportSummary {
  dataset_id: string;
  requested_analyzers: string[];
  analysis_results: AnalysisResult[];
  created_at: string;
  completed_at: string | null;
}
