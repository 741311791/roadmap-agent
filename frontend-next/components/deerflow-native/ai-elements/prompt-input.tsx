"use client";

import * as React from "react";
import {
  type ChangeEvent,
  type ChangeEventHandler,
  type ClipboardEventHandler,
  type ComponentProps,
  createContext,
  Fragment,
  type FormEvent,
  type FormEventHandler,
  type HTMLAttributes,
  type KeyboardEventHandler,
  type PropsWithChildren,
  type ReactNode,
  type RefObject,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  ArrowUpIcon,
  Loader2Icon,
  PaperclipIcon,
  PlusIcon,
  SquareIcon,
  XIcon,
} from "lucide-react";
import { nanoid } from "nanoid";
import type { ChatStatus, FileUIPart } from "ai";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  HoverCard,
  HoverCardContent,
  HoverCardTrigger,
} from "@/components/deerflow-native/ui/hover-card";
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from "@/components/deerflow-native/ui/input-group";
import { isIMEComposing } from "@/lib/ime";
import { cn } from "@/lib/utils";

/**
 * 附件上下文。
 */
export type PromptInputAttachmentsContext = {
  files: (FileUIPart & { id: string })[];
  add: (files: File[] | FileList) => void;
  remove: (id: string) => void;
  clear: () => void;
  openFileDialog: () => void;
  fileInputRef: RefObject<HTMLInputElement | null>;
};

/**
 * 文本输入上下文。
 */
export type PromptInputTextContext = {
  value: string;
  setInput: (value: string) => void;
  clear: () => void;
};

/**
 * PromptInput 控制器。
 */
export type PromptInputControllerProps = {
  textInput: PromptInputTextContext;
  attachments: PromptInputAttachmentsContext;
  __registerFileInput: (
    ref: RefObject<HTMLInputElement | null>,
    open: () => void
  ) => void;
};

const PromptInputControllerContext = createContext<PromptInputControllerProps | null>(null);
const PromptInputProviderAttachmentsContext =
  createContext<PromptInputAttachmentsContext | null>(null);
const PromptInputLocalAttachmentsContext =
  createContext<PromptInputAttachmentsContext | null>(null);

/**
 * 读取 PromptInput 控制器。
 */
export function usePromptInputController(): PromptInputControllerProps {
  const context = useContext(PromptInputControllerContext);
  if (!context) {
    throw new Error("PromptInput controller is not available.");
  }
  return context;
}

/**
 * 读取附件上下文。
 */
export function usePromptInputAttachments(): PromptInputAttachmentsContext {
  const providerContext = useContext(PromptInputProviderAttachmentsContext);
  const localContext = useContext(PromptInputLocalAttachmentsContext);
  const context = providerContext ?? localContext;

  if (!context) {
    throw new Error("PromptInput attachments context is not available.");
  }

  return context;
}

/**
 * Provider 属性。
 */
export interface PromptInputProviderProps extends PropsWithChildren {
  initialInput?: string;
}

/**
 * 提供 Deer-Flow 原版 PromptInput 的共享输入状态。
 */
