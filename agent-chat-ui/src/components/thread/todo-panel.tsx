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
  { label: string; className: string }
> = {
  pending: {
    label: "待处理",
    className: "bg-slate-100 text-slate-600",
  },
  in_progress: {
    label: "进行中",
    className: "bg-amber-100 text-amber-700",
  },
  completed: {
    label: "已完成",
    className: "bg-emerald-100 text-emerald-700",
  },
};

function StatusIcon({ status }: { status: TodoItem["status"] }) {
  if (status === "completed") {
    return <CheckCircle2 className="size-4 text-emerald-600" />;
  }
  if (status === "in_progress") {
    return <LoaderCircle className="size-4 animate-spin text-amber-600" />;
  }
  return <Circle className="size-4 text-slate-400" />;
}

function TodoList({ todos }: { todos: TodoItem[] }) {
  if (todos.length === 0) {
    return (
      <p className="px-4 py-6 text-center text-sm text-slate-500">暂无待办</p>
    );
  }

  return (
    <ul className="divide-y divide-slate-100">
      {todos.map((todo, index) => {
        const details = statusDetails[todo.status];
        return (
          <li
            key={`${todo.content}-${index}`}
            className="flex items-start gap-3 px-4 py-3"
          >
            <span className="mt-0.5 shrink-0">
              <StatusIcon status={todo.status} />
            </span>
            <div className="min-w-0 flex-1">
              <p
                className={cn(
                  "text-sm leading-5 break-words text-slate-800",
                  todo.status === "completed" &&
                    "text-slate-500 line-through decoration-slate-300",
                )}
              >
                {todo.content}
              </p>
              <span
                className={cn(
                  "mt-1.5 inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium",
                  details.className,
                )}
              >
                {details.label}
              </span>
            </div>
          </li>
        );
      })}
    </ul>
  );
}

export function TodoPanel({
  variant = "desktop",
}: {
  variant?: "desktop" | "mobile";
}) {
  const todos = useStreamContext().values?.todos ?? [];

  if (variant === "mobile") {
    return (
      <details className="group mx-4 mb-2 rounded-xl border border-slate-200 bg-white shadow-xs lg:hidden">
        <summary className="flex cursor-pointer list-none items-center gap-2 px-4 py-3 text-sm font-semibold text-slate-800 [&::-webkit-details-marker]:hidden">
          <ListTodo className="size-4 text-slate-500" />
          <span>待办事项</span>
          <span className="ml-auto text-xs font-normal text-slate-500">
            {todos.length}
          </span>
          <ChevronDown className="size-4 text-slate-400 transition-transform group-open:rotate-180" />
        </summary>
        <div className="max-h-56 overflow-y-auto border-t border-slate-100">
          <TodoList todos={todos} />
        </div>
      </details>
    );
  }

  return (
    <aside
      aria-label="待办事项"
      className="hidden w-72 shrink-0 flex-col border-l border-slate-200 bg-slate-50/70 lg:flex"
    >
      <div className="flex items-center gap-2 border-b border-slate-200 px-4 py-4">
        <ListTodo className="size-4 text-slate-500" />
        <h2 className="text-sm font-semibold text-slate-800">待办事项</h2>
        <span className="ml-auto text-xs text-slate-500">{todos.length}</span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <TodoList todos={todos} />
      </div>
    </aside>
  );
}
