import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { ScanSearch, TrendingUp, Activity, AlertTriangle, ArrowRight } from "lucide-react";

import { useAuth, getHistory, type HistoryEntry } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/SeverityBadge";

export const Route = createFileRoute("/_authenticated/dashboard")({
  head: () => ({
    meta: [
      { title: "Dashboard — CrackScan" },
      { name: "description", content: "Your CrackScan dashboard with recent surface defect analyses and stats." },
      { property: "og:title", content: "Dashboard — CrackScan" },
      { property: "og:description", content: "Your CrackScan dashboard with recent surface defect analyses and stats." },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const { user } = useAuth();
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    if (user) setHistory(getHistory(user.id));
  }, [user]);

  const total = history.length;
  const avgSev = total
    ? history.reduce((s, h) => s + h.severity_score, 0) / total
    : 0;
  const highCount = history.filter((h) => h.severity_label === "High").length;
  const last = history[0];

  return (
    <div className="space-y-8">
      <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">
            Welcome back, <span className="text-gradient-primary">{user?.full_name.split(" ")[0]}</span>
          </h1>
          <p className="text-muted-foreground mt-1">Here's an overview of your surface defect analyses.</p>
        </div>
        <Button asChild className="bg-gradient-primary text-white border-0 hover:opacity-90">
          <Link to="/predict">
            <ScanSearch className="h-4 w-4 mr-2" /> New Analysis
          </Link>
        </Button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <StatCard icon={<Activity className="h-5 w-5" />} label="Total Predictions" value={String(total)} />
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Avg Severity"
          value={total ? `${(avgSev * 100).toFixed(0)}%` : "—"}
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5" />}
          label="High Severity"
          value={String(highCount)}
        />
      </div>

      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold">Recent activity</h2>
          {last && (
            <Link to="/profile" className="text-sm text-primary hover:underline inline-flex items-center gap-1">
              View all <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          )}
        </div>
        {history.length === 0 ? (
          <div className="text-center py-12 text-muted-foreground">
            <p className="mb-4">No analyses yet.</p>
            <Button asChild variant="outline">
              <Link to="/predict">Run your first analysis</Link>
            </Button>
          </div>
        ) : (
          <ul className="divide-y divide-border">
            {history.slice(0, 5).map((h) => (
              <li key={h.id} className="py-3 flex items-center justify-between gap-4">
                <div className="min-w-0">
                  <p className="font-medium truncate">{h.predicted_class}</p>
                  <p className="text-xs text-muted-foreground">
                    {new Date(h.createdAt).toLocaleString()} · {(h.confidence * 100).toFixed(0)}% confidence
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-sm text-muted-foreground hidden sm:inline">
                    {h.repair_cost_display}
                  </span>
                  <SeverityBadge label={h.severity_label} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function StatCard({ icon, label, value }: { icon: React.ReactNode; label: string; value: string }) {
  return (
    <Card className="p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <div className="h-9 w-9 rounded-lg bg-primary/10 text-primary flex items-center justify-center">
          {icon}
        </div>
      </div>
      <p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p>
    </Card>
  );
}