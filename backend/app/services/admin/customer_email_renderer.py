"""
客户邮件渲染工具

负责将 Markdown 正文渲染为 HTML，并注入邮件模板。
"""
import re

from app.config.settings import settings


INLINE_CODE_PATTERN = re.compile(r"`([^`]+)`")
BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")
ITALIC_PATTERN = re.compile(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)")
LINK_PATTERN = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")


def escape_html(value: str) -> str:
    """
    转义 HTML 特殊字符

    Args:
        value: 原始文本

    Returns:
        转义后的文本
    """
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_inline_markdown(value: str) -> str:
    """
    渲染行内 Markdown

    Args:
        value: 原始文本

    Returns:
        HTML 字符串
    """
    escaped_value = escape_html(value)
    escaped_value = LINK_PATTERN.sub(r'<a href="\2" style="color:#4c5d4c;text-decoration:underline;">\1</a>', escaped_value)
    escaped_value = INLINE_CODE_PATTERN.sub(
        r'<code style="padding:2px 6px;background:#f6f7f6;border:1px solid #e3e7e3;border-radius:6px;font-family:monospace;">\1</code>',
        escaped_value,
    )
    escaped_value = BOLD_PATTERN.sub(r"<strong>\1</strong>", escaped_value)
    escaped_value = ITALIC_PATTERN.sub(r"<em>\1</em>", escaped_value)
    return escaped_value


def markdown_to_html(markdown_content: str) -> str:
    """
    将 Markdown 正文转换为邮件可用 HTML

    Args:
        markdown_content: Markdown 正文

    Returns:
        HTML 字符串
    """
    normalized_markdown = markdown_content.replace("\r\n", "\n").strip()
    if not normalized_markdown:
        return '<p style="margin:0;font-size:15px;line-height:1.9;color:#6b7280;">No content yet.</p>'

    lines = normalized_markdown.split("\n")
    html_parts: list[str] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()

        if not line:
            index += 1
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            content = render_inline_markdown(heading_match.group(2))
            font_sizes = {
                1: "30px",
                2: "24px",
                3: "20px",
                4: "18px",
                5: "16px",
                6: "15px",
            }
            html_parts.append(
                f'<h{level} style="margin:0 0 14px;font-size:{font_sizes[level]};line-height:1.35;color:#1c1917;">{content}</h{level}>'
            )
            index += 1
            continue

        unordered_list_match = re.match(r"^[-*+]\s+(.+)$", line)
        if unordered_list_match:
            list_items: list[str] = []
            while index < len(lines):
                current_line = lines[index].strip()
                match = re.match(r"^[-*+]\s+(.+)$", current_line)
                if not match:
                    break
                list_items.append(
                    f'<li style="margin:0 0 8px;color:#44403c;">{render_inline_markdown(match.group(1))}</li>'
                )
                index += 1

            html_parts.append(
                '<ul style="margin:0 0 18px;padding-left:22px;line-height:1.9;">'
                + "".join(list_items)
                + "</ul>"
            )
            continue

        ordered_list_match = re.match(r"^\d+\.\s+(.+)$", line)
        if ordered_list_match:
            list_items = []
            while index < len(lines):
                current_line = lines[index].strip()
                match = re.match(r"^\d+\.\s+(.+)$", current_line)
                if not match:
                    break
                list_items.append(
                    f'<li style="margin:0 0 8px;color:#44403c;">{render_inline_markdown(match.group(1))}</li>'
                )
                index += 1

            html_parts.append(
                '<ol style="margin:0 0 18px;padding-left:22px;line-height:1.9;">'
                + "".join(list_items)
                + "</ol>"
            )
            continue

        paragraph_lines = [line]
        index += 1
        while index < len(lines):
            next_line = lines[index].strip()
            if not next_line:
                index += 1
                break
            if re.match(r"^(#{1,6})\s+(.+)$", next_line):
                break
            if re.match(r"^[-*+]\s+(.+)$", next_line):
                break
            if re.match(r"^\d+\.\s+(.+)$", next_line):
                break
            paragraph_lines.append(next_line)
            index += 1

        paragraph_html = "<br />".join(
            render_inline_markdown(paragraph_line)
            for paragraph_line in paragraph_lines
        )
        html_parts.append(
            f'<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#44403c;">{paragraph_html}</p>'
        )

    return "".join(html_parts)


def markdown_to_plain_text(markdown_content: str) -> str:
    """
    将 Markdown 正文转换为纯文本兜底内容

    Args:
        markdown_content: Markdown 正文

    Returns:
        纯文本字符串
    """
    normalized_markdown = markdown_content.replace("\r\n", "\n")
    normalized_markdown = LINK_PATTERN.sub(r"\1: \2", normalized_markdown)
    normalized_markdown = normalized_markdown.replace("**", "").replace("*", "").replace("`", "")
    normalized_markdown = re.sub(r"^#{1,6}\s*", "", normalized_markdown, flags=re.MULTILINE)
    normalized_markdown = re.sub(r"^\s*[-*+]\s+", "- ", normalized_markdown, flags=re.MULTILINE)
    normalized_markdown = re.sub(r"^\s*\d+\.\s+", "- ", normalized_markdown, flags=re.MULTILINE)
    normalized_markdown = re.sub(r"\n{3,}", "\n\n", normalized_markdown)
    return normalized_markdown.strip()


def compose_email_html(
    template_html: str,
    *,
    subject: str,
    markdown_content: str,
) -> str:
    """
    组合邮件模板与 Markdown 正文

    Args:
        template_html: HTML 模板壳
        subject: 邮件主题
        markdown_content: Markdown 正文

    Returns:
        最终邮件 HTML
    """
    rendered_content = markdown_to_html(markdown_content)
    rendered_subject = escape_html(subject)

    rendered_html = (
        template_html.replace("{{subject}}", rendered_subject)
        .replace("{{content}}", rendered_content)
        .replace("{{frontend_url}}", settings.FRONTEND_URL)
    )

    if "{{content}}" in template_html:
        return rendered_html

    fallback_content = (
        '<div style="max-width:680px;margin:0 auto;padding:0 16px 32px;">'
        f"{rendered_content}"
        "</div>"
    )
    if "</body>" in rendered_html:
        return rendered_html.replace("</body>", f"{fallback_content}</body>")
    return rendered_html + fallback_content

