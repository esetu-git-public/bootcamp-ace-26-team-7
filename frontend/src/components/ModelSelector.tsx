import { useEffect, useState } from "react";
import { Loader2, Cpu } from "lucide-react";
import { api, type ModelInfo } from "@/lib/api";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

const STATUS_DOT: Record<string, string> = {
  loaded: "bg-green-500",
  loading: "bg-yellow-500 animate-pulse",
  unavailable: "bg-gray-500",
  error: "bg-red-500",
};

export function ModelSelector() {
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [activeModel, setActiveModel] = useState<string>("");
  const [switching, setSwitching] = useState(false);

  const fetchModels = () => {
    api
      .getModels()
      .then((r) => {
        setModels(r.models);
        const active = r.models.find((m) => m.is_active);
        if (active) setActiveModel(active.name);
      })
      .catch(() => {});
  };

  useEffect(() => {
    fetchModels();
  }, []);

  useEffect(() => {
    const hasLoading = models.some((m) => m.status === "loading" || (m.is_active && switching));
    if (!hasLoading) return;
    const interval = setInterval(fetchModels, 2000);
    return () => clearInterval(interval);
  }, [models, switching]);

  const handleChange = async (name: string) => {
    setSwitching(true);
    try {
      await api.selectModel(name);
      setActiveModel(name);
    } catch {
      /* selection error — model stays unchanged */
    }
    fetchModels();
    setSwitching(false);
  };

  const current = models.find((m) => m.name === activeModel);

  return (
    <div className="flex items-center gap-2">
      <Cpu className="h-4 w-4 text-muted-foreground shrink-0" />
      <Select value={activeModel || undefined} onValueChange={handleChange} disabled={switching}>
        <SelectTrigger className="w-[200px] h-8 text-xs">
          <SelectValue>
            {switching ? (
              <span className="flex items-center gap-1.5">
                <Loader2 className="h-3 w-3 animate-spin" />
                Downloading&hellip;
              </span>
            ) : current ? (
              <span className="flex items-center gap-1.5">
                <span
                  className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATUS_DOT[current.status] ?? "bg-gray-500"}`}
                />
                {current.display_name}
              </span>
            ) : (
              "Select model"
            )}
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {models.map((m) => (
            <SelectItem key={m.name} value={m.name}>
              <span className="flex items-center gap-2 w-full">
                <span
                  className={`h-1.5 w-1.5 rounded-full shrink-0 ${STATUS_DOT[m.status] ?? "bg-gray-500"}`}
                />
                <span>{m.display_name}</span>
                <span className="text-[10px] text-muted-foreground ml-auto">{m.size_mb}MB</span>
              </span>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
