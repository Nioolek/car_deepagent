import type { Message } from "@langchain/langgraph-sdk";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function isReasoningBlock(value: unknown): value is UnknownRecord {
  return (
    isRecord(value) && (value.type === "reasoning" || value.type === "thinking")
  );
}

function getReasoningText(value: unknown): string | null {
  if (typeof value === "string") {
    const text = value.trim();
    return text.length > 0 ? text : null;
  }

  if (!isRecord(value)) return null;

  for (const key of ["text", "reasoning", "thinking", "content"]) {
    const text = getReasoningText(value[key]);
    if (text) return text;
  }

  return null;
}

export function extractReasoning(message: Message): string | null {
  const parts: string[] = [];

  if (Array.isArray(message.content)) {
    for (const block of message.content) {
      if (isReasoningBlock(block)) {
        const text = getReasoningText(block);
        if (text) parts.push(text);
      }
    }
  }

  if ("additional_kwargs" in message && isRecord(message.additional_kwargs)) {
    for (const key of ["reasoning", "reasoning_content"]) {
      const text = getReasoningText(message.additional_kwargs[key]);
      if (text) parts.push(text);
    }
  }

  return parts.length > 0 ? parts.join("\n\n") : null;
}
