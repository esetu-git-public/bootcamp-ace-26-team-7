import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Loader2, CheckCircle2 } from "lucide-react";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";

export const Route = createFileRoute("/forgot")({
  head: () => ({
    meta: [
      { title: "Reset password — CrackScan" },
      { name: "description", content: "Send yourself a reset link to recover your CrackScan account." },
      { property: "og:title", content: "Reset password — CrackScan" },
      { property: "og:description", content: "Send yourself a reset link to recover your CrackScan account." },
    ],
  }),
  component: ForgotPage,
});

const schema = z.object({ email: z.string().trim().email("Enter a valid email") });

function ForgotPage() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const [sent, setSent] = useState(false);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = schema.safeParse({ email });
    if (!parsed.success) {
      setError(parsed.error.issues[0]?.message);
      return;
    }
    setError(undefined);
    setSubmitting(true);
    try {
      await api.forgotPassword(parsed.data.email);
      setSent(true);
      toast.success("Reset link sent. Check your email.");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Request failed");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthCard
      title="Forgot password?"
      subtitle="We'll send a reset link to your email"
      footer={
        <Link to="/login" className="text-primary hover:underline">Back to sign in</Link>
      }
    >
      {sent ? (
        <div className="rounded-lg border border-border bg-muted/40 p-4 text-sm flex items-start gap-3">
          <CheckCircle2 className="h-5 w-5 text-[color:var(--success)] shrink-0 mt-0.5" />
          <div>
            <p className="font-medium">Check your inbox</p>
            <p className="text-muted-foreground mt-1">
              If an account exists for {email}, a reset link is on its way.
            </p>
          </div>
        </div>
      ) : (
        <form onSubmit={onSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="email">Email</Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
            />
            {error && <p className="text-xs text-destructive">{error}</p>}
          </div>
          <Button type="submit" disabled={submitting} className="w-full bg-gradient-primary hover:opacity-90 text-white border-0">
            {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Send Reset Link"}
          </Button>
        </form>
      )}
    </AuthCard>
  );
}