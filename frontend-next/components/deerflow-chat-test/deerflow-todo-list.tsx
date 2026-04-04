import { ChevronUpIcon, ListTodoIcon } from "lucide-react";
import { useState } from "react";

import type { DeerFlowTodo } from "@/components/deerflow-chat-test/deerflow-thread-context";
import { cn } from "@/lib/utils";

/**
 * DeerFlowTodoList - 官方风格 To-dos 面板
 */
export function DeerFlowTodoList({
  className,
  todos,
  hidden = false,
  /** 与下方输入区同处一层圆角外壳内：去掉自身圆角/边框，头栏底边直角贴输入区（对齐官方一体卡片） */
  combinedCardStack = false,
}: {
  className?: string;
  todos: DeerFlowTodo[];
  hidden?: boolean;
  combinedCardStack?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(true);

  /** 无待办时不占位，避免输入区与空白面板叠层（与官方聊天区纵向排布一致）。 */
  if (hidden) {
    return null;
  }

  return (
    <div
      className={cn(
        "flex w-full flex-col overflow-hidden",
        combinedCardStack
          ? "rounded-none border-0 bg-transparent shadow-none"
          : "rounded-t-xl border border-black/10 border-b-0 bg-white shadow-sm",
        className
      )}
    >
      <header
        className={cn(
          "flex min-h-9 shrink-0 cursor-pointer select-none items-center justify-between bg-[#efeee6] px-4 text-sm",
          combinedCardStack ? "rounded-none" : "rounded-t-[inherit]"
        )}
        onClick={() => setCollapsed((previousState) => !previousState)}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            setCollapsed((previousState) => !previousState);
          }
        }}
        role="button"
        tabIndex={0}
        aria-expanded={!collapsed}
      >
        <div className="text-slate-600">
          <div className="flex items-center justify-center gap-2">
            <ListTodoIcon className="size-4 shrink-0" aria-hidden />
            <span>To-dos</span>
          </div>
        </div>
        <ChevronUpIcon
          className={cn(
            "size-4 shrink-0 text-slate-500 transition-transform duration-300 ease-out",
            collapsed ? "" : "rotate-180"
          )}
          aria-hidden
        />
      </header>

      {/*
        使用 grid-template-rows 0fr/1fr 折叠，避免 flex grow + h-0 与 pb-3 导致条带、滚动条露边。
      */}
      <div
        className={cn(
          "grid transition-[grid-template-rows] duration-300 ease-out motion-reduce:transition-none",
          collapsed ? "grid-rows-[0fr]" : "grid-rows-[1fr]"
        )}
      >
        <div className="min-h-0 overflow-hidden">
          <div className="box-border max-h-52 bg-[#efeee6] px-2 pb-3 pt-0">
            <div className="max-h-44 min-h-0 w-full overflow-y-auto overscroll-contain rounded-t-xl bg-white px-3 py-2">
              <ul className="m-0 list-none space-y-2 p-0">
                {todos.map((todo) => (
                  <li key={todo.id} className="flex items-start gap-2 text-sm">
                    <span
                      className={cn(
                        "mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full border border-black/10",
                        todo.status === "completed"
                          ? "bg-emerald-500"
                          : todo.status === "in_progress"
                            ? "bg-sky-500"
                            : "bg-slate-200"
                      )}
                    />
                    <span
                      className={cn(
                        "min-w-0 break-words",
                        todo.status === "completed" && "text-slate-400 line-through",
                        todo.status === "in_progress" && "text-sky-700"
                      )}
                    >
                      {todo.content}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
