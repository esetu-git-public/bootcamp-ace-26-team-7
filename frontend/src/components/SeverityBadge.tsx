import { cn } from "@/lib/utils";
import type { SeverityLabel } from "@/lib/api";

export function SeverityBadge({ label }: { label: SeverityLabel }) {
  const styles: Record<SeverityLabel, string> = {
    Low: "bg-[color:var(--success)]/15 text-[color:var(--success)] border-[color:var(--success)]/30",
    Medium:
      "bg-[color:var(--warning)]/15 text-[color:var(--warning)] border-[color:var(--warning)]/30",
    High: "bg-destructive/15 text-destructive border-destructive/30",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium",
        styles[label],
      )}
    >
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          label === "Low" && "bg-[color:var(--success)]",
          label === "Medium" && "bg-[color:var(--warning)]",
          label === "High" && "bg-destructive",
        )}
      />
      {label} severity
    </span>
  );
}
