"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { FileText, LoaderCircle } from "lucide-react";

import { extractPreviewPaths } from "@/lib/file-paths";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";

interface PreviewResponse {
  path: string;
  mediaType: string;
  content: string;
}

const FilePreviewContext = createContext<{
  openPath: (path: string) => void;
} | null>(null);

export function FilePreviewProvider({ children }: { children: ReactNode }) {
  const [path, setPath] = useState<string | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!path) return;

    const controller = new AbortController();
    setLoading(true);
    setError("");
    setPreview(null);
    fetch(`/api/files/preview?path=${encodeURIComponent(path)}`, {
      signal: controller.signal,
    })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw new Error(body.error || "Preview failed");
        setPreview(body);
      })
      .catch((cause: Error) => {
        if (cause.name !== "AbortError") setError(cause.message);
      })
      .finally(() => setLoading(false));

    return () => controller.abort();
  }, [path]);

  const value = useMemo(() => ({ openPath: setPath }), []);

  return (
    <FilePreviewContext.Provider value={value}>
      {children}
      <Sheet
        open={path !== null}
        onOpenChange={(open) => !open && setPath(null)}
      >
        <SheetContent className="w-[min(92vw,48rem)] gap-0 sm:max-w-none">
          <SheetHeader className="border-b pr-12">
            <SheetTitle className="flex items-center gap-2">
              <FileText className="size-4" />
              File preview
            </SheetTitle>
            <SheetDescription className="truncate">{path}</SheetDescription>
          </SheetHeader>
          <div className="min-h-0 flex-1 overflow-auto p-4">
            {loading && (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <LoaderCircle className="size-4 animate-spin" />
                Loading preview…
              </div>
            )}
            {error && (
              <p className="text-destructive text-sm">
                Could not open this file: {error}
              </p>
            )}
            {preview && (
              <pre className="bg-muted/50 overflow-x-auto rounded-lg border p-4 font-mono text-sm leading-6 whitespace-pre-wrap">
                {preview.content}
              </pre>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </FilePreviewContext.Provider>
  );
}

export function useFilePreview() {
  const context = useContext(FilePreviewContext);
  if (!context) {
    throw new Error("useFilePreview must be used within FilePreviewProvider");
  }
  return context;
}

export function FilePathButton({ path }: { path: string }) {
  const { openPath } = useFilePreview();
  return (
    <button
      type="button"
      onClick={() => openPath(path)}
      className="border-border bg-muted/60 hover:bg-muted focus-visible:ring-ring inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-xs break-all transition-colors focus-visible:ring-2 focus-visible:outline-none"
      title={`Preview ${path}`}
    >
      <FileText className="size-3.5 shrink-0" />
      {path}
    </button>
  );
}

export function FilePathButtons({ value }: { value: unknown }) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  const paths = extractPreviewPaths(text ?? "");
  if (!paths.length) return null;

  return (
    <span className="mt-1 flex flex-wrap gap-1.5">
      {paths.map((path) => (
        <FilePathButton
          key={path}
          path={path}
        />
      ))}
    </span>
  );
}
