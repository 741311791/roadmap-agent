"use client";

import { useTranslations } from "next-intl";

import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  MENTOR_AGENT_OPTIONS,
  MENTOR_MODEL_OPTIONS,
  type MentorAgentType,
} from "@/components/mentor/types";

interface MentorToolbarProps {
  agentType: MentorAgentType;
  modelId: string;
  onAgentChange: (agentType: MentorAgentType) => void;
  onModelChange: (modelId: string) => void;
}

/**
 * MentorToolbar - 侧栏底部工具栏，仅保留 Agent 与模型选择
 */
export function MentorToolbar({
  agentType,
  modelId,
  onAgentChange,
  onModelChange,
}: MentorToolbarProps) {
  const t = useTranslations("mentor");

  return (
    <div className="flex items-center gap-2">
      <Select value={agentType} onValueChange={(value) => onAgentChange(value as MentorAgentType)}>
        <SelectTrigger className="h-8 rounded-lg border-transparent bg-transparent hover:bg-slate-100 text-xs shadow-none px-2.5 w-auto gap-1.5 focus:ring-0 focus:ring-offset-0 transition-colors">
          <SelectValue placeholder={t("agent")} />
        </SelectTrigger>
        <SelectContent>
          {MENTOR_AGENT_OPTIONS.map((agent) => (
            <SelectItem key={agent.id} value={agent.id} className="text-xs">
              {agent.id === "company" ? t("agentCompany") : t("agentTutoring")}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={modelId} onValueChange={onModelChange}>
        <SelectTrigger className="h-8 rounded-lg border-transparent bg-transparent hover:bg-slate-100 text-xs shadow-none px-2.5 w-auto gap-1.5 focus:ring-0 focus:ring-offset-0 transition-colors">
          <SelectValue placeholder={t("model")} />
        </SelectTrigger>
        <SelectContent>
          {MENTOR_MODEL_OPTIONS.map((model) => (
            <SelectItem key={model.id} value={model.id} className="text-xs">
              <div className="flex w-full items-center justify-between gap-2">
                <span>{model.label}</span>
                {model.isLimitedFree ? (
                  <Badge
                    variant="secondary"
                    className="border border-emerald-200 bg-emerald-50 text-[9px] px-1 py-0 h-4 text-emerald-700"
                  >
                    {t("freeLimited")}
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
