import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputProvider,
  PromptInputSubmit,
  PromptInputTextarea,
  PromptInputTools,
} from "@/components/deerflow-native/ai-elements/prompt-input";

describe("PromptInput", () => {
  it("should clear the controlled textarea immediately after async submit", async () => {
    const user = userEvent.setup();
    let resolveSubmit: (() => void) | undefined;
    const onSubmit = vi.fn(
      () =>
        new Promise<void>((resolve) => {
          resolveSubmit = resolve;
        })
    );

    render(
      <PromptInputProvider>
        <PromptInput onSubmit={onSubmit}>
          <PromptInputBody>
            <PromptInputTextarea />
          </PromptInputBody>
          <PromptInputFooter>
            <PromptInputTools>
              <PromptInputSubmit />
            </PromptInputTools>
          </PromptInputFooter>
        </PromptInput>
      </PromptInputProvider>
    );

    const textbox = screen.getByPlaceholderText("What would you like to know?");
    await user.type(textbox, "hello deerflow");

    fireEvent.submit(textbox.closest("form") as HTMLFormElement);

    expect(onSubmit).toHaveBeenCalledWith(
      {
        text: "hello deerflow",
        files: [],
      },
      expect.any(Object)
    );

    await waitFor(() => {
      expect(textbox).toHaveValue("");
    });

    resolveSubmit?.();
  });
});
