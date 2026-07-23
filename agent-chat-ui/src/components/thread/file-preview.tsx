"use client";

import {
  createContext,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { FileText, LoaderCircle } from "lucide-react";

import { extractPreviewPaths, normalizePreviewPathInput } from "@/lib/file-paths";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { cn } from "@/lib/utils";

interface PreviewResponse {
  path: string;
  mediaType: string;
  content: string;
}

export interface PreviewRequest {
  path: string;
  line?: number;
  lineEnd?: number;
}

const FilePreviewContext = createContext<{
  openPath: (path: string, options?: { line?: number; lineEnd?: number }) => void;
} | null>(null);

function PreviewBody({
  content,
  line,
  lineEnd,
}: {
  content: string;
  line?: number;
  lineEnd?: number;
}) {
  const targetRef = useRef<HTMLSpanElement | null>(null);
  const lines = content.split("\n");
  const start = line && line > 0 ? line : undefined;
  const end =
    start && lineEnd && lineEnd >= start ? lineEnd : start ? start : undefined;

  useEffect(() => {
    if (!targetRef.current) return;
    targetRef.current.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [content, start, end]);

  return (
    <pre className="bg-muted/50 overflow-x-auto rounded-lg border p-2 font-mono text-sm leading-6">
      {lines.map((text, index) => {
        const n = index + 1;
        const highlighted =
          start !== undefined && end !== undefined && n >= start && n <= end;
        return (
          <span
            key={n}
            ref={n === start ? targetRef : undefined}
            className={cn(
              "flex gap-3 px-2",
              highlighted && "bg-amber-200/70 dark:bg-amber-500/30",
            )}
          >
            <span className="text-muted-foreground w-10 shrink-0 select-none text-right">
              {n}
            </span>
            <span className="min-w-0 flex-1 whitespace-pre-wrap break-words">
              {text || " "}
            </span>
          </span>
        );
      })}
    </pre>
  );
}

export function FilePreviewProvider({ children }: { children: ReactNode }) {
  const [request, setRequest] = useState<PreviewRequest | null>(null);
  const [preview, setPreview] = useState<PreviewResponse | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!request) return;

    const controller = new AbortController();
    setLoading(true);
    setError("");
    setPreview(null);
    const path = normalizePreviewPathInput(request.path);
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
  }, [request]);

  const value = useMemo(
    () => ({
      openPath: (path: string, options?: { line?: number; lineEnd?: number }) => {
        setRequest({
          path: normalizePreviewPathInput(path),
          line: options?.line,
          lineEnd: options?.lineEnd,
        });
      },
    }),
    [],
  );

  return (
    <FilePreviewContext.Provider value={value}>
      {children}
      <Sheet
        open={request !== null}
        onOpenChange={(open) => !open && setRequest(null)}
      >
        <SheetContent className="w-[min(92vw,48rem)] gap-0 sm:max-w-none">
          <SheetHeader className="border-b pr-12">
            <SheetTitle className="flex items-center gap-2">
              <FileText className="size-4" />
              File preview
              {request?.line ? (
                <span className="text-muted-foreground font-mono text-xs font-normal">
                  L{request.line}
                  {request.lineEnd && request.lineEnd !== request.line
                    ? `–L${request.lineEnd}`
                    : ""}
                </span>
              ) : null}
            </SheetTitle>
            <SheetDescription className="truncate">
              {request?.path}
            </SheetDescription>
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
              <PreviewBody
                content={preview.content}
                line={request?.line}
                lineEnd={request?.lineEnd}
              />
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
  const normalized = normalizePreviewPathInput(path);
  return (
    <button
      type="button"
      onClick={() => openPath(normalized)}
      className="border-border bg-muted/60 hover:bg-muted focus-visible:ring-ring inline-flex max-w-full cursor-pointer items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-xs break-all transition-colors focus-visible:ring-2 focus-visible:outline-none"
      title={`Preview ${normalized}`}
    >
      <FileText className="size-3.5 shrink-0" />
      {normalized}
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
