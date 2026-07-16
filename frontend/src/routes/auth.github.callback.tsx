import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Loader2, AlertCircle } from "lucide-react";

import { AuthCard } from "@/components/AuthCard";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { Button } from "@/components/ui/button";

export const Route = createFileRoute("/auth/github/callback")({
  head: () => ({ meta: [{ title: "Signing in… — CrackScan" }] }),
  component: GithubCallback,
});

function GithubCallback() {
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const ran = useRef(false);

  useEffect(() => {
    if (ran.current) return;
    ran.current = true;
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    if (!code) {
      setError("Missing authorization code");
      return;
    }
    (async () => {
      try {
        const res = await api.githubCallback(code);
        signIn(res.access_token, res.user);
        navigate({ to: "/dashboard", replace: true });
      } catch (e) {
        setError(e instanceof ApiError ? e.message : "Sign in failed");
      }
    })();
  }, [signIn, navigate]);

  return (
    <AuthCard title={error ? "Sign in failed" : "Signing you in…"}>
      {error ? (
        <div className="space-y-4">
          <div className="flex items-start gap-3 rounded-lg border border-destructive/30 bg-destructive/10 p-4 text-sm">
            <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
          <Button className="w-full" onClick={() => navigate({ to: "/login", replace: true })}>
            Back to sign in
          </Button>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-3 py-6 text-muted-foreground">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm">Completing GitHub authentication…</p>
        </div>
      )}
    </AuthCard>
  );
}
