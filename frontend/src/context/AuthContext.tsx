import { createContext, useContext, useState, type ReactNode } from "react";
import * as authApi from "../api/auth";
import type { Plan } from "../api/types";

interface AuthState {
  token: string | null;
  plan: Plan | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  upgrade: (plan: "pro" | "max") => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

function persist(token: string, plan: Plan) {
  localStorage.setItem("mgs_token", token);
  localStorage.setItem("mgs_plan", plan);
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(localStorage.getItem("mgs_token"));
  const [plan, setPlan] = useState<Plan | null>(localStorage.getItem("mgs_plan") as Plan | null);

  async function login(email: string, password: string) {
    const res = await authApi.login(email, password);
    persist(res.access_token, res.plan);
    setToken(res.access_token);
    setPlan(res.plan);
  }

  async function register(email: string, password: string) {
    const res = await authApi.register(email, password);
    persist(res.access_token, res.plan);
    setToken(res.access_token);
    setPlan(res.plan);
  }

  async function upgrade(newPlan: "pro" | "max") {
    // Re-issues a fresh token carrying the new plan claim — old tokens keep
    // the stale plan until they expire, so callers must swap to this one.
    const res = await authApi.upgrade(newPlan);
    persist(res.access_token, res.plan);
    setToken(res.access_token);
    setPlan(res.plan);
  }

  function logout() {
    localStorage.removeItem("mgs_token");
    localStorage.removeItem("mgs_plan");
    setToken(null);
    setPlan(null);
  }

  return (
    <AuthContext.Provider
      value={{ token, plan, isAuthenticated: !!token, login, register, upgrade, logout }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
