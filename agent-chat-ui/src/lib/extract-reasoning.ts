import type { Message } from "@langchain/langgraph-sdk";

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null;
}

function isReasoningBlock(value: unknown): value is UnknownRecord {
  if (!isRecord(value)) return false;
  const type = value.type;
  return (
    type === "reasoning" ||
    type === "thinking" ||
    type === "reasoning_content" ||
    type === "thought"
  );
}

function getReasoningText(value: unknown): string | null {
  if (typeof value === "string") {
    const text = value.trim();
    return text.length > 0 ? text : null;
  }

  if (!isRecord(value)) return null;

  // Prefer common leaf keys before recursing blindly.
  for (const key of [
    "text",
    "reasoning",
    "thinking",
    "reasoning_content",
    "content",
    "summary",
  ]) {
    const nested = value[key];
    if (typeof nested === "string") {
      const text = nested.trim();
      if (text) return text;
    }
  }

  for (const key of [
    "text",
    "reasoning",
    "thinking",
    "reasoning_content",
    "content",
  ]) {
    const text = getReasoningText(value[key]);
    if (text) return text;
  }

  return null;
}

function pushUnique(parts: string[], text: string | null) {
  if (!text) return;
  if (!parts.includes(text)) parts.push(text);
}

/**
 * Extract model thinking / reasoning text from an AI message.
 * Supports DeepSeek-style additional_kwargs.reasoning_content and content blocks.
 */
export function extractReasoning(message: Message): string | null {
  const parts: string[] = [];

  if (Array.isArray(message.content)) {
    for (const block of message.content) {
      if (isReasoningBlock(block)) {
        pushUnique(parts, getReasoningText(block));
      }
    }
  }

  if ("additional_kwargs" in message && isRecord(message.additional_kwargs)) {
    const kwargs = message.additional_kwargs;
    for (const key of [
      "reasoning_content",
      "reasoning",
      "thinking",
      "reasoning_details",
    ]) {
      pushUnique(parts, getReasoningText(kwargs[key]));
    }
  }

  if ("response_metadata" in message && isRecord(message.response_metadata)) {
    const meta = message.response_metadata;
    for (const key of ["reasoning_content", "reasoning", "thinking"]) {
      pushUnique(parts, getReasoningText(meta[key]));
    }
  }

  // Some serializers flatten reasoning onto the message root.
  const root = message as unknown as UnknownRecord;
  for (const key of ["reasoning_content", "reasoning", "thinking"]) {
    pushUnique(parts, getReasoningText(root[key]));
  }

  return parts.length > 0 ? parts.join("\n\n") : null;
}
