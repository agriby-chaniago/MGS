import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode } from "react";

export function Input(props: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      {...props}
      className={`w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2.5 text-sm text-slate-100
        placeholder-slate-500 outline-none transition focus:border-violet-500 focus:ring-2 focus:ring-violet-500/30
        disabled:cursor-not-allowed disabled:opacity-50 ${props.className ?? ""}`}
    />
  );
}

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
}

const variantClasses: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-violet-600 hover:bg-violet-500 text-white shadow-sm shadow-violet-950/50",
  secondary:
    "bg-slate-800 hover:bg-slate-700 text-slate-100 border border-slate-700",
  danger: "bg-rose-600/90 hover:bg-rose-500 text-white",
  ghost: "bg-transparent hover:bg-slate-800 text-slate-300",
};

export function Button({ variant = "primary", className, ...props }: ButtonProps) {
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 text-sm font-medium
        transition disabled:cursor-not-allowed disabled:opacity-40 ${variantClasses[variant]} ${className ?? ""}`}
    />
  );
}

export function Card({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div
      className={`rounded-2xl border border-slate-800 bg-slate-900/60 backdrop-blur-sm shadow-xl shadow-black/20 ${className ?? ""}`}
    >
      {children}
    </div>
  );
}

const planColors: Record<string, string> = {
  free: "bg-slate-700 text-slate-200",
  pro: "bg-blue-600/20 text-blue-300 border border-blue-500/30",
  max: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
};

export function PlanBadge({ plan }: { plan: string | null }) {
  const key = (plan ?? "?").toLowerCase();
  return (
    <span
      className={`inline-flex w-fit items-center rounded-full px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${
        planColors[key] ?? "bg-slate-700 text-slate-200"
      }`}
    >
      {plan ?? "?"}
    </span>
  );
}

const statusColors: Record<string, string> = {
  completed: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
  failed: "bg-rose-500/20 text-rose-300 border border-rose-500/30",
  processing: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
  queued: "bg-sky-500/20 text-sky-300 border border-sky-500/30",
  waiting: "bg-slate-700 text-slate-400",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium capitalize ${
        statusColors[status] ?? "bg-slate-700 text-slate-300"
      }`}
    >
      {status}
    </span>
  );
}

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Konfirmasi",
  danger,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={onCancel}
    >
      <Card className="w-full max-w-sm p-6" >
        <div onClick={(e) => e.stopPropagation()}>
          <h3 className="mb-2 text-lg font-semibold text-white">{title}</h3>
          <p className="mb-6 text-sm text-slate-400">{message}</p>
          <div className="flex justify-end gap-3">
            <Button variant="ghost" onClick={onCancel}>
              Batal
            </Button>
            <Button variant={danger ? "danger" : "primary"} onClick={onConfirm}>
              {confirmLabel}
            </Button>
          </div>
        </div>
      </Card>
    </div>
  );
}

export function BackLink({ onClick, label }: { onClick: () => void; label: string }) {
  return (
    <button
      onClick={onClick}
      className="mb-4 flex items-center gap-1 text-sm text-slate-400 transition hover:text-slate-200"
    >
      ← {label}
    </button>
  );
}

export function Logo() {
  return (
    <div className="flex items-center gap-2">
      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-violet-500 to-fuchsia-600 text-sm font-bold text-white">
        M
      </div>
      <span className="text-lg font-semibold tracking-tight text-white">ModelGate</span>
    </div>
  );
}
