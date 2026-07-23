import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { extractPreviewPaths, normalizePreviewPathInput } from "../src/lib/file-paths.ts";
import {
  linkifyBareProvenanceCitations,
  parseProvenanceFromFootnoteHref,
  parseProvenanceLabel,
} from "../src/lib/provenance.ts";
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
  resolvePreviewPath("/docs/interviews/interview_001.md", repoRoot),
  path.join(repoRoot, "docs/interviews/interview_001.md"),
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
assert.deepEqual(
  extractPreviewPaths("see /docs/interviews/interview_001.md here"),
  ["docs/interviews/interview_001.md"],
);
assert.equal(
  normalizePreviewPathInput("/docs/interviews/x.md"),
  "docs/interviews/x.md",
);
assert.equal(findRepoRoot(import.meta.dirname), repoRoot);

assert.deepEqual(parseProvenanceLabel("interview_001§L842"), {
  docId: "interview_001",
  path: "docs/interviews/interview_001.md",
  line: 842,
  lineEnd: undefined,
  label: "interview_001§L842",
});
assert.deepEqual(parseProvenanceLabel("eval_long§L100-L150"), {
  docId: "eval_long",
  path: "docs/interviews/eval_long.md",
  line: 100,
  lineEnd: 150,
  label: "eval_long§L100-L150",
});
assert.deepEqual(
  parseProvenanceFromFootnoteHref(
    "#user-content-fn-interview_001%C2%A7l842",
  ),
  {
    docId: "interview_001",
    path: "docs/interviews/interview_001.md",
    line: 842,
    lineEnd: undefined,
    label: "interview_001§L842",
  },
);
assert.equal(
  linkifyBareProvenanceCitations("claim[^interview_001§L10]。"),
  "claim[interview_001§L10](provenance://docs/interviews/interview_001.md#L10)。",
);
assert.equal(
  linkifyBareProvenanceCitations(
    "claim[^interview_001§L10]。\n\n[^interview_001§L10]: quote",
  ),
  "claim[^interview_001§L10]。\n\n[^interview_001§L10]: quote",
);

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
    "file",
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

console.log("file path + provenance assertions passed");
