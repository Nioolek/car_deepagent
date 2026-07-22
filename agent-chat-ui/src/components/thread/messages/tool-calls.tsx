import { AIMessage, ToolMessage } from "@langchain/langgraph-sdk";
import { useState, type ReactNode } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, ChevronUp } from "lucide-react";
import { FilePathButtons } from "../file-preview";

const COLLAPSED_MAX_ENTRIES = 5;
const COLLAPSED_MAX_CHARS = 500;
const COLLAPSED_VALUE_CHARS = 100;

function isComplexValue(value: unknown): boolean {
  return Array.isArray(value) || (typeof value === "object" && value !== null);
}

function shouldTruncateContent(content: unknown): boolean {
  const contentStr = isComplexValue(content)
    ? JSON.stringify(content, null, 2)
    : String(content);
  return (
    contentStr.split("\n").length > 4 || contentStr.length > COLLAPSED_MAX_CHARS
  );
}

function truncateValue(value: unknown, isExpanded: boolean): unknown {
  if (isExpanded) return value;

  if (typeof value === "string" && value.length > COLLAPSED_VALUE_CHARS) {
    return value.substring(0, COLLAPSED_VALUE_CHARS) + "...";
  }

  if (Array.isArray(value)) {
    return value.slice(0, 2).map((item) => truncateValue(item, isExpanded));
  }

  if (isComplexValue(value)) {
    const strValue = JSON.stringify(value, null, 2);
    if (strValue.length > COLLAPSED_VALUE_CHARS) {
      return `Truncated ${strValue.length} characters...`;
    }
  }

  return value;
}

function renderCellValue(value: unknown): ReactNode {
  if (isComplexValue(value)) {
    return (
      <code className="rounded bg-gray-50 px-2 py-1 font-mono text-sm break-all">
        {JSON.stringify(value, null, 2)}
      </code>
    );
  }
  return String(value);
}

