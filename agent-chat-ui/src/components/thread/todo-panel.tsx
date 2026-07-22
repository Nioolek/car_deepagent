"use client";

import {
  CheckCircle2,
  ChevronDown,
  Circle,
  ListTodo,
  LoaderCircle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { type TodoItem, useStreamContext } from "@/providers/Stream";

const statusDetails: Record<
  TodoItem["status"],
  { label: string; className: string; rowClassName: string }
> = {
  pending: {
    label: "待处理",
    className: "bg-slate-100 text-slate-600",
    rowClassName: "border-l-transparent",
  },
  in_progress: {
    label: "进行中",
    className: "bg-amber-100 text-amber-800",
    rowClassName: "border-l-amber-400 bg-amber-50/60",
  },
  completed: {
    label: "已完成",
    className: "bg-emerald-100 text-emerald-700",
    rowClassName: "border-l-emerald-300/80",
  },
};

function StatusIcon({ status }: { status: TodoItem["status"] }) {
  if (status === "completed") {
    return <CheckCircle2 className="size-4 text-emerald-600" />;
  }
  if (status === "in_progress") {
    return <LoaderCircle className="size-4 animate-spin text-amber-600" />;
  }
  return <Circle className="size-4 text-slate-300" />;
}

function ProgressSummary({ todos }: { todos: TodoItem[] }) {
  const total = todos.length;
  const completed = todos.filter((t) => t.status === "completed").length;
  const inProgress = todos.filter((t) => t.status === "in_progress").length;
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100);

  return (
    <div className="space-y-2 border-b border-slate-100 px-4 py-3">
      <div className="flex items-baseline justify-between gap-2">
        <p className="text-xs text-slate-500">
          {total === 0
            ? "等待 Agent 规划步骤"
            : `${completed}/${total} 已完成`}
          {inProgress > 0 ? (
            <span className="ml-2 text-amber-700">· {inProgress} 进行中</span>
          ) : null}
        </p>
        {total > 0 ? (
          <span className="text-[11px] font-medium tabular-nums text-slate-500">
            {percent}%
          </span>
        ) : null}
      </div>
      <div className="h-1.5 overflow-hidden rounded-full bg-slate-100">
        <div
          className={cn(
            "h-full rounded-full transition-[width] duration-500 ease-out",
            percent === 100 ? "bg-emerald-500" : "bg-slate-700",
          )}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function TodoList({ todos }: { todos: TodoItem[] }) {
  if (todos.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center gap-2 px-6 py-10 text-center">
        <ListTodo className="size-8 text-slate-200" />
        <p className="text-sm text-slate-500">暂无待办</p>
        <p className="text-xs leading-relaxed text-slate-400">
          Agent 调用规划工具后，步骤会显示在这里，而不会出现在对话里。
        </p>
      </div>
    );
  }

  return (
    <ol className="flex flex-col gap-1 p-2">
      {todos.map((todo, index) => {
        const details = statusDetails[todo.status] ?? statusDetails.pending;
        return (
          <li
            key={`${todo.content}-${index}`}
            className={cn(
              "flex items-start gap-3 rounded-lg border-l-2 px-3 py-2.5 transition-colors",
              details.rowClassName,
            )}
          >
            <span className="mt-0.5 flex size-5 shrink-0 items-center justify-center text-[11px] font-medium tabular-nums text-slate-400">
              {index + 1}
            </span>
            <span className="mt-0.5 shrink-0">
              <StatusIcon status={todo.status} />
            </span>
            <div className="min-w-0 flex-1">
              <p
                className={cn(
                  "text-sm leading-5 break-words text-slate-800",
                  todo.status === "completed" &&
                    "text-slate-500 line-through decoration-slate-300",
                  todo.status === "in_progress" && "font-medium text-slate-900",
                )}
              >
                {todo.content}
              </p>
              <span
                className={cn(
                  "mt-1.5 inline-flex rounded px-1.5 py-0.5 text-[10px] font-medium tracking-wide",
                  details.className,
                )}
              >
                {details.label}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}

export function TodoPanel({
  variant = "desktop",
}: {
  variant?: "desktop" | "mobile";
}) {
  const todos = useStreamContext().values?.todos ?? [];
  const completed = todos.filter((t) => t.status === "completed").length;

  if (variant === "mobile") {
    return (
      <details className="group mx-4 mb-2 rounded-xl border border-slate-200 bg-white shadow-xs lg:hidden">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold text-slate-800 [&::-webkit-details-marker]:hidden">
          <ListTodo className="size-4 text-slate-500" />
          <span>待办事项</span>
          <span className="ml-auto text-xs font-normal text-slate-500">
            {todos.length === 0 ? "0" : `${completed}/${todos.length}`}
          </span>
          <ChevronDown className="size-4 text-slate-400 transition-transform group-open:rotate-180" />
        </summary>
        <div className="max-h-64 overflow-y-auto border-t border-slate-100">
          <ProgressSummary todos={todos} />
          <TodoList todos={todos} />
        </div>
      </details>
    );
  }

  return (
    <aside
      aria-label="待办事项"
      className="flex h-full min-h-0 w-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xs"
    >
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-3">
        <ListTodo className="size-4 text-slate-600" />
        <h2 className="text-sm font-semibold text-slate-800">待办事项</h2>
        <span className="ml-auto rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-medium tabular-nums text-slate-600">
          {todos.length === 0 ? "0" : `${completed}/${todos.length}`}
        </span>
      </div>
      <ProgressSummary todos={todos} />
      <div className="min-h-0 flex-1 overflow-y-auto">
        <TodoList todos={todos} />
      </div>
    </aside>
  );
}
