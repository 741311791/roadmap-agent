"use client";

import type { ChatStatus } from "ai";
import {
  CheckIcon,
  GraduationCapIcon,
  LightbulbIcon,
  Loader2Icon,
  PaperclipIcon,
  PlusIcon,
  RocketIcon,
  SparklesIcon,
  XIcon,
  ZapIcon,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  ModelSelector,
  ModelSelectorContent,
  ModelSelectorInput,
  ModelSelectorItem,
  ModelSelectorList,
  ModelSelectorLogo,
  ModelSelectorName,
  ModelSelectorTrigger,
} from "@/components/deerflow-native/ai-elements/model-selector";
import {
  PromptInput,
  PromptInputActionMenu,
  PromptInputActionMenuContent,
  PromptInputActionMenuItem,
  PromptInputActionMenuTrigger,
  PromptInputAttachment,
  PromptInputAttachments,
  PromptInputBody,
  PromptInputButton,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
  usePromptInputController,
  usePromptInputAttachments,
  type PromptInputMessage,
} from "@/components/deerflow-native/ai-elements/prompt-input";
import { DeerFlowWelcome } from "@/components/deerflow-chat-test/deerflow-welcome";
import type { MentorModelDto } from "@/components/mentor/mentor-deerflow-api";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";

export type DeerFlowInputMode = "flash" | "thinking" | "pro" | "ultra";

/**
 * 输入框属性。
 */
interface DeerFlowInputBoxProps {
  status: ChatStatus;
  autoFocus?: boolean;
  disabled?: boolean;
  isModelsLoading?: boolean;
  models: MentorModelDto[];
  selectedModelId: string;
  onModelChange: (modelId: string) => void;
  mode: DeerFlowInputMode;
  onModeChange: (mode: DeerFlowInputMode) => void;
  isNewThread?: boolean;
  followupSuggestions?: string[];
  isFollowupsLoading?: boolean;
  onStop?: () => void;
  onFollowupClick?: (suggestion: string) => void;
  onDismissFollowups?: () => void;
  onSubmit: (message: PromptInputMessage) => void | Promise<void>;
  /** 为 true 时与上方 To-dos 同属一块圆角卡片：去掉顶圆角与独立边框/阴影 */
  isDockedWithTodosAbove?: boolean;
}

/** 与独立输入框外轮廓一致，供测试页 To-dos + 输入区一体包裹 */
export const DEERFLOW_INPUT_OUTER_CARD_CLASSNAME =
  "overflow-hidden rounded-[22px] border border-black/[0.08] bg-white shadow-[0_12px_40px_-24px_rgba(15,23,42,0.2)] transition-all duration-300 ease-out";

const MODE_LABELS: Record<DeerFlowInputMode, string> = {
  flash: "闪速",
  thinking: "思考",
  pro: "Pro",
  ultra: "Ultra",
};

const MODE_DESCRIPTIONS: Record<DeerFlowInputMode, string> = {
  flash: "快速且高效的完成任务，但可能不够精准",
  thinking: "思考后再行动，在时间与准确性之间取得平衡",
  pro: "思考、计划再执行，获得更精准的结果，可能需要更多时间",
  ultra: "继承自 Pro 模式，可调用子代理分工协作，适合复杂多步骤任务，能力最强",
};

/** 下拉选中态：必须与 bg-accent 成对使用，否则 accent-foreground 与 popover 底色同为浅色会不可读 */
const MODE_MENU_ITEM_SELECTED = "bg-accent text-accent-foreground";
const MODE_MENU_ITEM_NORMAL = "text-muted-foreground/70";

function resolveModeIcon(mode: DeerFlowInputMode) {
  if (mode === "flash") {
    return <ZapIcon className="size-3" />;
  }
  if (mode === "thinking") {
    return <LightbulbIcon className="size-3" />;
  }
  if (mode === "pro") {
    return <GraduationCapIcon className="size-3" />;
  }
  return <RocketIcon className="size-3 text-[#dabb5e]" />;
}

function getResolvedMode(
  mode: DeerFlowInputMode,
  supportsThinking: boolean
): DeerFlowInputMode {
  if (!supportsThinking && mode !== "flash") {
    return "flash";
  }
  return mode;
}

/**
 * Deer-Flow 风格输入框。
 */
