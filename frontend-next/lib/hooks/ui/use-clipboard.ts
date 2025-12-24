/**
 * useClipboard - 剪贴板操作 Hook
 * 
 * 提供复制文本到剪贴板的功能,带状态反馈
 * 
 * @param timeout - 成功状态持续时间 (毫秒)
 * @returns copy 函数和状态
 */

import { useState, useCallback } from 'react';

interface UseClipboardReturn {
  /** 复制文本到剪贴板 */
  copy: (text: string) => Promise<void>;
  /** 是否已复制 */
  copied: boolean;
  /** 错误信息 */
  error: Error | null;
}

export function useClipboard(timeout: number = 2000): UseClipboardReturn {
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const copy = useCallback(
    async (text: string) => {
      if (!navigator?.clipboard) {
        setError(new Error('Clipboard API not supported'));
        return;
      }

      try {
        await navigator.clipboard.writeText(text);
        setCopied(true);
        setError(null);

        // 重置状态
        setTimeout(() => {
          setCopied(false);
        }, timeout);
      } catch (err) {
        setError(err as Error);
        setCopied(false);
      }
    },
    [timeout]
  );

  return { copy, copied, error };
}
