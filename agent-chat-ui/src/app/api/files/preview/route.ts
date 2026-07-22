import { readFile } from "node:fs/promises";
import path from "node:path";
import mammoth from "mammoth";
import { NextRequest, NextResponse } from "next/server";

import { findRepoRoot, resolveRealPreviewPath } from "@/lib/repo-root";

export const runtime = "nodejs";

const MEDIA_TYPES: Record<string, string> = {
  ".docx":
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ".json": "application/json",
  ".md": "text/markdown",
  ".txt": "text/plain",
};

export async function GET(request: NextRequest) {
  const requestedPath = request.nextUrl.searchParams.get("path");
  if (!requestedPath) {
    return NextResponse.json({ error: "Missing path" }, { status: 400 });
  }

  const repoRoot = findRepoRoot();
  let resolvedPath: string;
  try {
    resolvedPath = await resolveRealPreviewPath(requestedPath, repoRoot);
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    return NextResponse.json(
      {
        error: code === "ENOENT" ? "File not found" : "Path is not allowlisted",
      },
      { status: code === "ENOENT" ? 404 : 403 },
    );
  }

  const extension = path.extname(resolvedPath).toLowerCase();
  const mediaType = MEDIA_TYPES[extension];
  if (!mediaType) {
    return NextResponse.json(
      { error: "File type is not supported" },
      { status: 415 },
    );
  }

  try {
    const content =
      extension === ".docx"
        ? (await mammoth.extractRawText({ path: resolvedPath })).value
        : await readFile(resolvedPath, "utf8");

    return NextResponse.json({ path: requestedPath, mediaType, content });
  } catch (error) {
    const code = (error as NodeJS.ErrnoException).code;
    return NextResponse.json(
      {
        error: code === "ENOENT" ? "File not found" : "Could not preview file",
      },
      { status: code === "ENOENT" ? 404 : 500 },
    );
  }
}
