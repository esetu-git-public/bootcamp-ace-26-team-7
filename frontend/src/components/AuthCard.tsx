import type { ReactNode } from "react";
import { Shield } from "lucide-react";

export function AuthCard({
  title,
  subtitle,
  children,
  footer,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  footer?: ReactNode;
}) {
  return (
    <div className="min-h-screen w-full flex items-center justify-center px-4 py-12 relative overflow-hidden">
      <div
        className="pointer-events-none absolute inset-0 opacity-40"
        style={{
          background:
            "radial-gradient(600px circle at 20% 20%, rgba(99,102,241,0.15), transparent 60%), radial-gradient(600px circle at 80% 80%, rgba(139,92,246,0.12), transparent 60%)",
        }}
      />
      <div className="relative w-full max-w-md rounded-2xl border border-border bg-card p-8 shadow-2xl">
        <div className="flex flex-col items-center gap-3 mb-6">
          <div className="h-12 w-12 rounded-xl bg-gradient-primary flex items-center justify-center shadow-lg shadow-primary/30">
            <Shield className="h-6 w-6 text-white" strokeWidth={2.4} />
          </div>
          <h1 className="text-2xl font-semibold text-foreground">{title}</h1>
          {subtitle && <p className="text-sm text-muted-foreground text-center">{subtitle}</p>}
        </div>
        {children}
        {footer && <div className="mt-6 text-center text-sm text-muted-foreground">{footer}</div>}
      </div>
    </div>
  );
}