export function PromptInputProvider({
  initialInput = "",
  children,
}: PromptInputProviderProps) {
  const [textInput, setTextInput] = useState(initialInput);
  const [attachmentFiles, setAttachmentFiles] = useState<(FileUIPart & { id: string })[]>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const openFileDialogRef = useRef<() => void>(() => {});

  const clearTextInput = useCallback(() => {
    setTextInput("");
  }, []);

  const addAttachments = useCallback((files: File[] | FileList) => {
    const nextFiles = Array.from(files);
    if (nextFiles.length === 0) {
      return;
    }

    setAttachmentFiles((previousFiles) =>
      previousFiles.concat(
        nextFiles.map((file) => ({
          id: nanoid(),
          type: "file" as const,
          url: URL.createObjectURL(file),
          mediaType: file.type,
          filename: file.name,
        }))
      )
    );
  }, []);

  const removeAttachment = useCallback((id: string) => {
    setAttachmentFiles((previousFiles) => {
      const targetFile = previousFiles.find((file) => file.id === id);
      if (targetFile?.url) {
        URL.revokeObjectURL(targetFile.url);
      }

      return previousFiles.filter((file) => file.id !== id);
    });
  }, []);

  const clearAttachments = useCallback(() => {
    setAttachmentFiles((previousFiles) => {
      for (const file of previousFiles) {
        if (file.url) {
          URL.revokeObjectURL(file.url);
        }
      }
      return [];
    });
  }, []);

  const attachmentsRef = useRef(attachmentFiles);
  attachmentsRef.current = attachmentFiles;

  useEffect(() => {
    return () => {
      for (const file of attachmentsRef.current) {
        if (file.url) {
          URL.revokeObjectURL(file.url);
        }
      }
    };
  }, []);

  const openFileDialog = useCallback(() => {
    openFileDialogRef.current?.();
  }, []);

  const attachments = useMemo<PromptInputAttachmentsContext>(
    () => ({
      files: attachmentFiles,
      add: addAttachments,
      remove: removeAttachment,
      clear: clearAttachments,
      openFileDialog,
      fileInputRef,
    }),
    [
      addAttachments,
      attachmentFiles,
      clearAttachments,
      openFileDialog,
      removeAttachment,
    ]
  );

  const registerFileInput = useCallback(
    (ref: RefObject<HTMLInputElement | null>, open: () => void) => {
      fileInputRef.current = ref.current;
      openFileDialogRef.current = open;
    },
    []
  );

  const controller = useMemo<PromptInputControllerProps>(
    () => ({
      textInput: {
        value: textInput,
        setInput: setTextInput,
        clear: clearTextInput,
      },
      attachments,
      __registerFileInput: registerFileInput,
    }),
    [attachments, clearTextInput, registerFileInput, textInput]
  );

  return (
    <PromptInputControllerContext.Provider value={controller}>
      <PromptInputProviderAttachmentsContext.Provider value={attachments}>
        {children}
      </PromptInputProviderAttachmentsContext.Provider>
    </PromptInputControllerContext.Provider>
  );
}

/**
 * PromptInput 提交消息结构。
 */
export type PromptInputMessage = {
  text: string;
  files: FileUIPart[];
};

/**
 * PromptInput 属性。
 */
export type PromptInputProps = Omit<
  HTMLAttributes<HTMLFormElement>,
  "onSubmit" | "onError"
> & {
  accept?: string;
  disabled?: boolean;
  multiple?: boolean;
  globalDrop?: boolean;
  onSubmit: (
    message: PromptInputMessage,
    event: FormEvent<HTMLFormElement>
  ) => void | Promise<void>;
};

/**
 * Deer-Flow 风格 PromptInput 容器。
 */
