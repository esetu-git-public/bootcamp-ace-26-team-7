import { useCallback, useRef, useState } from "react";
import { Upload, X, ImageIcon } from "lucide-react";
import { cn } from "@/lib/utils";

export function UploadDropzone({
  file,
  onFile,
  disabled,
}: {
  file: File | null;
  onFile: (f: File | null) => void;
  disabled?: boolean;
}) {
  const [dragging, setDragging] = useState(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback(
    (f: File | null) => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      if (f) {
        setPreviewUrl(URL.createObjectURL(f));
      } else {
        setPreviewUrl(null);
      }
      onFile(f);
    },
    [onFile, previewUrl],
  );

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragging(false);
    if (disabled) return;
    const f = e.dataTransfer.files?.[0];
    if (f && /^image\/(jpeg|png)$/.test(f.type)) handleFile(f);
  };

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        if (!disabled) setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={onDrop}
      className={cn(
        "relative rounded-xl border-2 border-dashed border-border bg-muted/30 transition-colors",
        dragging && "border-primary bg-primary/5",
        disabled && "opacity-60 pointer-events-none",
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/jpeg,image/png"
        className="hidden"
        onChange={(e) => handleFile(e.target.files?.[0] ?? null)}
      />
      {file && previewUrl ? (
        <div className="p-4">
          <div className="relative rounded-lg overflow-hidden bg-background">
            <img src={previewUrl} alt="Preview" className="w-full max-h-[380px] object-contain" />
            <button
              type="button"
              onClick={() => handleFile(null)}
              className="absolute top-2 right-2 rounded-full bg-background/80 p-1.5 border border-border hover:bg-background"
              aria-label="Remove image"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-3 flex items-center gap-2 text-sm text-muted-foreground">
            <ImageIcon className="h-4 w-4" />
            <span className="truncate">{file.name}</span>
            <span className="ml-auto">{(file.size / 1024).toFixed(0)} KB</span>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="w-full flex flex-col items-center justify-center gap-3 py-16 px-6 text-center"
        >
          <div className="h-14 w-14 rounded-full bg-primary/10 flex items-center justify-center">
            <Upload className="h-6 w-6 text-primary" />
          </div>
          <div>
            <p className="font-medium">Drop an image here, or click to browse</p>
            <p className="text-xs text-muted-foreground mt-1">JPEG or PNG · up to 10 MB</p>
          </div>
        </button>
      )}
    </div>
  );
}
