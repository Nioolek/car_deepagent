"use client";

import { useEffect, useMemo, useState } from "react";
import { FileText, Search, X } from "lucide-react";
import { cn } from "@/lib/utils";

export type InterviewFile = {
  name: string;
  path: string;
};

export function InterviewFilePicker({
  selectedPaths,
  onChange,
}: {
  selectedPaths: string[];
  onChange: (paths: string[]) => void;
}) {
  const [files, setFiles] = useState<InterviewFile[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [query, setQuery] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const response = await fetch("/api/files/interviews");
        const data = (await response.json()) as {
          files?: InterviewFile[];
          error?: string;
        };
        if (!response.ok) {
          throw new Error(data.error || "加载访谈文件失败");
        }
        if (!cancelled) {
          setFiles(data.files ?? []);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "加载访谈文件失败");
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return files;
    return files.filter((file) => {
      const stem = file.name.replace(/\.docx$/i, "");
      return (
        file.name.toLowerCase().includes(needle) ||
        stem.toLowerCase().includes(needle) ||
        file.path.toLowerCase().includes(needle)
      );
    });
  }, [files, query]);

  const selected = new Set(selectedPaths);

  const toggle = (filePath: string) => {
    if (selected.has(filePath)) {
      onChange(selectedPaths.filter((path) => path !== filePath));
    } else {
      onChange([...selectedPaths, filePath]);
    }
  };

  return (
    <div className="border-b border-slate-100 px-3.5 pb-2 pt-3">
      <div className="mb-2 flex flex-wrap items-center gap-2 text-sm text-slate-600">
        <FileText className="size-4 shrink-0" />
        <span className="font-medium text-slate-700">分析文件</span>
        <span className="text-xs text-slate-500">
          仅 docs/interviews · 可选；勾选后本轮只分析选中文件
        </span>
      </div>

      <div className="relative mb-2">
        <Search className="pointer-events-none absolute top-1/2 left-2.5 size-3.5 -translate-y-1/2 text-slate-400" />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="搜索文件名，如 001 或 interview…"
          className="w-full rounded-md border border-slate-200 bg-white py-1.5 pr-8 pl-8 text-xs text-slate-800 outline-none placeholder:text-slate-400 focus:border-slate-300 focus:ring-1 focus:ring-slate-200"
          aria-label="搜索访谈文件"
        />
        {query ? (
          <button
            type="button"
            onClick={() => setQuery("")}
            className="absolute top-1/2 right-2 -translate-y-1/2 rounded p-0.5 text-slate-400 hover:text-slate-600"
            aria-label="清除搜索"
          >
            <X className="size-3.5" />
          </button>
        ) : null}
      </div>

      {loading ? (
        <p className="text-xs text-slate-500">加载中…</p>
      ) : error ? (
        <p className="text-xs text-red-600">{error}</p>
      ) : files.length === 0 ? (
        <p className="text-xs text-slate-500">docs/interviews 下暂无 .docx</p>
      ) : filtered.length === 0 ? (
        <p className="text-xs text-slate-500">无匹配「{query.trim()}」的文件</p>
      ) : (
        <ul className="flex max-h-28 flex-wrap gap-2 overflow-y-auto">
          {filtered.map((file) => {
            const isOn = selected.has(file.path);
            return (
              <li key={file.path}>
                <button
                  type="button"
                  onClick={() => toggle(file.path)}
                  aria-pressed={isOn}
                  className={cn(
                    "rounded-md border px-2.5 py-1 text-xs transition-colors",
                    isOn
                      ? "border-indigo-300 bg-indigo-50 text-indigo-800"
                      : "border-slate-200 bg-white text-slate-700 hover:border-slate-300",
                  )}
                >
                  {file.name}
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {selectedPaths.length > 0 ? (
        <p className="mt-2 text-[11px] text-slate-500">
          已选 {selectedPaths.length} 个：
          {selectedPaths.map((p) => p.split("/").pop()).join("、")}
        </p>
      ) : null}
    </div>
  );
}
