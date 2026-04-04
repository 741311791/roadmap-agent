import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MentorMarkdownContent } from "@/components/mentor/mentor-thread";

describe("MentorMarkdownContent", () => {
  it("should render gfm table markdown as a semantic table", () => {
    const markdown = `
| 数组 A | 数组 B | 是否能广播 |
| --- | --- | --- |
| (3, 3) | (3,) | 能 |
| (4, 3) | (3, 2) | 不能 |
`.trim();

    render(<MentorMarkdownContent plainText={markdown} isUser={false} />);

    const table = screen.getByRole("table");
    expect(table).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "数组 A" })).toBeInTheDocument();
    expect(within(table).getByRole("columnheader", { name: "是否能广播" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "(3,)" })).toBeInTheDocument();
    expect(within(table).getByRole("cell", { name: "不能" })).toBeInTheDocument();
  });

  it("should render fenced code blocks and external links", () => {
    const markdown = [
      "访问 [文档](https://example.com)",
      "",
      "```ts",
      "const total = 1 + 2;",
      "```",
    ].join("\n");

    const { container } = render(
      <MentorMarkdownContent plainText={markdown} isUser={false} />
    );

    const link = screen.getByRole("link", { name: "文档" });
    expect(link).toHaveAttribute("href", "https://example.com");
    expect(link).toHaveAttribute("target", "_blank");

    const code = container.querySelector("code.language-ts");
    expect(code).toBeInTheDocument();
    expect(code?.textContent).toContain("const total = 1 + 2;");
    expect(code?.closest("pre")).toBeInTheDocument();
  });

  it("should normalize wrapped inline backticks before rendering", () => {
    render(
      <MentorMarkdownContent
        plainText={"把 `` `GROUP BY` `` 理解成透视是不准确的。"}
        isUser={false}
      />
    );

    expect(screen.getByText("GROUP BY")).toBeInTheDocument();
    expect(screen.queryByText("`GROUP BY`")).not.toBeInTheDocument();
  });
});
