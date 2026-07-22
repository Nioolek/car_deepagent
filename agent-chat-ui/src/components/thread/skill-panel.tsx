"use client";

import { BookOpen, CheckCircle2, Sparkles } from "lucide-react";
import { cn } from "@/lib/utils";
import { useStreamContext } from "@/providers/Stream";
import {
  extractLoadedSkills,
  KNOWN_SKILLS,
} from "@/lib/extract-loaded-skills";

export function SkillPanel({
  variant = "desktop",
}: {
  variant?: "desktop" | "mobile";
}) {
  const stream = useStreamContext();
  const loaded = extractLoadedSkills(stream.messages ?? []);
  const loadedNames = new Set(loaded.map((s) => s.name));

  const body = (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
        <Sparkles className="size-4 text-indigo-600" />
        <h2 className="text-sm font-semibold text-slate-800">Skills</h2>
      </div>
      <ul className="divide-y divide-slate-100">
        {KNOWN_SKILLS.map((skill) => {
          const isLoaded = loadedNames.has(skill.name);
          return (
            <li
              key={skill.name}
              className="flex items-start gap-3 px-4 py-3"
            >
              <span className="mt-0.5 shrink-0">
                {isLoaded ? (
                  <CheckCircle2 className="size-4 text-indigo-600" />
                ) : (
                  <BookOpen className="size-4 text-slate-400" />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-medium text-slate-800">
                  {skill.label}
                </p>
                <p className="mt-0.5 truncate font-mono text-[11px] text-slate-500">
                  {skill.name}
                </p>
                <span
                  className={cn(
                    "mt-1.5 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium",
                    isLoaded
                      ? "bg-indigo-100 text-indigo-700"
                      : "bg-slate-100 text-slate-500",
                  )}
                >
                  {isLoaded ? "已加载" : "未加载"}
                </span>
              </div>
            </li>
          );
        })}
      </ul>
      {loaded.length === 0 ? (
        <p className="px-4 py-3 text-xs text-slate-500">
          Agent 通过 read_file 加载 /skills/…/SKILL.md，或使用 /skill-name
          命令后，此处标记为已加载。
        </p>
      ) : null}
    </div>
  );

  if (variant === "mobile") {
    return (
      <details className="rounded-lg border border-slate-200 bg-white lg:hidden">
        <summary className="cursor-pointer list-none px-4 py-3 text-sm font-medium text-slate-800">
          Skills（{loaded.length}/{KNOWN_SKILLS.length} 已加载）
        </summary>
        {body}
      </details>
    );
  }

  return (
    <aside className="hidden h-full w-72 shrink-0 flex-col overflow-hidden rounded-lg border border-slate-200 bg-white lg:flex">
      {body}
    </aside>
  );
}
