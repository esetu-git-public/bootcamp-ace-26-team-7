import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { z } from "zod";
import { Github, Loader2 } from "lucide-react";

import { AuthCard } from "@/components/AuthCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, ApiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export const Route = createFileRoute("/login")({
  head: () => ({
    meta: [
      { title: "Sign in — CrackScan" },
      {
        name: "description",
        content: "Sign in to your CrackScan account to analyze surface defects.",
      },
      { property: "og:title", content: "Sign in — CrackScan" },
      {
        property: "og:description",
        content: "Sign in to your CrackScan account to analyze surface defects.",
      },
    ],
  }),
  component: LoginPage,
});

const schema = z.object({
  username: z.string().trim().min(1, "Username is required"),
  password: z.string().min(1, "Password is required"),
});

function LoginPage() {
  const { signIn, isAuthenticated, isReady } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<{ username?: string; password?: string }>({});
  const [submitting, setSubmitting] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);

  useEffect(() => {
    if (isReady && isAuthenticated) navigate({ to: "/dashboard", replace: true });
  }, [isReady, isAuthenticated, navigate]);

  const onSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const parsed = schema.safeParse({ username, password });
    if (!parsed.success) {
      const errs: typeof errors = {};
      for (const issue of parsed.error.issues) {
        errs[issue.path[0] as "username" | "password"] = issue.message;
      }
      setErrors(errs);
      return;
    }
    setErrors({});
    setSubmitting(true);
    try {
      const res = await api.login(parsed.data.username, parsed.data.password);
      if (!res.success) throw new ApiError(0, res.message ?? "Invalid credentials");
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
          <Link to="/register" className="text-primary hover:underline">
            Create account
          </Link>
        </span>
      }
    >
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="space-y-2">
          <Label htmlFor="username">Username</Label>
          <Input
            id="username"
            type="text"
            autoComplete="username"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            placeholder="your_username"
          />
          {errors.username && <p className="text-xs text-destructive">{errors.username}</p>}
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