function ExpandToggle({
  isExpanded,
  onToggle,
}: {
  isExpanded: boolean;
  onToggle: () => void;
}) {
  return (
    <motion.button
      type="button"
      onClick={onToggle}
      className="flex w-full cursor-pointer items-center justify-center border-t border-gray-200 py-2 text-gray-500 transition-all duration-200 ease-in-out hover:bg-gray-50 hover:text-gray-600"
      initial={{ scale: 1 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      aria-expanded={isExpanded}
      aria-label={isExpanded ? "收起" : "展开"}
    >
      {isExpanded ? <ChevronUp /> : <ChevronDown />}
    </motion.button>
  );
}

function KeyValueTable({
  data,
  isExpanded,
}: {
  data: Record<string, unknown> | unknown[];
  isExpanded: boolean;
}) {
  const entries = Array.isArray(data)
    ? isExpanded
      ? data.map((value, index) => [String(index), value] as const)
      : data
          .slice(0, COLLAPSED_MAX_ENTRIES)
          .map((value, index) => [String(index), truncateValue(value, isExpanded)] as const)
    : isExpanded
      ? Object.entries(data)
      : Object.entries(data)
          .slice(0, COLLAPSED_MAX_ENTRIES)
          .map(([key, value]) => [key, truncateValue(value, isExpanded)] as const);

  return (
    <table className="min-w-full divide-y divide-gray-200">
      <tbody className="divide-y divide-gray-200">
        {entries.map(([key, value], argIdx) => (
          <tr key={argIdx}>
            <td className="px-4 py-2 text-sm font-medium whitespace-nowrap text-gray-900">
              {key}
            </td>
            <td className="px-4 py-2 text-sm text-gray-500">
              {renderCellValue(value)}
              <FilePathButtons value={value} />
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function needsExpandToggle(data: unknown, isJsonContent: boolean): boolean {
  if (!isJsonContent) {
    const contentStr = String(data);
    return (
      contentStr.split("\n").length > 4 ||
      contentStr.length > COLLAPSED_MAX_CHARS
    );
  }

  if (Array.isArray(data)) {
    return data.length > COLLAPSED_MAX_ENTRIES || shouldTruncateContent(data);
  }

  if (isComplexValue(data)) {
    const entries = Object.entries(data as Record<string, unknown>);
    return entries.length > COLLAPSED_MAX_ENTRIES || shouldTruncateContent(data);
  }

  return false;
}

function ExpandableContent({
  data,
  isJsonContent,
  plainText,
}: {
  data: unknown;
  isJsonContent: boolean;
  plainText?: string;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const showToggle = needsExpandToggle(data, isJsonContent);

  const displayedPlainText = (() => {
    const contentStr = plainText ?? String(data);
    if (!showToggle || isExpanded) return contentStr;
    if (contentStr.length > COLLAPSED_MAX_CHARS) {
      return contentStr.slice(0, COLLAPSED_MAX_CHARS) + "...";
    }
    return contentStr.split("\n").slice(0, 4).join("\n") + "\n...";
  })();

  return (
    <>
      <motion.div
        className="min-w-full bg-gray-100"
        initial={false}
        animate={{ height: "auto" }}
        transition={{ duration: 0.3 }}
      >
        <div className="p-3">
          <AnimatePresence
            mode="wait"
            initial={false}
          >
            <motion.div
              key={isExpanded ? "expanded" : "collapsed"}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -20 }}
              transition={{ duration: 0.2 }}
              style={{
                maxHeight: isExpanded ? "none" : "500px",
                overflow: "auto",
              }}
            >
              {isJsonContent && isComplexValue(data) ? (
                <KeyValueTable
                  data={data as Record<string, unknown> | unknown[]}
                  isExpanded={isExpanded}
                />
              ) : (
                <>
                  <code className="block text-sm break-all whitespace-pre-wrap">
                    {displayedPlainText}
                  </code>
                  <FilePathButtons value={plainText ?? data} />
                </>
              )}
            </motion.div>
          </AnimatePresence>
        </div>
        {showToggle && (
          <ExpandToggle
            isExpanded={isExpanded}
            onToggle={() => setIsExpanded((prev) => !prev)}
          />
        )}
      </motion.div>
    </>
  );
}

export function ToolCalls({
  toolCalls,
}: {
  toolCalls: AIMessage["tool_calls"];
}) {
  if (!toolCalls || toolCalls.length === 0) return null;

  return (
    <div className="mx-auto grid max-w-3xl grid-rows-[1fr_auto] gap-2">
      {toolCalls.map((tc, idx) => {
        const args = (tc.args ?? {}) as Record<string, unknown>;
        const hasArgs = Object.keys(args).length > 0;
        return (
          <div
            key={idx}
            className="overflow-hidden rounded-lg border border-gray-200"
          >
            <div className="border-b border-gray-200 bg-gray-50 px-4 py-2">
              <h3 className="font-medium text-gray-900">
                {tc.name}
                {tc.id && (
                  <code className="ml-2 rounded bg-gray-100 px-2 py-1 text-sm">
                    {tc.id}
                  </code>
                )}
              </h3>
            </div>
            {hasArgs ? (
              <ExpandableContent
                data={args}
                isJsonContent
              />
            ) : (
              <code className="block p-3 text-sm">{"{}"}</code>
            )}
          </div>
        );
      })}
    </div>
  );
}

export function ToolResult({ message }: { message: ToolMessage }) {
  let parsedContent: unknown = message.content;
  let isJsonContent = false;

  try {
    if (typeof message.content === "string") {
      parsedContent = JSON.parse(message.content);
      isJsonContent = isComplexValue(parsedContent);
    }
  } catch {
    parsedContent = message.content;
  }

  const plainText =
    typeof message.content === "string" ? message.content : String(message.content);

  return (
    <div className="mx-auto grid max-w-3xl grid-rows-[1fr_auto] gap-2">
      <div className="overflow-hidden rounded-lg border border-gray-200">
        <div className="border-b border-gray-200 bg-gray-50 px-4 py-2">
          <div className="flex flex-wrap items-center justify-between gap-2">
            {message.name ? (
              <h3 className="font-medium text-gray-900">
                Tool Result:{" "}
                <code className="rounded bg-gray-100 px-2 py-1">
                  {message.name}
                </code>
              </h3>
            ) : (
              <h3 className="font-medium text-gray-900">Tool Result</h3>
            )}
            {message.tool_call_id && (
              <code className="ml-2 rounded bg-gray-100 px-2 py-1 text-sm">
                {message.tool_call_id}
              </code>
            )}
          </div>
        </div>
        <ExpandableContent
          data={parsedContent}
          isJsonContent={isJsonContent}
          plainText={plainText}
        />
      </div>
    </div>
  );
}
