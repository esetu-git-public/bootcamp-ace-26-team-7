import { useEffect, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { Shield, LogOut, LayoutDashboard, ScanSearch, User } from "lucide-react";
import { useAuth } from "@/lib/auth";
import { api } from "@/lib/api";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

function initials(name: string) {
  const parts = name.trim().split(/\s+/);
  const a = parts[0]?.[0] ?? "";
  const b = parts[1]?.[0] ?? parts[0]?.[1] ?? "";
  return (a + b).toUpperCase() || "U";
}

const STATUS_COLORS: Record<string, string> = {
  loaded: "bg-green-500",
  loading: "bg-yellow-500 animate-pulse",
  unavailable: "bg-gray-500",
  error: "bg-red-500",
};

export function TopNav() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  const [modelStatus, setModelStatus] = useState<string>("unavailable");
  const [activeModel, setActiveModel] = useState<string>("");

  useEffect(() => {
    api
      .modelStatus()
      .then((r) => {
        setModelStatus(r.status);
        setActiveModel(r.active_model);
      })
      .catch(() => setModelStatus("unavailable"));
  }, []);

  const handleSignOut = () => {
    signOut();
    navigate({ to: "/login", replace: true });
  };

  return (
    <header className="sticky top-0 z-30 border-b border-border bg-card/80 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
        <Link to="/dashboard" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-gradient-primary flex items-center justify-center">
            <Shield className="h-4 w-4 text-white" strokeWidth={2.5} />
          </div>
          <div className="flex flex-col leading-tight">
            <span className="font-semibold tracking-tight">CrackScan</span>
            <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
              <span
                className={`h-1.5 w-1.5 rounded-full ${STATUS_COLORS[modelStatus] ?? "bg-gray-500"}`}
              />
              {modelStatus}
              {activeModel && <span className="ml-1 font-medium">{activeModel}</span>}
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-1">
          <NavItem to="/dashboard" icon={<LayoutDashboard className="h-4 w-4" />}>
            Dashboard
          </NavItem>
          <NavItem to="/predict" icon={<ScanSearch className="h-4 w-4" />}>
            Predict
          </NavItem>
          <NavItem to="/profile" icon={<User className="h-4 w-4" />}>
            Profile
          </NavItem>
        </nav>

        <DropdownMenu>
          <DropdownMenuTrigger className="flex items-center gap-2 rounded-full outline-none focus:ring-2 focus:ring-ring">
            <div className="h-9 w-9 rounded-full bg-gradient-primary flex items-center justify-center text-xs font-semibold text-white">
              {initials(user?.full_name ?? "U")}
            </div>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="font-normal">
              <div className="flex flex-col">
                <span className="text-sm font-medium truncate">{user?.full_name}</span>
                <span className="text-xs text-muted-foreground truncate">{user?.username}</span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem asChild>
              <Link to="/profile">
                <User className="mr-2 h-4 w-4" /> Profile
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem
              onClick={handleSignOut}
              className="text-destructive focus:text-destructive"
            >
              <LogOut className="mr-2 h-4 w-4" /> Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
}

function NavItem({
  to,
  icon,
  children,
}: {
  to: "/dashboard" | "/predict" | "/profile";
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Link
      to={to}
      className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
      activeProps={{ className: "bg-muted text-foreground" }}
    >
      {icon}
      {children}
    </Link>
  );
}
