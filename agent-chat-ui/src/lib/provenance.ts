/** Parse and normalize interview provenance citations like `doc§L123`. */

export interface ProvenanceTarget {
  docId: string;
  path: string;
  line: number;
  lineEnd?: number;
  label: string;
}

const LABEL_RE =
  /^([A-Za-z0-9_-]+)§[lL](\d+)(?:-[lL](\d+))?$/i;

const FOOTNOTE_HREF_RE =
  /^#(?:user-content-)?fn(?:ref)?-(.+)$/i;

const INLINE_CITATION_RE =
  /\[\^([A-Za-z0-9_-]+§L\d+(?:-L\d+)?)\](?!:)/g;

export function interviewPathForDocId(docId: string): string {
  return `docs/interviews/${docId}.md`;
}

export function parseProvenanceLabel(raw: string): ProvenanceTarget | null {
  const label = raw.trim();
  const match = LABEL_RE.exec(label);
  if (!match) return null;
  const docId = match[1];
  const line = Number(match[2]);
  const lineEnd = match[3] ? Number(match[3]) : undefined;
  if (!Number.isFinite(line) || line < 1) return null;
  if (lineEnd !== undefined && (!Number.isFinite(lineEnd) || lineEnd < line)) {
    return null;
  }
  return {
    docId,
    path: interviewPathForDocId(docId),
    line,
    lineEnd,
    label: lineEnd
      ? `${docId}§L${line}-L${lineEnd}`
      : `${docId}§L${line}`,
  };
}

/** Extract provenance from GFM footnote href/id (handles encoded §). */
export function parseProvenanceFromFootnoteHref(
  href: string | undefined | null,
): ProvenanceTarget | null {
  if (!href) return null;
  let decoded = href;
  try {
    decoded = decodeURIComponent(href);
  } catch {
    // keep raw
  }
  const match = FOOTNOTE_HREF_RE.exec(decoded);
  if (!match) return null;
  return parseProvenanceLabel(match[1]);
}

export function parseProvenanceFromProvenanceUrl(
  href: string | undefined | null,
): ProvenanceTarget | null {
  if (!href?.startsWith("provenance://")) return null;
  try {
    const url = new URL(href);
    const path = decodeURIComponent(url.pathname.replace(/^\//, ""));
    const hash = url.hash.replace(/^#/, "");
    const lineMatch = /^L(\d+)(?:-L(\d+))?$/i.exec(hash);
    if (!lineMatch) return null;
    const docId = path.split("/").pop()?.replace(/\.md$/i, "") ?? "";
    const line = Number(lineMatch[1]);
    const lineEnd = lineMatch[2] ? Number(lineMatch[2]) : undefined;
    if (!docId || !Number.isFinite(line)) return null;
    return {
      docId,
      path,
      line,
      lineEnd,
      label: lineEnd
        ? `${docId}§L${line}-L${lineEnd}`
        : `${docId}§L${line}`,
    };
  } catch {
    return null;
  }
}

/**
 * Rewrite bare `[^doc§L…]` (no matching footnote definition) into provenance
 * links. Leaves defined GFM footnotes alone so 参考文献摘录 still renders.
 */
export function linkifyBareProvenanceCitations(markdown: string): string {
  const defined = new Set(
    [...markdown.matchAll(/^\[\^([^\]]+)\]:/gm)].map((match) => match[1]),
  );
  return markdown.replace(INLINE_CITATION_RE, (full, label: string) => {
    if (defined.has(label)) return full;
    const target = parseProvenanceLabel(label);
    if (!target) return full;
    const hash = target.lineEnd
      ? `L${target.line}-L${target.lineEnd}`
      : `L${target.line}`;
    return `[${target.label}](provenance://${target.path}#${hash})`;
  });
}
