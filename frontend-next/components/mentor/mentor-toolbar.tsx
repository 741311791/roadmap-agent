"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  QA_STYLE_OPTIONS,
  type MentorAgentKind,
  type MentorModelOption,
  type MentorQaStyle,
} from "@/components/mentor/types";

interface MentorToolbarProps {
  agentKind: MentorAgentKind;
  qaStyle: MentorQaStyle;
  modelId: string;
  modelOptions: MentorModelOption[];
  isLoading?: boolean;
  onAgentKindChange: (agentKind: MentorAgentKind) => void;
  onQaStyleChange: (qaStyle: MentorQaStyle) => void;
  onModelChange: (modelId: string) => void;
}

/**
 * MentorToolbar - 侧栏底部工具栏，仅保留 Agent 与模型选择
 */
export function MentorToolbar({
  agentKind,
  qaStyle,
  modelId,
  modelOptions,
  isLoading = false,
  onAgentKindChange,
  onQaStyleChange,
  onModelChange,
}: MentorToolbarProps) {
  const t = useTranslations("mentor");

  return (
    <div className="flex items-center gap-2">
      <div className="inline-flex items-center rounded-lg border border-slate-200 bg-slate-50 p-0.5">
        {([
          { id: "qa", label: "Answer" },
          { id: "guide", label: "Guide" },
          { id: "quiz", label: "Quiz" },
        ] as const).map((item) => (
          <Button
            key={item.id}
            type="button"
            variant="ghost"
            size="sm"
            disabled={isLoading}
            className={
              agentKind === item.id
                ? "h-7 rounded-md bg-white px-2 text-xs text-slate-900 shadow-sm"
                : "h-7 rounded-md px-2 text-xs text-slate-500 hover:text-slate-900"
            }
            onClick={() => onAgentKindChange(item.id)}
          >
            {item.label}
          </Button>
        ))}
      </div>

      {agentKind === "qa" ? (
        <Select value={qaStyle} onValueChange={(value) => onQaStyleChange(value as MentorQaStyle)} disabled={isLoading}>
          <SelectTrigger className="h-8 rounded-lg border-transparent bg-transparent hover:bg-slate-100 text-xs shadow-none px-2.5 w-auto gap-1.5 focus:ring-0 focus:ring-offset-0 transition-colors">
            <SelectValue placeholder="Style" />
          </SelectTrigger>
          <SelectContent>
            {QA_STYLE_OPTIONS.map((style) => (
              <SelectItem key={style.id} value={style.id} className="text-xs">
                {style.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      ) : null}

      <Select value={modelId} onValueChange={onModelChange} disabled={isLoading || modelOptions.length === 0}>
        <SelectTrigger className="h-8 rounded-lg border-transparent bg-transparent hover:bg-slate-100 text-xs shadow-none px-2.5 w-auto gap-1.5 focus:ring-0 focus:ring-offset-0 transition-colors">
          <SelectValue placeholder={t("model")} />
        </SelectTrigger>
        <SelectContent>
          {modelOptions.map((model) => (
            <SelectItem key={model.id} value={model.id} className="text-xs">
              <div className="flex w-full items-center justify-between gap-2">
                <span>{model.label}</span>
                {model.isUnavailable ? (
                  <Badge
                    variant="secondary"
                    className="border border-amber-200 bg-amber-50 text-[9px] px-1 py-0 h-4 text-amber-700"
                  >
                    Unavailable
                  </Badge>
                ) : model.isDefault ? (
                  <Badge
                    variant="secondary"
                    className="border border-emerald-200 bg-emerald-50 text-[9px] px-1 py-0 h-4 text-emerald-700"
                  >
                    Default
                  </Badge>
                ) : null}
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
