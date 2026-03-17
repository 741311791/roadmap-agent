/**
 * 客户邮件渲染工具
 *
 * 负责将 Markdown 正文渲染到 HTML 模板中，用于前端预览。
 */

const INLINE_CODE_PATTERN = /`([^`]+)`/g;
const BOLD_PATTERN = /\*\*(.+?)\*\*/g;
const ITALIC_PATTERN = /(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)/g;
const LINK_PATTERN = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;

export const DEFAULT_EMAIL_TEMPLATE_SHELL = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{{subject}}</title>
  </head>
  <body style="margin:0;padding:0;background:#f6f7f6;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;color:#1c1917;">
    <div style="max-width:680px;margin:0 auto;padding:32px 16px;">
      <div style="background:#ffffff;border:1px solid #e3e7e3;border-radius:28px;overflow:hidden;box-shadow:0 18px 60px rgba(28,25,23,0.08);">
        <div style="padding:36px 40px;background:linear-gradient(180deg,#f6f7f6 0%,#eef2ee 100%);border-bottom:1px solid #e3e7e3;">
          <div style="display:inline-block;padding:8px 14px;border-radius:999px;background:#e3e7e3;color:#4c5d4c;font-size:12px;font-weight:700;letter-spacing:1.6px;text-transform:uppercase;">
            Fast Learning
          </div>
          <h1 style="margin:18px 0 0;font-size:32px;line-height:1.25;font-weight:700;color:#1c1917;">
            {{subject}}
          </h1>
        </div>

        <div style="padding:36px 40px;">
          {{content}}
        </div>
      </div>
    </div>
  </body>
</html>`;

/**
 * 转义 HTML 特殊字符。
 *
 * Args:
 *   value: 原始文本
 *
 * Returns:
 *   转义后的文本
 */
function escapeHtml(value: string): string {
  return value
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
    .replaceAll("'", '&#39;');
}

/**
 * 渲染行内 Markdown。
 *
 * Args:
 *   value: 原始文本
 *
 * Returns:
 *   HTML 字符串
 */
function renderInlineMarkdown(value: string): string {
  let rendered = escapeHtml(value);
  rendered = rendered.replace(
    LINK_PATTERN,
    '<a href="$2" style="color:#4c5d4c;text-decoration:underline;">$1</a>'
  );
  rendered = rendered.replace(
    INLINE_CODE_PATTERN,
    '<code style="padding:2px 6px;background:#f6f7f6;border:1px solid #e3e7e3;border-radius:6px;font-family:monospace;">$1</code>'
  );
  rendered = rendered.replace(BOLD_PATTERN, '<strong>$1</strong>');
  rendered = rendered.replace(ITALIC_PATTERN, '<em>$1</em>');
  return rendered;
}

/**
 * 将 Markdown 转为 HTML。
 *
 * Args:
 *   markdownContent: Markdown 正文
 *
 * Returns:
 *   HTML 字符串
 */
export function markdownToHtml(markdownContent: string): string {
  const normalizedMarkdown = markdownContent.replaceAll('\r\n', '\n').trim();
  if (!normalizedMarkdown) {
    return '<p style="margin:0;font-size:15px;line-height:1.9;color:#6b7280;">No content yet.</p>';
  }

  const lines = normalizedMarkdown.split('\n');
  const htmlParts: string[] = [];
  let index = 0;

  while (index < lines.length) {
    const line = lines[index].trim();

    if (!line) {
      index += 1;
      continue;
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.+)$/);
    if (headingMatch) {
      const level = headingMatch[1].length;
      const content = renderInlineMarkdown(headingMatch[2]);
      const fontSizes = {
        1: '30px',
        2: '24px',
        3: '20px',
        4: '18px',
        5: '16px',
        6: '15px',
      } as const;
      htmlParts.push(
        `<h${level} style="margin:0 0 14px;font-size:${fontSizes[level as keyof typeof fontSizes]};line-height:1.35;color:#1c1917;">${content}</h${level}>`
      );
      index += 1;
      continue;
    }

    const unorderedListMatch = line.match(/^[-*+]\s+(.+)$/);
    if (unorderedListMatch) {
      const listItems: string[] = [];
      while (index < lines.length) {
        const currentLine = lines[index].trim();
        const match = currentLine.match(/^[-*+]\s+(.+)$/);
        if (!match) {
          break;
        }
        listItems.push(
          `<li style="margin:0 0 8px;color:#44403c;">${renderInlineMarkdown(match[1])}</li>`
        );
        index += 1;
      }

      htmlParts.push(
        `<ul style="margin:0 0 18px;padding-left:22px;line-height:1.9;">${listItems.join('')}</ul>`
      );
      continue;
    }

    const orderedListMatch = line.match(/^\d+\.\s+(.+)$/);
    if (orderedListMatch) {
      const listItems: string[] = [];
      while (index < lines.length) {
        const currentLine = lines[index].trim();
        const match = currentLine.match(/^\d+\.\s+(.+)$/);
        if (!match) {
          break;
        }
        listItems.push(
          `<li style="margin:0 0 8px;color:#44403c;">${renderInlineMarkdown(match[1])}</li>`
        );
        index += 1;
      }

      htmlParts.push(
        `<ol style="margin:0 0 18px;padding-left:22px;line-height:1.9;">${listItems.join('')}</ol>`
      );
      continue;
    }

    const paragraphLines = [line];
    index += 1;

    while (index < lines.length) {
      const nextLine = lines[index].trim();
      if (!nextLine) {
        index += 1;
        break;
      }
      if (/^(#{1,6})\s+(.+)$/.test(nextLine) || /^[-*+]\s+(.+)$/.test(nextLine) || /^\d+\.\s+(.+)$/.test(nextLine)) {
        break;
      }
      paragraphLines.push(nextLine);
      index += 1;
    }

    htmlParts.push(
      `<p style="margin:0 0 18px;font-size:15px;line-height:1.9;color:#44403c;">${paragraphLines
        .map((paragraphLine) => renderInlineMarkdown(paragraphLine))
        .join('<br />')}</p>`
    );
  }

  return htmlParts.join('');
}

/**
 * 组合模板和 Markdown 正文。
 *
 * Args:
 *   templateHtml: HTML 模板壳
 *   subject: 邮件主题
 *   markdownContent: Markdown 正文
 *   frontendUrl: 前端地址
 *
 * Returns:
 *   完整 HTML 邮件
 */
export function composeEmailHtml(
  templateHtml: string,
  subject: string,
  markdownContent: string,
  frontendUrl = '#'
): string {
  const renderedContent = markdownToHtml(markdownContent);
  const renderedSubject = escapeHtml(subject);

  const renderedHtml = templateHtml
    .replaceAll('{{subject}}', renderedSubject)
    .replaceAll('{{content}}', renderedContent)
    .replaceAll('{{frontend_url}}', frontendUrl);

  if (templateHtml.includes('{{content}}')) {
    return renderedHtml;
  }

  const fallbackContent = `<div style="max-width:680px;margin:0 auto;padding:0 16px 32px;">${renderedContent}</div>`;
  if (renderedHtml.includes('</body>')) {
    return renderedHtml.replace('</body>', `${fallbackContent}</body>`);
  }
  return renderedHtml + fallbackContent;
}