export function PromptInput({
  className,
  accept,
  disabled,
  multiple,
  globalDrop = false,
  onSubmit,
  children,
  ...props
}: PromptInputProps) {
  const controller = useContext(PromptInputControllerContext);
  const usingProvider = Boolean(controller);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const formRef = useRef<HTMLFormElement | null>(null);

  const [localAttachments, setLocalAttachments] = useState<(FileUIPart & { id: string })[]>([]);
  const files = usingProvider ? controller!.attachments.files : localAttachments;

  const addLocalAttachments = useCallback((nextFiles: File[] | FileList) => {
    const incomingFiles = Array.from(nextFiles);
    if (incomingFiles.length === 0) {
      return;
    }

    setLocalAttachments((previousFiles) =>
      previousFiles.concat(
        incomingFiles.map((file) => ({
          id: nanoid(),
          type: "file" as const,
          url: URL.createObjectURL(file),
          mediaType: file.type,
          filename: file.name,
        }))
      )
    );
  }, []);

  const removeLocalAttachment = useCallback((id: string) => {
    setLocalAttachments((previousFiles) => {
      const targetFile = previousFiles.find((file) => file.id === id);
      if (targetFile?.url) {
        URL.revokeObjectURL(targetFile.url);
      }
      return previousFiles.filter((file) => file.id !== id);
    });
  }, []);

  const clearLocalAttachments = useCallback(() => {
    setLocalAttachments((previousFiles) => {
      for (const file of previousFiles) {
        if (file.url) {
          URL.revokeObjectURL(file.url);
        }
      }
      return [];
    });
  }, []);

  const openLocalFileDialog = useCallback(() => {
    inputRef.current?.click();
  }, []);

  const attachmentsContext = useMemo<PromptInputAttachmentsContext>(
    () =>
      usingProvider
        ? controller!.attachments
        : {
            files: localAttachments,
            add: addLocalAttachments,
            remove: removeLocalAttachment,
            clear: clearLocalAttachments,
            openFileDialog: openLocalFileDialog,
            fileInputRef: inputRef,
          },
    [
      addLocalAttachments,
      clearLocalAttachments,
      controller,
      localAttachments,
      openLocalFileDialog,
      removeLocalAttachment,
      usingProvider,
    ]
  );

  useEffect(() => {
    if (!usingProvider) {
      return;
    }

    controller!.__registerFileInput(inputRef, () => {
      inputRef.current?.click();
    });
  }, [controller, usingProvider]);

  useEffect(() => {
    if (!globalDrop) {
      return;
    }

    const handleDragOver = (event: DragEvent) => {
      if (event.dataTransfer?.types?.includes("Files")) {
        event.preventDefault();
      }
    };

    const handleDrop = (event: DragEvent) => {
      if (event.dataTransfer?.types?.includes("Files")) {
        event.preventDefault();
      }

      if (event.dataTransfer?.files && event.dataTransfer.files.length > 0) {
        attachmentsContext.add(event.dataTransfer.files);
      }
    };

    document.addEventListener("dragover", handleDragOver);
    document.addEventListener("drop", handleDrop);

    return () => {
      document.removeEventListener("dragover", handleDragOver);
      document.removeEventListener("drop", handleDrop);
    };
  }, [attachmentsContext, globalDrop]);

  const handleChange: ChangeEventHandler<HTMLInputElement> = (event) => {
    if (event.currentTarget.files) {
      attachmentsContext.add(event.currentTarget.files);
    }
    event.currentTarget.value = "";
  };

  const handleSubmit: FormEventHandler<HTMLFormElement> = (event) => {
    event.preventDefault();

    const form = event.currentTarget;
    const text = usingProvider
      ? controller!.textInput.value
      : ((new FormData(form).get("message") as string | null) ?? "");

    if (!usingProvider) {
      form.reset();
    }

    const result = onSubmit(
      {
        text,
        files: files.map(({ id: _id, ...file }) => file),
      },
      event
    );

    attachmentsContext.clear();
    if (usingProvider) {
      controller!.textInput.clear();
    }

    if (result instanceof Promise) {
      void result.catch(() => {
        // 输入内容已用于 optimistic rendering，失败时不回填，避免再次触发重叠状态。
      });
      return;
    }
  };

  const formContent = (
    <>
      <input
        accept={accept}
        aria-label="Upload files"
        className="hidden"
        disabled={disabled}
        multiple={multiple}
        onChange={handleChange}
        ref={inputRef}
        type="file"
      />
      <form
        className={cn("w-full", className)}
        onSubmit={handleSubmit}
        ref={formRef}
        {...props}
      >
        <InputGroup>{children}</InputGroup>
      </form>
    </>
  );

  return usingProvider ? (
    formContent
  ) : (
    <PromptInputLocalAttachmentsContext.Provider value={attachmentsContext}>
      {formContent}
    </PromptInputLocalAttachmentsContext.Provider>
  );
}

/**
 * PromptInput 主体区域。
 */
export function PromptInputBody({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("contents", className)} {...props} />;
}

/**
 * PromptInput 附件渲染容器。
 */