export function DeerFlowInputBox({
  status,
  autoFocus = false,
  disabled = false,
  isModelsLoading = false,
  models,
  selectedModelId,
  onModelChange,
  mode,
  onModeChange,
  isNewThread = false,
  followupSuggestions = [],
  isFollowupsLoading = false,
  onStop,
  onFollowupClick,
  onDismissFollowups,
  onSubmit,
  isDockedWithTodosAbove = false,
}: DeerFlowInputBoxProps) {
  return (
    <PromptInputProvider>
      <DeerFlowInputBoxInner
        status={status}
        autoFocus={autoFocus}
        disabled={disabled}
        isModelsLoading={isModelsLoading}
        models={models}
        selectedModelId={selectedModelId}
        onModelChange={onModelChange}
        mode={mode}
        onModeChange={onModeChange}
        isNewThread={isNewThread}
        followupSuggestions={followupSuggestions}
        isFollowupsLoading={isFollowupsLoading}
        onStop={onStop}
        onFollowupClick={onFollowupClick}
        onDismissFollowups={onDismissFollowups}
        onSubmit={onSubmit}
        isDockedWithTodosAbove={isDockedWithTodosAbove}
      />
    </PromptInputProvider>
  );
}

/**
 * DeerFlowInputBoxInner - 真实输入框实现
 */
