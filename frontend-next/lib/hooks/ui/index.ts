/**
 * UI Hooks - 统一导出
 * 
 * 通用的 UI 工具 Hooks
 */

export { useDebounce } from './use-debounce';
export { useThrottle } from './use-throttle';
export {
  useMediaQuery,
  useIsMobile,
  useIsTablet,
  useIsDesktop,
  useIsWide,
  useDeviceType,
  useIsTouchDevice,
  type DeviceType,
} from './use-media-query';
export {
  useBreakpoint,
  useBreakpointValue,
  useOrientation,
  breakpoints,
  type Breakpoint,
  type BreakpointState,
  type Orientation,
} from './use-breakpoint';
export { useLocalStorage } from './use-local-storage';
export { useIntersectionObserver } from './use-intersection-observer';
export { useClipboard } from './use-clipboard';
export { useToggle } from './use-toggle';