export function PromptInputAttachments({
  children,
  className,
  ...props
}: Omit<HTMLAttributes<HTMLDivElement>, "children"> & {
  children: (attachment: FileUIPart & { id: string }) => ReactNode;
}) {
  const attachments = usePromptInputAttachments();

  if (attachments.files.length === 0) {
    return null;
  }

  return (
    <div
      className={cn("flex w-full flex-wrap items-center gap-2 p-3", className)}
      {...props}
    >
      {attachments.files.map((file) => (
        <Fragment key={file.id}>
          <div className="max-w-60">{children(file)}</div>
        </Fragment>
      ))}
    </div>
  );
}

/**
 * PromptInput 附件卡片。
 */
export function PromptInputAttachment({
  data,
  className,
  ...props
}: HTMLAttributes<HTMLDivElement> & {
  data: FileUIPart & { id: string };
}) {
  const attachments = usePromptInputAttachments();
  const isImage = data.mediaType?.startsWith("image/") && data.url;

  return (
    <HoverCard openDelay={0} closeDelay={0}>
      <HoverCardTrigger asChild>
        <div
          className={cn(
            "group border-border hover:bg-accent hover:text-accent-foreground relative flex h-8 cursor-pointer items-center gap-1.5 rounded-md border px-1.5 text-sm font-medium transition-all select-none",
            className
          )}
          {...props}
        >
          <div className="relative size-5 shrink-0">
            <div className="bg-background absolute inset-0 flex size-5 items-center justify-center overflow-hidden rounded transition-opacity group-hover:opacity-0">
              {isImage ? (
                <img
                  alt={data.filename || "attachment"}
                  className="size-5 object-cover"
                  src={data.url}
                />
              ) : (
                <div className="text-muted-foreground flex size-5 items-center justify-center">
                  <PaperclipIcon className="size-3" />
                </div>
              )}
            </div>
            <Button
              aria-label="Remove attachment"
              className="absolute inset-0 size-5 rounded p-0 opacity-0 transition-opacity group-hover:pointer-events-auto group-hover:opacity-100 [&>svg]:size-2.5"
              onClick={(event) => {
                event.stopPropagation();
                attachments.remove(data.id);
              }}
              type="button"
              variant="ghost"
            >
              <XIcon />
            </Button>
          </div>
          <span className="flex-1 truncate">
            {data.filename || (isImage ? "Image" : "Attachment")}
          </span>
        </div>
      </HoverCardTrigger>
      <HoverCardContent align="start" className="w-auto p-2">
        <div className="space-y-2">
          {isImage && (
            <div className="flex max-h-96 w-96 items-center justify-center overflow-hidden rounded-md border">
              <img
                alt={data.filename || "attachment preview"}
                className="max-h-full max-w-full object-contain"
                src={data.url}
              />
            </div>
          )}
          <div className="text-sm font-medium">
            {data.filename || (isImage ? "Image" : "Attachment")}
          </div>
        </div>
      </HoverCardContent>
    </HoverCard>
  );
}

/**
 * PromptInput 文本框。
 */
