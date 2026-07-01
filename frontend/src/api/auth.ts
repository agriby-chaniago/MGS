import { apiClient } from "./client";
import type { ApiKeyCreatedResponse, StandardResponse, TokenResponse, User } from "./types";

export async function register(email: string, password: string): Promise<TokenResponse> {
  const res = await apiClient.post<StandardResponse<TokenResponse>>("/api/v1/auth/register", {
    email,
    password,
  });
  return res.data.data;
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const res = await apiClient.post<StandardResponse<TokenResponse>>("/api/v1/auth/login", {
    email,
    password,
  });
  return res.data.data;
}

export async function me(): Promise<User> {
  const res = await apiClient.get<StandardResponse<User>>("/api/v1/auth/me");
  return res.data.data;
}

export async function upgrade(plan: "pro" | "max"): Promise<TokenResponse> {
  const res = await apiClient.post<StandardResponse<TokenResponse>>("/api/v1/auth/upgrade", { plan });
  return res.data.data;
}

export async function createApiKey(): Promise<ApiKeyCreatedResponse> {
  const res = await apiClient.post<StandardResponse<ApiKeyCreatedResponse>>("/api/v1/auth/api-keys");
  return res.data.data;
}
