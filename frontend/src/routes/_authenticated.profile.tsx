import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { LogOut, Mail, Shield } from "lucide-react";

import { useAuth, getHistory, type HistoryEntry } from "@/lib/auth";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { SeverityBadge } from "@/components/SeverityBadge";

export const Route = createFileRoute("/_authenticated/profile")({
  head: () => ({
    meta: [
      { title: "Profile — CrackScan" },
      { name: "description", content: "Your CrackScan profile and prediction history." },
      { property: "og:title", content: "Profile — CrackScan" },
      { property: "og:description", content: "Your CrackScan profile and prediction history." },
    ],
  }),
  component: ProfilePage,
});

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  const a = parts[0]?.[0] ?? "";
  const b = parts[1]?.[0] ?? parts[0]?.[1] ?? "";
  return (a + b).toUpperCase() || "U";
}

function ProfilePage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  useEffect(() => {
    if (user) setHistory(getHistory(user.id));
  }, [user]);

  const handleSignOut = () => {
    signOut();
    navigate({ to: "/login", replace: true });
  };

  return (
    <div className="space-y-8">
      <Card className="p-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-6">
          <div className="h-20 w-20 rounded-full bg-gradient-primary flex items-center justify-center text-2xl font-semibold text-white shadow-lg shadow-primary/30">
            {initials(user?.full_name ?? "U")}
          </div>
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-semibold">{user?.full_name}</h1>
            <p className="text-muted-foreground inline-flex items-center gap-2 mt-1">
              <Mail className="h-4 w-4" /> {user?.email}
            </p>
            <div className="mt-3 flex flex-wrap gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-3 py-1 text-xs">
                <Shield className="h-3.5 w-3.5" /> Standard account
              </span>
              <span className="inline-flex items-center rounded-full border border-border bg-muted/40 px-3 py-1 text-xs">
                {history.length} predictions
              </span>
            </div>
          </div>
          <Button variant="outline" onClick={handleSignOut}>
            <LogOut className="h-4 w-4 mr-2" /> Sign out
          </Button>
        </div>
      </Card>

      <Card className="p-6">
        <h2 className="text-lg font-semibold mb-4">Prediction history</h2>
        {history.length === 0 ? (
          <p className="text-sm text-muted-foreground py-8 text-center">
            You haven't run any analyses yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="text-xs text-muted-foreground border-b border-border">
                <tr className="text-left">
                  <th className="py-2 pr-4 font-medium">Date</th>
                  <th className="py-2 pr-4 font-medium">Defect</th>
                  <th className="py-2 pr-4 font-medium">Confidence</th>
                  <th className="py-2 pr-4 font-medium">Severity</th>
                  <th className="py-2 pr-4 font-medium">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {history.map((h) => (
                  <tr key={h.id}>
                    <td className="py-3 pr-4 text-muted-foreground">
                      {new Date(h.createdAt).toLocaleString()}
                    </td>
                    <td className="py-3 pr-4 font-medium">{h.predicted_class}</td>
                    <td className="py-3 pr-4">{(h.confidence * 100).toFixed(0)}%</td>
                    <td className="py-3 pr-4">
                      <SeverityBadge label={h.severity_label} />
                    </td>
                    <td className="py-3 pr-4 text-muted-foreground">{h.repair_cost_display}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}