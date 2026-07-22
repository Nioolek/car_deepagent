import { readdir } from "node:fs/promises";
import path from "node:path";
import { NextRequest, NextResponse } from "next/server";

import { findRepoRoot } from "@/lib/repo-root";

export const runtime = "nodejs";

type InterviewFile = {
  name: string;
  path: string;
};

function matchesQuery(file: InterviewFile, query: string): boolean {
  const needle = query.trim().toLowerCase();
  if (!needle) return true;
  const stem = file.name.replace(/\.docx$/i, "");
  return (
    file.name.toLowerCase().includes(needle) ||
    stem.toLowerCase().includes(needle) ||
    file.path.toLowerCase().includes(needle)
  );
}

export async function GET(request: NextRequest) {
  try {
    const query = request.nextUrl.searchParams.get("q") ?? "";
    const repoRoot = findRepoRoot();
    const interviewsDir = path.join(repoRoot, "docs", "interviews");
    const entries = await readdir(interviewsDir, { withFileTypes: true });
    const files = entries
      .filter(
        (entry) =>
          entry.isFile() && entry.name.toLowerCase().endsWith(".docx"),
      )
      .map((entry) => ({
        name: entry.name,
        path: path.posix.join("docs", "interviews", entry.name),
      }))
      .filter((file) => matchesQuery(file, query))
      .sort((a, b) => a.name.localeCompare(b.name));

    return NextResponse.json({
      files,
      root: "docs/interviews",
      query: query.trim() || null,
    });
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Could not list interviews";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
