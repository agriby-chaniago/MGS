import axios from "axios";

// Baked in at Docker build time via Vite's build-arg mechanism (NOT a
// docker-compose `environment:` var — Vite inlines import.meta.env.VITE_*
// at `npm run build`, not at container start). See frontend/Dockerfile.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8080";

export const apiClient = axios.create({ baseURL: API_BASE_URL });

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("mgs_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("mgs_token");
      localStorage.removeItem("mgs_plan");
      if (window.location.pathname !== "/login") {
        window.location.href = "/login";
      }
    }
    return Promise.reject(error);
  }
);

export function wsBaseUrl(): string {
  return API_BASE_URL.replace(/^http/, "ws");
}
