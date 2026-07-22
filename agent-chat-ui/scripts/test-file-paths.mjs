import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { extractPreviewPaths } from "../src/lib/file-paths.ts";
import {
  findRepoRoot,
  resolvePreviewPath,
  resolveRealPreviewPath,
} from "../src/lib/repo-root.ts";

const repoRoot = path.resolve(import.meta.dirname, "../..");

assert.equal(
  resolvePreviewPath("docs/example.md", repoRoot),
  path.join(repoRoot, "docs/example.md"),
);
assert.equal(
  resolvePreviewPath(path.join(repoRoot, "data/example.json"), repoRoot),
  path.join(repoRoot, "data/example.json"),
);
assert.throws(
  () => resolvePreviewPath("../etc/passwd", repoRoot),
  /not allowlisted/i,
);
assert.throws(
  () => resolvePreviewPath("docs/../../etc/passwd", repoRoot),
  /not allowlisted/i,
);
assert.deepEqual(
  extractPreviewPaths(
    "Saved docs/report.md and /tmp/repo/workspace/cache/result.json.",
  ),
  ["docs/report.md", "/tmp/repo/workspace/cache/result.json"],
);
assert.equal(findRepoRoot(import.meta.dirname), repoRoot);

const temporaryRoot = await mkdtemp(path.join(os.tmpdir(), "file-preview-"));
const outsideRoot = await mkdtemp(
  path.join(os.tmpdir(), "file-preview-outside-"),
);
try {
  await mkdir(path.join(temporaryRoot, "data"));
  await writeFile(path.join(temporaryRoot, "data", "allowed.txt"), "allowed");
  await writeFile(path.join(outsideRoot, "secret.txt"), "secret");
  await symlink(
    path.join(outsideRoot, "secret.txt"),
    path.join(temporaryRoot, "data", "escaped.txt"),
  );

  assert.equal(
    await resolveRealPreviewPath("data/allowed.txt", temporaryRoot),
    path.join(temporaryRoot, "data", "allowed.txt"),
  );
  await assert.rejects(
    resolveRealPreviewPath("data/escaped.txt", temporaryRoot),
    /not allowlisted/i,
  );
} finally {
  await Promise.all([
    rm(temporaryRoot, { recursive: true, force: true }),
    rm(outsideRoot, { recursive: true, force: true }),
  ]);
}

console.log("file path assertions passed");
