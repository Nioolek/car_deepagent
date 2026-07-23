const PREVIEW_EXTENSION = /\.(?:docx|md|json|txt)$/i;

/** Strip virtual-FS leading slash: `/docs/...` → `docs/...`. */
export function normalizePreviewPathInput(path: string): string {
  const trimmed = path.trim();
  if (/^\/(?:docs|workspace\/cache|data)(?:\/|$)/i.test(trimmed)) {
    return trimmed.replace(/^\/+/, "");
  }
  return trimmed;
}

export function extractPreviewPaths(text: string): string[] {
  const candidates =
    text.match(
      /(?:\/[^\s"'`()<>[\]{}]+)*\/?(?:docs|workspace\/cache|data)\/[^\s"'`()<>[\]{}]+/gi,
    ) ?? [];

  return [
    ...new Set(
      candidates
        .map((candidate) => candidate.replace(/[.,;:!?]+$/, ""))
        .map(normalizePreviewPathInput)
        .filter((candidate) => PREVIEW_EXTENSION.test(candidate)),
    ),
  ];
}
