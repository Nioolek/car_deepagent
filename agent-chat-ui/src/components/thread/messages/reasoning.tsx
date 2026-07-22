import { BrainCircuit, ChevronDown } from "lucide-react";
import { useState } from "react";
import { MarkdownText } from "../markdown-text";

interface ReasoningBlockProps {
  reasoning: string;
  defaultOpen?: boolean;
}

export function ReasoningBlock({
  reasoning,
  defaultOpen = false,
}: ReasoningBlockProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  if (!reasoning.trim()) return null;

  return (
    <details
      open={isOpen}
      onToggle={(event) => setIsOpen(event.currentTarget.open)}
      className="group/reasoning border-border bg-muted/30 rounded-lg border"
    >
      <summary className="text-muted-foreground flex cursor-pointer list-none items-center gap-2 px-3 py-2 text-sm font-medium [&::-webkit-details-marker]:hidden">
        <BrainCircuit className="size-4" />
        <span>Reasoning</span>
        <ChevronDown className="ml-auto size-4 transition-transform group-open/reasoning:rotate-180" />
      </summary>
      <div className="border-border text-muted-foreground border-t px-3 py-2 text-sm">
        <MarkdownText>{reasoning}</MarkdownText>
      </div>
    </details>
  );
}
