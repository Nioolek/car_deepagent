"use client";

import "./markdown-styles.css";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeKatex from "rehype-katex";
import remarkMath from "remark-math";
import { FC, memo, useMemo, useState } from "react";
import { CheckIcon, CopyIcon } from "lucide-react";
import { SyntaxHighlighter } from "@/components/thread/syntax-highlighter";

import { TooltipIconButton } from "@/components/thread/tooltip-icon-button";
import { cn } from "@/lib/utils";
import { FilePathButtons, useFilePreview } from "./file-preview";
import {
  linkifyBareProvenanceCitations,
  parseProvenanceFromFootnoteHref,
  parseProvenanceFromProvenanceUrl,
  type ProvenanceTarget,
} from "@/lib/provenance";

import "katex/dist/katex.min.css";

interface CodeHeaderProps {
  language?: string;
  code: string;
}

const useCopyToClipboard = ({
  copiedDuration = 3000,
}: {
  copiedDuration?: number;
} = {}) => {
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const copyToClipboard = (value: string) => {
    if (!value) return;

    navigator.clipboard.writeText(value).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), copiedDuration);
    });
  };

  return { isCopied, copyToClipboard };
};

const CodeHeader: FC<CodeHeaderProps> = ({ language, code }) => {
  const { isCopied, copyToClipboard } = useCopyToClipboard();
  const onCopy = () => {
    if (!code || isCopied) return;
    copyToClipboard(code);
  };

  return (
    <div className="flex items-center justify-between gap-4 rounded-t-lg bg-zinc-900 px-4 py-2 text-sm font-semibold text-white">
      <span className="lowercase [&>span]:text-xs">{language}</span>
      <TooltipIconButton
        tooltip="Copy"
        onClick={onCopy}
      >
        {!isCopied && <CopyIcon />}
        {isCopied && <CheckIcon />}
      </TooltipIconButton>
    </div>
  );
};

function ProvenanceLink({
  target,
  children,
  className,
  title,
}: {
  target: ProvenanceTarget;
  children: React.ReactNode;
  className?: string;
  title?: string;
}) {
  const { openPath } = useFilePreview();
  return (
    <button
      type="button"
      onClick={(event) => {
        event.preventDefault();
        openPath(target.path, { line: target.line, lineEnd: target.lineEnd });
      }}
      className={cn(
        "text-primary cursor-pointer font-medium underline underline-offset-4",
        className,
      )}
      title={title ?? `打开 ${target.path} · ${target.label}`}
    >
      {children}
    </button>
  );
}