function DeerFlowInputBoxInner({
  status,
  autoFocus = false,
  disabled = false,
  isModelsLoading = false,
  models,
  selectedModelId,
  onModelChange,
  mode,
  onModeChange,
  isNewThread = false,
  followupSuggestions = [],
  isFollowupsLoading = false,
  onStop,
  onFollowupClick,
  onDismissFollowups,
  onSubmit,
  isDockedWithTodosAbove = false,
}: DeerFlowInputBoxProps) {
  const [isModelSelectorOpen, setIsModelSelectorOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingSuggestion, setPendingSuggestion] = useState<string | null>(null);
  const promptRootRef = useRef<HTMLDivElement | null>(null);
  const { textInput } = usePromptInputController();
  const selectedModel =
    models.find((model) => model.model_id === selectedModelId) ?? models[0] ?? null;
  const supportsThinking = selectedModel?.supports_thinking ?? false;
  const visibleMode = useMemo(
    () => getResolvedMode(mode, supportsThinking),
    [mode, supportsThinking]
  );
  const displaySuggestions = isNewThread ? DEFAULT_SUGGESTIONS : followupSuggestions;

  /**
   * 与官方一致：textarea 在 absolute 层，InputGroup 在仅有 footer 时高度塌缩会导致工具栏盖住输入区。
   * 为 [data-slot=input-group] 预留最小高度，保证可点击、可聚焦。
   */
  useEffect(() => {
    if (!autoFocus || disabled) {
      return;
    }
    const id = window.requestAnimationFrame(() => {
      const textarea = promptRootRef.current?.querySelector<HTMLTextAreaElement>(
        "textarea[name='message']",
      );
      textarea?.focus({ preventScroll: true });
    });
    return () => window.cancelAnimationFrame(id);
  }, [autoFocus, disabled, status]);

  /**
   * requestFormSubmit - 触发内部表单提交
   */
  const requestFormSubmit = useCallback(() => {
    const form = promptRootRef.current?.querySelector("form");
    form?.requestSubmit();
  }, []);

  /**
   * handleSubmit - 包装 Deer-Flow 输入框提交行为
   */
  const handleSubmit = useCallback(
    async (message: PromptInputMessage) => {
      if (status === "submitted" || status === "streaming") {
        onStop?.();
        return;
      }

      if (!message.text.trim() && message.files.length === 0) {
        return;
      }

      await onSubmit(message);
    },
    [onStop, onSubmit, status]
  );

  /**
   * handleSuggestionClick - 处理首屏建议与追问建议点击
   */
  const handleSuggestionClick = useCallback(
    (suggestion: string) => {
      if (status === "submitted" || status === "streaming") {
        return;
      }

      const currentValue = textInput.value.trim();
      if (currentValue) {
        setPendingSuggestion(suggestion);
        setConfirmOpen(true);
        return;
      }

      textInput.setInput(suggestion);
      onFollowupClick?.(suggestion);
      window.setTimeout(() => requestFormSubmit(), 0);
    },
    [onFollowupClick, requestFormSubmit, status, textInput]
  );

  /**
   * confirmReplaceAndSend - 替换输入框内容并自动发送
   */
  const confirmReplaceAndSend = useCallback(() => {
    if (!pendingSuggestion) {
      setConfirmOpen(false);
      return;
    }

    textInput.setInput(pendingSuggestion);
    onFollowupClick?.(pendingSuggestion);
    setPendingSuggestion(null);
    setConfirmOpen(false);
    window.setTimeout(() => requestFormSubmit(), 0);
  }, [onFollowupClick, pendingSuggestion, requestFormSubmit, textInput]);

  /**
   * confirmAppendAndSend - 在原输入后追加建议并自动发送
   */
  const confirmAppendAndSend = useCallback(() => {
    if (!pendingSuggestion) {
      setConfirmOpen(false);
      return;
    }

    const currentValue = textInput.value.trim();
    textInput.setInput(currentValue ? `${currentValue}\n${pendingSuggestion}` : pendingSuggestion);
    onFollowupClick?.(pendingSuggestion);
    setPendingSuggestion(null);
    setConfirmOpen(false);
    window.setTimeout(() => requestFormSubmit(), 0);
  }, [onFollowupClick, pendingSuggestion, requestFormSubmit, textInput]);

  return (
    <div ref={promptRootRef} className="relative w-full">
      {isNewThread ? <DeerFlowWelcome className="mb-10" /> : null}
      <PromptInput
        className={cn(
          "overflow-hidden bg-white",
          isDockedWithTodosAbove
            ? "rounded-none border-0 shadow-none transition-all duration-300 ease-out"
            : DEERFLOW_INPUT_OUTER_CARD_CLASSNAME,
          "[&_[data-slot=input-group]]:min-h-[168px] [&_[data-slot=input-group]]:rounded-none [&_[data-slot=input-group]]:border-0 [&_[data-slot=input-group]]:bg-transparent [&_[data-slot=input-group]]:shadow-none"
        )}
        disabled={disabled}
        globalDrop
        multiple
        onSubmit={handleSubmit}
      >
        <PromptInputAttachments>
          {(attachment) => <PromptInputAttachment data={attachment} />}
        </PromptInputAttachments>
        <PromptInputBody className="contents absolute top-0 right-0 left-0 z-[3]">
          <PromptInputTextarea
            autoFocus={autoFocus}
            className="min-h-[108px] size-full px-5 py-4 text-[15px] leading-6 text-slate-900 placeholder:text-slate-400"
            disabled={disabled}
            placeholder="今天我能为你做些什么？"
          />
        </PromptInputBody>
        <PromptInputFooter className="px-2 pb-4 pt-1">
          <PromptInputTools>
            <AddAttachmentsButton />
            <PromptInputActionMenu>
              <PromptInputActionMenuTrigger className="gap-1 px-2">
                {resolveModeIcon(visibleMode)}
                <span
                  className={cn(
                    "text-xs font-normal",
                    visibleMode === "ultra" && "text-[#b8962e]"
                  )}
                >
                  {MODE_LABELS[visibleMode]}
                </span>
              </PromptInputActionMenuTrigger>
              <PromptInputActionMenuContent className="w-80">
                <div className="px-2 py-1 text-xs font-medium text-muted-foreground">
                  Mode
                </div>
                <PromptInputActionMenuItem
                  className={cn(
                    visibleMode === "flash" ? MODE_MENU_ITEM_SELECTED : MODE_MENU_ITEM_NORMAL
                  )}
                  onSelect={() => {
                    onModeChange("flash");
                  }}
                >
                  <div className="flex flex-1 flex-col gap-2">
                    <div className="flex items-center gap-2 font-bold">
                      <ZapIcon className="size-4" />
                      {MODE_LABELS.flash}
                    </div>
                    <div className="pl-6 text-xs">{MODE_DESCRIPTIONS.flash}</div>
                  </div>
                  {visibleMode === "flash" ? (
                    <CheckIcon className="ml-auto size-4" />
                  ) : (
                    <div className="ml-auto size-4" />
                  )}
                </PromptInputActionMenuItem>
                {supportsThinking ? (
                  <PromptInputActionMenuItem
                    className={cn(
                      visibleMode === "thinking"
                        ? MODE_MENU_ITEM_SELECTED
                        : MODE_MENU_ITEM_NORMAL
                    )}
                    onSelect={() => {
                      onModeChange("thinking");
                    }}
                  >
                    <div className="flex flex-1 flex-col gap-2">
                      <div className="flex items-center gap-2 font-bold">
                        <LightbulbIcon className="size-4" />
                        {MODE_LABELS.thinking}
                      </div>
                      <div className="pl-6 text-xs">{MODE_DESCRIPTIONS.thinking}</div>
                    </div>
                    {visibleMode === "thinking" ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </PromptInputActionMenuItem>
                ) : null}
                {supportsThinking ? (
                  <PromptInputActionMenuItem
                    className={cn(
                      visibleMode === "pro" ? MODE_MENU_ITEM_SELECTED : MODE_MENU_ITEM_NORMAL
                    )}
                    onSelect={() => {
                      onModeChange("pro");
                    }}
                  >
                    <div className="flex flex-1 flex-col gap-2">
                      <div className="flex items-center gap-2 font-bold">
                        <GraduationCapIcon className="size-4" />
                        {MODE_LABELS.pro}
                      </div>
                      <div className="pl-6 text-xs">{MODE_DESCRIPTIONS.pro}</div>
                    </div>
                    {visibleMode === "pro" ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </PromptInputActionMenuItem>
                ) : null}
                {supportsThinking ? (
                  <PromptInputActionMenuItem
                    className={cn(
                      visibleMode === "ultra" ? MODE_MENU_ITEM_SELECTED : MODE_MENU_ITEM_NORMAL
                    )}
                    onSelect={() => {
                      onModeChange("ultra");
                    }}
                  >
                    <div className="flex flex-1 flex-col gap-2">
                      <div className="flex items-center gap-2 font-bold">
                        <RocketIcon className="size-4 text-[#dabb5e]" />
                        <span className="text-[#b8962e]">{MODE_LABELS.ultra}</span>
                      </div>
                      <div className="pl-6 text-xs">{MODE_DESCRIPTIONS.ultra}</div>
                    </div>
                    {visibleMode === "ultra" ? (
                      <CheckIcon className="ml-auto size-4" />
                    ) : (
                      <div className="ml-auto size-4" />
                    )}
                  </PromptInputActionMenuItem>
                ) : null}
              </PromptInputActionMenuContent>
            </PromptInputActionMenu>
          </PromptInputTools>
          <PromptInputTools>
            <ModelSelector open={isModelSelectorOpen} onOpenChange={setIsModelSelectorOpen}>
              <ModelSelectorTrigger asChild>
                <PromptInputButton
                  className="px-2 text-[13px] font-normal text-slate-500 hover:text-slate-700"
                  variant="ghost"
                >
                  {isModelsLoading ? (
                    <>
                      <Loader2Icon className="mr-2 size-3 animate-spin" />
                      Loading model...
                    </>
                  ) : (
                    <>
                      {selectedModel?.display_name ? (
                        <ModelSelectorLogo
                          className="mr-2 size-5 opacity-90"
                          displayName={selectedModel.display_name}
                        />
                      ) : null}
                      <span className="max-w-[14rem] truncate">
                        {selectedModel?.display_name || "Select model"}
                      </span>
                    </>
                  )}
                </PromptInputButton>
              </ModelSelectorTrigger>
              <ModelSelectorContent className="sm:max-w-lg">
                <ModelSelectorInput placeholder="Search models..." />
                <ModelSelectorList className="max-h-[min(420px,52vh)] scroll-py-2 p-2">
                  {models.length === 0 ? (
                    <div className="px-3 py-8 text-center text-sm text-muted-foreground">
                      No visible Deer-Flow models.
                    </div>
                  ) : null}
                  {models.map((model) => {
                    const isChosen = model.model_id === selectedModelId;
                    return (
                      <ModelSelectorItem
                        key={model.model_id}
                        className={cn(
                          "mb-1 rounded-xl border border-transparent px-3 py-2.5 last:mb-0",
                          "data-[selected=true]:bg-muted/75",
                          isChosen &&
                            "border-primary/20 bg-primary/[0.07] data-[selected=true]:bg-primary/[0.11]"
                        )}
                        value={`${model.display_name} ${model.provider}`}
                        onSelect={() => {
                          onModelChange(model.model_id);
                          setIsModelSelectorOpen(false);
                        }}
                      >
                        <div className="flex min-w-0 flex-1 items-center gap-3">
                          <ModelSelectorLogo displayName={model.display_name} />
                          <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                            <ModelSelectorName className="text-[13px] font-medium leading-tight">
                              {model.display_name}
                            </ModelSelectorName>
                            <span
                              className={cn(
                                "truncate text-[11px] leading-tight",
                                isChosen ? "text-foreground/55" : "text-muted-foreground"
                              )}
                            >
                              {model.provider}
                            </span>
                          </div>
                        </div>
                        {isChosen ? (
                          <CheckIcon className="ml-auto size-4 shrink-0 text-primary" />
                        ) : (
                          <span className="ml-auto size-4 shrink-0" aria-hidden />
                        )}
                      </ModelSelectorItem>
                    );
                  })}
                </ModelSelectorList>
              </ModelSelectorContent>
            </ModelSelector>
            <PromptInputSubmit
              className="size-9 shrink-0 rounded-full border-0 bg-slate-100 text-slate-700 shadow-none hover:bg-slate-200/90 hover:text-slate-800"
              disabled={disabled}
              status={status}
              variant="outline"
            />
          </PromptInputTools>
        </PromptInputFooter>
      </PromptInput>

      {displaySuggestions.length > 0 ? (
        <div
          className={cn(
            "flex items-center justify-center",
            isNewThread ? "mt-8" : "mt-4"
          )}
        >
          <DeerFlowSuggestionRow
            isLoading={isFollowupsLoading}
            isNewThread={isNewThread}
            onDismiss={onDismissFollowups}
            onSuggestionClick={handleSuggestionClick}
            suggestions={displaySuggestions}
          />
        </div>
      ) : null}

      <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Use this follow-up?</DialogTitle>
            <DialogDescription>
              Your current draft is not empty. You can replace it or append the selected follow-up
              before sending.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="secondary" onClick={confirmAppendAndSend}>
              Append
            </Button>
            <Button onClick={confirmReplaceAndSend}>Replace</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

const DEFAULT_SUGGESTIONS = [
  "帮我分析一个复杂问题。",
  "先搜索资料再给我结论。",
  "给我一个可执行的计划。",
];

/**
 * 打开附件选择器按钮。
 */
function AddAttachmentsButton() {
  const attachments = usePromptInputAttachments();

  return (
    <PromptInputButton className="px-2" onClick={() => attachments.openFileDialog()}>
      <PaperclipIcon className="size-3" />
    </PromptInputButton>
  );
}

/**
 * DeerFlowSuggestionRow - 首屏建议与追问建议行
 */
function DeerFlowSuggestionRow({
  suggestions,
  isLoading,
  isNewThread,
  onSuggestionClick,
  onDismiss,
}: {
  suggestions: string[];
  isLoading: boolean;
  isNewThread: boolean;
  onSuggestionClick: (suggestion: string) => void;
  onDismiss?: () => void;
}) {
  if (isLoading && !isNewThread) {
    return (
      <div className="rounded-full border border-slate-200/80 bg-white/85 px-4 py-2 text-xs text-slate-500 shadow-sm backdrop-blur">
        Generating follow-up suggestions...
      </div>
    );
  }

  if (suggestions.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center justify-center gap-2">
      {isNewThread ? (
        <Button
          className="rounded-full border-black/[0.08] bg-white px-4 text-xs font-normal text-slate-600 shadow-[0_1px_2px_rgba(15,23,42,0.04)] hover:bg-white"
          onClick={() => onSuggestionClick("给我一个有趣但实用的研究任务。")}
          size="sm"
          type="button"
          variant="outline"
        >
          <SparklesIcon className="mr-1.5 size-4" />
          Surprise me
        </Button>
      ) : null}
      {suggestions.map((suggestion) => (
        <Button
          key={suggestion}
          className="rounded-full border-black/[0.08] bg-white px-4 text-xs font-normal text-slate-600 shadow-[0_1px_2px_rgba(15,23,42,0.04)] hover:bg-white"
          onClick={() => onSuggestionClick(suggestion)}
          size="sm"
          type="button"
          variant="outline"
        >
          {suggestion}
        </Button>
      ))}
      {isNewThread ? (
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button
              className="rounded-full border-black/[0.08] bg-white px-4 text-xs font-normal text-slate-600 shadow-[0_1px_2px_rgba(15,23,42,0.04)] hover:bg-white"
              size="sm"
              type="button"
              variant="outline"
            >
              <PlusIcon className="mr-1.5 size-4" />
              Create
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuGroup>
              {DEFAULT_CREATE_SUGGESTIONS.map((suggestion) =>
                suggestion === "---" ? (
                  <DropdownMenuSeparator key={suggestion} />
                ) : (
                  <DropdownMenuItem
                    key={suggestion}
                    onClick={() => onSuggestionClick(suggestion)}
                  >
                    {suggestion}
                  </DropdownMenuItem>
                )
              )}
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      ) : onDismiss ? (
        <Button
          className="rounded-full px-3 text-xs text-slate-500"
          onClick={onDismiss}
          size="sm"
          type="button"
          variant="outline"
        >
          <XIcon className="size-4" />
        </Button>
      ) : null}
    </div>
  );
}

const DEFAULT_CREATE_SUGGESTIONS = [
  "创建一份研究报告提纲。",
  "创建一个分步骤执行计划。",
  "---",
  "创建一个调研任务清单。",
  "创建一个网页或原型设计任务。",
];
