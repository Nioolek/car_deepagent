import { existsSync } from "node:fs";
import { realpath } from "node:fs/promises";
import path from "node:path";

const ALLOWED_DIRECTORIES = ["docs", "workspace/cache", "data"] as const;

function isInside(parent: string, child: string): boolean {
  const relative = path.relative(parent, child);
  return (
    relative === "" ||
    (!relative.startsWith("..") && !path.isAbsolute(relative))
  );
}

export function resolvePreviewPath(
  requestedPath: string,
  repoRoot: string,
): string {
  const resolved = path.resolve(repoRoot, requestedPath);
  const allowed = ALLOWED_DIRECTORIES.some((directory) =>
    isInside(path.resolve(repoRoot, directory), resolved),
  );

  if (!allowed) {
    throw new Error("Path is not allowlisted");
  }

  return resolved;
}

export async function resolveRealPreviewPath(
  requestedPath: string,
  repoRoot: string,
): Promise<string> {
  const resolvedPath = resolvePreviewPath(requestedPath, repoRoot);
  const [canonicalPath, canonicalRoot] = await Promise.all([
    realpath(resolvedPath),
    realpath(repoRoot),
  ]);

  return resolvePreviewPath(canonicalPath, canonicalRoot);
}

export function findRepoRoot(startDirectory = process.cwd()): string {
  let current = path.resolve(startDirectory);

  while (true) {
    if (
      existsSync(path.join(current, "pyproject.toml")) &&
      existsSync(path.join(current, "src/car_deepagent"))
    ) {
      return current;
    }

    const parent = path.dirname(current);
    if (parent === current) {
      throw new Error(`Could not find repository root from ${startDirectory}`);
    }
    current = parent;
  }
}
