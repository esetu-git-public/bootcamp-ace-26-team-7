import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Github, Loader2 } from "lucide-react";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Checkbox } from "@/components/ui/checkbox";
import { api, ApiError } from "@/lib/api";
import { getRememberedEmail, setRememberedEmail, useAuth } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — CrackScan" },
      { name: "description", content: "Sign in to your CrackScan account to analyze surface defects." },
      { property: "og:title", content: "Sign in — CrackScan" },
      { property: "og:description", content: "Sign in to your CrackScan account to analyze surface defects." },
    ],
  }),
  component: LoginPage,
});

const schema = z.object({
  email: z.string().trim().email("Enter a valid email"),
  password: z.string().min(1, "Password is required"),
});

function LoginPage() {
  const { signIn, isAuthenticated, isReady } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [remember, setRemember] = useState(false);
  const [errors, setErrors] = useState<{ email?: string; password?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);

  useEffect(() => {
    const saved = getRememberedEmail();
    if (saved) {
      setEmail(saved);
      setRemember(true);
    }
  }, []);

  useEffect(() => {
    if (isReady && isAuthenticated) navigate({ to: "/dashboard", replace: true });
  }, [isReady, isAuthenticated, navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = schema.safeParse({ email, password });
    if (!parsed.success) {
      const errs: typeof errors = {};
      for (const issue of parsed.error.issues) {
        errs[issue.path[0] as "email" | "password"] = issue.message;
      }
      setErrors(errs);
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      const res = await api.login(parsed.data.email, parsed.data.password);
      setRememberedEmail(remember ? parsed.data.email : "");
      signIn(res.access_token, res.user);
      toast.success(`Welcome back, ${res.user.full_name}`);
      navigate({ to: "/dashboard", replace: true });
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Sign in failed");
    } finally {
      setSubmitting(false);
    }
  };

  const onGithub = async () => {
    setGithubLoading(true);
    try {
      const redirect =
        import.meta.env.VITE_GITHUB_OAUTH_REDIRECT ||
        `${window.location.origin}/auth/github/callback`;
      const { url } = await api.githubStart(redirect);
      window.location.href = url;
    } catch (err) {
      setGithubLoading(false);
      toast.error(err instanceof ApiError ? err.message : "GitHub sign in failed");
    }
  };

  return (
    <AuthCard
      title="Welcome back"
      subtitle="Sign in to your CrackScan account"
      footer={
        <span>
          <Link to="/forgot" className="text-primary hover:underline">Forgot password?</Link>
          <span className="mx-2">·</span>
          <Link to="/register" className="text-primary hover:underline">Create account</Link>
        </span>
      }
    >
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
          {errors.email && <p className="text-xs text-destructive">{errors.email}</p>}
        </div>
        <div className="space-y-2">
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          {errors.password && <p className="text-xs text-destructive">{errors.password}</p>}
        </div>
        <label className="flex items-center gap-2 text-sm text-muted-foreground select-none cursor-pointer">
          <Checkbox checked={remember} onCheckedChange={(v) => setRemember(!!v)} />
          Remember me
        </label>
        <Button
          type="submit"
          disabled={submitting}
          className="w-full bg-gradient-primary hover:opacity-90 text-white border-0"
        >
          {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : "Sign In"}
        </Button>

        <div className="relative py-2">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-card px-2 text-muted-foreground">or continue with</span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          onClick={onGithub}
          disabled={githubLoading}
          className="w-full"
        >
          {githubLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" />
          ) : (
            <>
              <Github className="h-4 w-4 mr-2" /> GitHub
            </>
          )}
        </Button>
      </form>
    </AuthCard>
  );
}