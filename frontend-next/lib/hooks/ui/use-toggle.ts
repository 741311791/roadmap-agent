/**
 * useToggle - 布尔状态切换 Hook
 * 
 * 简化布尔值的切换操作
 * 
 * @param initialValue - 初始值 (默认 false)
 * @returns [value, toggle, setValue]
 */

import { useState, useCallback } from 'react';

type UseToggleReturn = [
  boolean,
  () => void,
  (value: boolean) => void
];

export function useToggle(initialValue: boolean = false): UseToggleReturn {
  const [value, setValue] = useState(initialValue);

  const toggle = useCallback(() => {
    setValue((v) => !v);
  }, []);

  return [value, toggle, setValue];
}
