import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { Loader2, Sparkles, Clock, DollarSign, IndianRupee, RotateCcw } from "lucide-react";

import { UploadDropzone } from "@/components/UploadDropzone";
import { SeverityBadge } from "@/components/SeverityBadge";
import { Card } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { api, ApiError, type PredictionResult, type DefectClass } from "@/lib/api";
import { addHistory, useAuth } from "@/lib/auth";
import { ModelSelector } from "@/components/ModelSelector";

export const Route = createFileRoute("/_authenticated/predict")({
  head: () => ({
    meta: [
      { title: "Analyze Defect — CrackScan" },
      {
        name: "description",
        content:
          "Upload a road or pavement image to detect cracks, patches, potholes, and surface defects.",
      },
      { property: "og:title", content: "Analyze Defect — CrackScan" },
      {
        property: "og:description",
        content:
          "Upload a road or pavement image to detect cracks, patches, potholes, and surface defects.",
      },
    ],
  }),
  component: PredictPage,
});

const classes: DefectClass[] = ["Cracks", "Patch", "Potholes", "Surface Defects"];

function PredictPage() {
  const { user, token } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [currency, setCurrency] = useState<"USD" | "INR">("USD");

  const analyze = async () => {
    if (!file || !token) return;
    setLoading(true);
    try {
      const res = await api.predict(file, token, currency);
      setResult(res);
      if (user) {
        addHistory(user.id, {
          id: crypto.randomUUID(),
          createdAt: Date.now(),
          predicted_class: res.predicted_class,
          confidence: res.confidence,
          severity_label: res.severity_label,
          severity_score: res.severity_score,
          repair_cost_display: res.repair_cost.display,
          repair_time_display: res.repair_time.display,
        });
      }
      toast.success("Analysis complete");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Analysis failed");
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setFile(null);
    setResult(null);
  };

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">Analyze Defect</h1>
        <p className="text-muted-foreground mt-1">
          Upload a photo of pavement or road surface to classify the defect and estimate repair
          cost.
        </p>
      </div>

      <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-2">
        <span className="text-xs text-muted-foreground">Model</span>
        <ModelSelector />
      </div>

      <div className="flex items-center justify-between rounded-lg border border-border bg-muted/30 px-4 py-2">
        <span className="text-xs text-muted-foreground">Currency</span>
        <select
          value={currency}
          onChange={(e) => setCurrency(e.target.value as "USD" | "INR")}
          disabled={loading}
          className="text-xs bg-transparent border border-border rounded-md px-2 py-1 focus:outline-none"
        >
          <option value="USD">USD ($)</option>
          <option value="INR">INR (₹)</option>
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">1. Upload image</h2>
          <UploadDropzone file={file} onFile={setFile} disabled={loading} />
          <div className="mt-4 flex gap-2">
            <Button
              onClick={analyze}
              disabled={!file || loading}
              className="flex-1 bg-gradient-primary hover:opacity-90 text-white border-0"
            >
              {loading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Analyzing…
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4 mr-2" /> Analyze Defect
                </>
              )}
            </Button>
            {(file || result) && (
              <Button variant="outline" onClick={reset} disabled={loading}>
                <RotateCcw className="h-4 w-4 mr-2" /> Reset
              </Button>
            )}
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold mb-4">2. Results</h2>
          {!result ? (
            <div className="flex flex-col items-center justify-center py-16 text-center text-muted-foreground">
              <div className="h-14 w-14 rounded-full bg-muted flex items-center justify-center mb-3">
                <Sparkles className="h-6 w-6" />
              </div>
              <p className="text-sm">
                Run an analysis to see the defect classification, severity, and repair estimates
                here.
              </p>
            </div>
          ) : (
            <div className="space-y-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-primary/15 text-primary border border-primary/30 px-3 py-1 text-xs font-medium">
                  {result.predicted_class}
                </span>
                <SeverityBadge label={result.severity_label} />
              </div>

              {result.pdf_path && (
                <div className="mt-4">
                  <a
                    href={`http://localhost:8501/api/report?path=${encodeURIComponent(result.pdf_path)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center rounded-lg bg-blue-600 px-4 py-2 text-white hover:bg-blue-700 transition"
                  >
                    📄 Download Inspection Report
                  </a>
                </div>
              )}

              <div>
                <div className="flex justify-between text-sm mb-1.5">
                  <span className="text-muted-foreground">Confidence</span>
                  <span className="font-medium">{(result.confidence * 100).toFixed(1)}%</span>
                </div>
                <Progress value={result.confidence * 100} />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <MetricTile
                  icon={result.repair_cost.currency === "INR" ? <IndianRupee className="h-4 w-4" /> : <DollarSign className="h-4 w-4" />}
                  label="Repair cost"
                  value={result.repair_cost.display}
                />
                <MetricTile
                  icon={<Clock className="h-4 w-4" />}
                  label="Repair time"
                  value={result.repair_time.display}
                />
              </div>

              <div>
                <h3 className="text-sm font-medium mb-2">Class probabilities</h3>
                <div className="space-y-2">
                  {classes.map((c) => {
                    const p = result.class_probabilities[c] ?? 0;
                    return (
                      <div key={c}>
                        <div className="flex justify-between text-xs mb-1">
                          <span
                            className={
                              c === result.predicted_class ? "font-medium" : "text-muted-foreground"
                            }
                          >
                            {c}
                          </span>
                          <span className="text-muted-foreground">{(p * 100).toFixed(1)}%</span>
                        </div>
                        <Progress value={p * 100} />
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}

function MetricTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-lg border border-border bg-muted/30 p-3">
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        {icon}
        {label}
      </div>
      <p className="mt-1 font-semibold">{value}</p>
    </div>
  );
}
