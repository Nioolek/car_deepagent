import { Message } from "@langchain/langgraph-sdk";

const SKILL_PATH_RE =
  /\/skills\/([a-z0-9]+(?:-[a-z0-9]+)*)\/SKILL\.md(?:$|\?|#)/i;

export type LoadedSkill = {
  name: string;
  path: string;
};

function pathFromToolCallArgs(args: unknown): string | null {
  if (!args || typeof args !== "object") return null;
  const record = args as Record<string, unknown>;
  for (const key of ["file_path", "path", "filepath"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return null;
}

function skillFromPath(path: string): LoadedSkill | null {
  const match = path.replace(/\\/g, "/").match(SKILL_PATH_RE);
  if (!match) return null;
  return { name: match[1], path: match[0].replace(/(?:\?|#).*$/, "") };
}

/**
 * Detect skills the agent loaded via read_file (progressive disclosure).
 */
export function extractLoadedSkills(messages: Message[]): LoadedSkill[] {
  const byName = new Map<string, LoadedSkill>();

  for (const message of messages) {
    if (message.type !== "ai") continue;
    const toolCalls =
      "tool_calls" in message && Array.isArray(message.tool_calls)
        ? message.tool_calls
        : [];
    for (const tc of toolCalls) {
      const name = tc.name?.toLowerCase?.() ?? "";
      if (name !== "read_file" && name !== "read") continue;
      const path = pathFromToolCallArgs(tc.args);
      if (!path) continue;
      const skill = skillFromPath(path);
      if (skill) byName.set(skill.name, skill);
    }
  }

  return Array.from(byName.values());
}

export const KNOWN_SKILLS = [
  {
    name: "single-report-analysis",
    label: "单篇报告分析",
  },
  {
    name: "multi-report-synthesis",
    label: "多篇报告综合",
  },
  {
    name: "user-profile-lookup",
    label: "用户画像查询",
  },
] as const;
