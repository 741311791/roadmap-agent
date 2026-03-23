"use client";

import { useState } from "react";
import { Bot } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { Concept } from "@/types/generated/models";
import { MentorSidebar } from "@/components/mentor/mentor-sidebar";

const mockConcept: Concept = {
  concept_id: "react-effects",
  name: "React Effects and Dependencies",
  description: "Learn when side effects run and how dependency arrays affect re-renders.",
  estimated_hours: 3,
  prerequisites: ["react-state"],
  difficulty: "medium",
  keywords: ["react", "useEffect", "dependencies"],
  content_status: "completed",
  content_ref: null,
  content_version: "v1",
  content_summary:
    "Understand how React compares dependencies, reruns effects, and avoids stale values.",
  tutorial_id: "tutorial-react-effects",
  resources_status: "completed",
  resources_id: null,
  resources_count: 2,
  quiz_status: "completed",
  quiz_id: null,
  quiz_questions_count: 4,
};

/**
 * MentorSidebarDemoPage - 独立的 mock 预览页，用于浏览器交互测试
 */
export default function MentorSidebarDemoPage() {
  const [isCollapsed, setIsCollapsed] = useState(false);

  return (
    <main className="flex h-screen bg-slate-100">
      <section className="flex-1 overflow-y-auto px-10 py-12">
        <div className="mx-auto max-w-4xl rounded-[32px] border border-border/60 bg-white p-10 shadow-sm">
          <div className="inline-flex rounded-full bg-slate-950 px-3 py-1 text-xs font-medium text-white">
            Mock roadmap detail
          </div>
          <h1 className="mt-6 text-4xl font-semibold tracking-tight text-slate-950">
            React Effects and Dependencies
          </h1>
          <p className="mt-4 max-w-3xl text-base leading-8 text-slate-600">
            This preview page exists only so the new mentor sidebar can be tested
            with mock data in a browser. You can send questions, switch agents,
            change models, open thread history, and create fresh threads without
            depending on backend chat APIs.
          </p>

          <div className="mt-8 space-y-6">
            <section className="rounded-3xl bg-slate-50 p-6">
              <h2 className="text-lg font-semibold text-slate-900">
                What to ask in this mock chapter
              </h2>
              <ul className="mt-4 space-y-3 text-sm leading-7 text-slate-600">
                <li>Why does an effect rerun after a dependency changes?</li>
                <li>How is a stale closure different from stale data?</li>
                <li>When should I split one effect into two separate effects?</li>
              </ul>
            </section>

            <section className="rounded-3xl border border-dashed border-border/70 p-6">
              <h2 className="text-lg font-semibold text-slate-900">
                Current chapter summary
              </h2>
              <p className="mt-4 text-sm leading-7 text-slate-600">
                Effects help React synchronize with things outside rendering.
                The dependency array tells React when the synchronization should
                be re-checked, while missing dependencies often lead to stale
                behavior or invisible bugs.
              </p>
            </section>
          </div>
        </div>
      </section>

      <aside 
        className={cn(
          "hidden h-screen shrink-0 xl:block transition-all duration-300",
          isCollapsed ? "w-0 overflow-hidden" : "w-[420px]"
        )}
      >
        <MentorSidebar 
          roadmapId="mock-roadmap-react" 
          activeConcept={mockConcept} 
          onCollapse={() => setIsCollapsed(true)}
        />
      </aside>

      {isCollapsed && (
        <Button
          variant="outline"
          size="icon"
          className="fixed right-4 top-4 z-50 rounded-full shadow-md bg-white/90 backdrop-blur-sm border-border/60 hover:bg-slate-50 hidden xl:flex"
          onClick={() => setIsCollapsed(false)}
        >
          <Bot className="h-5 w-5 text-slate-700" />
        </Button>
      )}
    </main>
  );
}
