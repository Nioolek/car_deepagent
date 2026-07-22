const PREVIEW_EXTENSION = /\.(?:docx|md|json|txt)$/i;

export function extractPreviewPaths(text: string): string[] {
  const candidates =
    text.match(
      /(?:\/[^\s"'`()<>[\]{}]+)*\/?(?:docs|workspace\/cache|data)\/[^\s"'`()<>[\]{}]+/gi,
    ) ?? [];

  return [
    ...new Set(
      candidates
        .map((candidate) => candidate.replace(/[.,;:!?]+$/, ""))
        .filter((candidate) => PREVIEW_EXTENSION.test(candidate)),
    ),
  ];
}
