/**
 * useIntersectionObserver - 可见性检测 Hook
 * 
 * 检测元素是否在视口中可见,用于懒加载、无限滚动等场景
 * 
 * @param options - IntersectionObserver 配置
 * @returns ref 和 isIntersecting 状态
 */

import { useEffect, useRef, useState } from 'react';

interface UseIntersectionObserverOptions extends IntersectionObserverInit {
  /** 冻结状态,一旦触发后不再更新 */
  freezeOnceVisible?: boolean;
}

export function useIntersectionObserver(
  options: UseIntersectionObserverOptions = {}
): [React.RefObject<HTMLElement>, boolean] {
  const { freezeOnceVisible = false, ...observerOptions } = options;

  const ref = useRef<HTMLElement>(null);
  const [isIntersecting, setIsIntersecting] = useState(false);
  const frozenRef = useRef(false);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;

    // 如果已冻结,不再创建 observer
    if (frozenRef.current) return;

    const observer = new IntersectionObserver(([entry]) => {
      const isVisible = entry.isIntersecting;
      setIsIntersecting(isVisible);

      if (isVisible && freezeOnceVisible) {
        frozenRef.current = true;
      }
    }, observerOptions);

    observer.observe(element);

    return () => {
      observer.disconnect();
    };
  }, [observerOptions, freezeOnceVisible]);

  return [ref, isIntersecting];
}