function buildMarkdownComponents(): Record<string, unknown> {
  return {
    h1: ({ className, ...props }: { className?: string }) => (
      <h1
        className={cn(
          "mb-8 scroll-m-20 text-4xl font-extrabold tracking-tight last:mb-0",
          className,
        )}
        {...props}
      />
    ),
    h2: ({ className, ...props }: { className?: string }) => (
      <h2
        className={cn(
          "mt-8 mb-4 scroll-m-20 text-3xl font-semibold tracking-tight first:mt-0 last:mb-0",
          className,
        )}
        {...props}
      />
    ),
    h3: ({ className, ...props }: { className?: string }) => (
      <h3
        className={cn(
          "mt-6 mb-4 scroll-m-20 text-2xl font-semibold tracking-tight first:mt-0 last:mb-0",
          className,
        )}
        {...props}
      />
    ),
    h4: ({ className, ...props }: { className?: string }) => (
      <h4
        className={cn(
          "mt-6 mb-4 scroll-m-20 text-xl font-semibold tracking-tight first:mt-0 last:mb-0",
          className,
        )}
        {...props}
      />
    ),
    h5: ({ className, ...props }: { className?: string }) => (
      <h5
        className={cn(
          "my-4 text-lg font-semibold first:mt-0 last:mb-0",
          className,
        )}
        {...props}
      />
    ),
    h6: ({ className, ...props }: { className?: string }) => (
      <h6
        className={cn("my-4 font-semibold first:mt-0 last:mb-0", className)}
        {...props}
      />
    ),
    p: ({ className, ...props }: { className?: string }) => (
      <p
        className={cn("mt-5 mb-5 leading-7 first:mt-0 last:mb-0", className)}
        {...props}
      />
    ),
    a: ({
      className,
      href,
      children,
      ...props
    }: {
      className?: string;
      href?: string;
      children?: React.ReactNode;
      "data-footnote-ref"?: boolean;
      "data-footnote-backref"?: string | boolean;
    }) => {
      const target =
        parseProvenanceFromProvenanceUrl(href) ??
        parseProvenanceFromFootnoteHref(href);

      if (target) {
        return (
          <ProvenanceLink
            target={target}
            className={cn(
              props["data-footnote-ref"] && "text-xs no-underline",
              props["data-footnote-backref"] !== undefined && "ml-1 no-underline",
              className,
            )}
            title={`打开原文 ${target.path} · ${target.label}`}
          >
            {children}
          </ProvenanceLink>
        );
      }

      return (
        <a
          className={cn(
            "text-primary font-medium underline underline-offset-4",
            className,
          )}
          href={href}
          {...props}
        >
          {children}
        </a>
      );
    },
    blockquote: ({ className, ...props }: { className?: string }) => (
      <blockquote
        className={cn("border-l-2 pl-6 italic", className)}
        {...props}
      />
    ),
    ul: ({ className, ...props }: { className?: string }) => (
      <ul
        className={cn("my-5 ml-6 list-disc [&>li]:mt-2", className)}
        {...props}
      />
    ),
    ol: ({ className, ...props }: { className?: string }) => (
      <ol
        className={cn("my-5 ml-6 list-decimal [&>li]:mt-2", className)}
        {...props}
      />
    ),
    hr: ({ className, ...props }: { className?: string }) => (
      <hr
        className={cn("my-5 border-b", className)}
        {...props}
      />
    ),
    table: ({ className, ...props }: { className?: string }) => (
      <table
        className={cn(
          "my-5 w-full border-separate border-spacing-0 overflow-y-auto",
          className,
        )}
        {...props}
      />
    ),
    th: ({ className, ...props }: { className?: string }) => (
      <th
        className={cn(
          "bg-muted px-4 py-2 text-left font-bold first:rounded-tl-lg last:rounded-tr-lg [&[align=center]]:text-center [&[align=right]]:text-right",
          className,
        )}
        {...props}
      />
    ),
    td: ({ className, ...props }: { className?: string }) => (
      <td
        className={cn(
          "border-b border-l px-4 py-2 text-left last:border-r [&[align=center]]:text-center [&[align=right]]:text-right",
          className,
        )}
        {...props}
      />
    ),
    tr: ({ className, ...props }: { className?: string }) => (
      <tr
        className={cn(
          "m-0 border-b p-0 first:border-t [&:last-child>td:first-child]:rounded-bl-lg [&:last-child>td:last-child]:rounded-br-lg",
          className,
        )}
        {...props}
      />
    ),
    sup: ({ className, ...props }: { className?: string }) => (
      <sup
        className={cn("[&>button]:text-xs [&>a]:text-xs [&>a]:no-underline", className)}
        {...props}
      />
    ),
    pre: ({ className, ...props }: { className?: string }) => (
      <pre
        className={cn(
          "max-w-4xl overflow-x-auto rounded-lg bg-black text-white",
          className,
        )}
        {...props}
      />
    ),
    code: ({
      className,
      children,
      ...props
    }: {
      className?: string;
      children: React.ReactNode;
    }) => {
      const match = /language-(\w+)/.exec(className || "");

      if (match) {
        const language = match[1];
        const code = String(children).replace(/\n$/, "");

        return (
          <>
            <CodeHeader
              language={language}
              code={code}
            />
            <SyntaxHighlighter
              language={language}
              className={className}
            >
              {code}
            </SyntaxHighlighter>
          </>
        );
      }

      return (
        <code
          className={cn("rounded font-semibold", className)}
          {...props}
        >
          {children}
        </code>
      );
    },
  };
}

const MarkdownTextImpl: FC<{ children: string }> = ({ children }) => {
  const content = useMemo(
    () => linkifyBareProvenanceCitations(children),
    [children],
  );
  const components = useMemo(() => buildMarkdownComponents(), []);

  return (
    <div className="markdown-content">
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkMath]}
        rehypePlugins={[rehypeKatex]}
        components={components as any}
      >
        {content}
      </ReactMarkdown>
      <FilePathButtons value={children} />
    </div>
  );
};

export const MarkdownText = memo(MarkdownTextImpl);