export function PromptInputTextarea({
  className,
  onChange,
  placeholder = "What would you like to know?",
  ...props
}: ComponentProps<typeof InputGroupTextarea>) {
  const controller = useContext(PromptInputControllerContext);
  const attachments = usePromptInputAttachments();
  const [isComposing, setIsComposing] = useState(false);

  const handleKeyDown: KeyboardEventHandler<HTMLTextAreaElement> = (event) => {
    if (event.key === "Enter") {
      if (isIMEComposing(event, isComposing)) {
        return;
      }

      if (event.shiftKey) {
        return;
      }

      event.preventDefault();
      const form = event.currentTarget.form;
      const submitButton = form?.querySelector(
        'button[type="submit"]'
      ) as HTMLButtonElement | null;
      if (submitButton?.disabled) {
        return;
      }
      form?.requestSubmit();
      return;
    }

    if (
      event.key === "Backspace" &&
      event.currentTarget.value === "" &&
      attachments.files.length > 0
    ) {
      event.preventDefault();
      const lastAttachment = attachments.files.at(-1);
      if (lastAttachment) {
        attachments.remove(lastAttachment.id);
      }
    }
  };

  const handlePaste: ClipboardEventHandler<HTMLTextAreaElement> = (event) => {
    const items = event.clipboardData?.items;
    if (!items) {
      return;
    }

    const files: File[] = [];
    for (const item of items) {
      if (item.kind === "file") {
        const file = item.getAsFile();
        if (file) {
          files.push(file);
        }
      }
    }

    if (files.length > 0) {
      event.preventDefault();
      attachments.add(files);
    }
  };

  const controlledProps = controller
    ? {
        value: controller.textInput.value,
        onChange: (event: ChangeEvent<HTMLTextAreaElement>) => {
          controller.textInput.setInput(event.currentTarget.value);
          onChange?.(event);
        },
      }
    : {
        onChange,
      };

  return (
    <InputGroupTextarea
      className={cn("field-sizing-content max-h-48 min-h-16", className)}
      name="message"
      onCompositionEnd={() => setIsComposing(false)}
      onCompositionStart={() => setIsComposing(true)}
      onKeyDown={handleKeyDown}
      onPaste={handlePaste}
      placeholder={placeholder}
      {...props}
      {...controlledProps}
    />
  );
}

/**
 * PromptInput 底部工具栏。
 */
export function PromptInputFooter({
  className,
  ...props
}: Omit<ComponentProps<typeof InputGroupAddon>, "align">) {
  return (
    <InputGroupAddon
      align="block-end"
      className={cn("justify-between gap-1", className)}
      {...props}
    />
  );
}

/**
 * PromptInput 工具分组。
 */
export function PromptInputTools({
  className,
  ...props
}: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("flex items-center gap-1", className)} {...props} />;
}

/**
 * PromptInput 通用按钮。
 */
export const PromptInputButton = React.forwardRef<
  HTMLButtonElement,
  ComponentProps<typeof InputGroupButton>
>(({ className, variant = "ghost", ...props }, ref) => {
  return (
    <InputGroupButton
      ref={ref}
      className={cn(className)}
      size="sm"
      type="button"
      variant={variant}
      {...props}
    />
  );
});
PromptInputButton.displayName = "PromptInputButton";

/**
 * PromptInput 动作菜单。
 */
export function PromptInputActionMenu(props: ComponentProps<typeof DropdownMenu>) {
  return <DropdownMenu {...props} />;
}

/**
 * PromptInput 动作菜单触发器。
 */
export function PromptInputActionMenuTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof PromptInputButton>) {
  return (
    <DropdownMenuTrigger asChild>
      <PromptInputButton className={className} {...props}>
        {children ?? <PlusIcon className="size-4" />}
      </PromptInputButton>
    </DropdownMenuTrigger>
  );
}

/**
 * PromptInput 动作菜单内容。
 */
export function PromptInputActionMenuContent({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuContent>) {
  return (
    <DropdownMenuContent align="start" className={cn(className)} {...props} />
  );
}

/**
 * PromptInput 动作菜单项。
 */
export function PromptInputActionMenuItem({
  className,
  ...props
}: ComponentProps<typeof DropdownMenuItem>) {
  return <DropdownMenuItem className={cn(className)} {...props} />;
}

/**
 * PromptInput 提交按钮。
 */
export function PromptInputSubmit({
  className,
  variant = "default",
  size = "icon-sm",
  status,
  children,
  ...props
}: ComponentProps<typeof InputGroupButton> & {
  status?: ChatStatus;
}) {
  let icon = <ArrowUpIcon className="size-4" />;

  if (status === "submitted") {
    icon = <Loader2Icon className="size-4 animate-spin" />;
  } else if (status === "streaming") {
    icon = <SquareIcon className="size-4" />;
  } else if (status === "error") {
    icon = <XIcon className="size-4" />;
  }

  return (
    <InputGroupButton
      aria-label="Submit"
      className={cn(className)}
      size={size}
      type="submit"
      variant={variant}
      {...props}
    >
      {children ?? icon}
    </InputGroupButton>
  );
}
