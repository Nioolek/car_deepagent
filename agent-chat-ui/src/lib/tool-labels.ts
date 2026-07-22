import { KNOWN_SKILLS } from "@/lib/extract-loaded-skills";

const TOOL_LABELS: Record<string, string> = {
  read_file: "读取文件",
  read: "读取文件",
  write_file: "写入文件",
  write_todos: "更新待办",
  ls: "列出目录",
  glob: "匹配文件",
  grep: "搜索内容",
  edit_file: "编辑文件",
  execute: "执行命令",
  task: "子任务",
  ensure_document_markdown: "转换文档",
  ensure_summary_tree: "构建摘要树",
  get_chapter_summary: "章节摘要",
  get_chapter_excerpt: "章节摘录",
  get_user_profile: "用户画像",
  estimate_tokens: "估算 Token",
};

const SKILL_PATH_RE =
  /\/skills\/([a-z0-9]+(?:-[a-z0-9]+)*)\/SKILL\.md(?:$|\?|#)/i;

export function toolDisplayName(name: string | undefined | null): string {
  if (!name) return "工具";
  return TOOL_LABELS[name] ?? name;
}

export function skillNameFromPath(path: string): string | null {
  const match = path.replace(/\\/g, "/").match(SKILL_PATH_RE);
  return match?.[1] ?? null;
}

export function skillLoadSummaryFromPath(path: string): string | null {
  const name = skillNameFromPath(path);
  if (!name) return null;
  const known = KNOWN_SKILLS.find((s) => s.name === name);
  const label = known?.label ?? name;
  return `已加载 skill：${label}（${name}）`;
}

export function pathFromToolArgs(args: unknown): string | null {
  if (!args || typeof args !== "object") return null;
  const record = args as Record<string, unknown>;
  for (const key of ["file_path", "path", "filepath"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}
