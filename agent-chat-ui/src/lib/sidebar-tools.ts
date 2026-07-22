/** Tools rendered in side panels — hide from the chat transcript. */
export const SIDEBAR_ONLY_TOOL_NAMES = new Set([
  "write_todos",
  "write_todo",
]);

export function isSidebarOnlyTool(name: string | undefined | null): boolean {
  if (!name) return false;
  return SIDEBAR_ONLY_TOOL_NAMES.has(name.toLowerCase());
}

export function filterSidebarOnlyToolCalls<
  T extends { name?: string | null },
>(toolCalls: T[] | undefined | null): T[] {
  if (!toolCalls?.length) return [];
  return toolCalls.filter((tc) => !isSidebarOnlyTool(tc.name));
}
