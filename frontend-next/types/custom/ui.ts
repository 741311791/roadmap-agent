/**
 * 前端UI组件专用类型
 */

/**
 * 视图模式
 */
export type ViewMode = 'flow' | 'list' | 'immersive';

/**
 * Toast配置
 */
export interface ToastConfig {
  id: string;
  title: string;
  description?: string;
  variant: 'default' | 'success' | 'error' | 'warning' | 'info';
  duration?: number;
}

/**
 * Dialog状态
 */
export interface DialogState {
  isOpen: boolean;
  title?: string;
  description?: string;
  content?: React.ReactNode;
  onConfirm?: () => void | Promise<void>;
  onCancel?: () => void;
  confirmText?: string;
  cancelText?: string;
}

/**
 * 加载状态
 */
export interface LoadingState {
  isLoading: boolean;
  loadingText?: string;
  progress?: number;
}

/**
 * 错误状态
 */
export interface ErrorState {
  hasError: boolean;
  errorMessage?: string;
  errorCode?: string;
  canRetry?: boolean;
}

/**
 * 侧边栏状态
 */
export interface SidebarState {
  isCollapsed: boolean;
  activeTab?: string;
  width?: number;
}

/**
 * 拖拽状态
 */
export interface DragState {
  isDragging: boolean;
  draggedId?: string;
  draggedType?: 'concept' | 'module' | 'stage';
  dropTargetId?: string;
}

/**
 * 选择状态
 */
export interface SelectionState {
  selectedIds: Set<string>;
  selectionMode: 'single' | 'multiple';
  lastSelectedId?: string;
}

/**
 * 通用组件Props
 */
export interface BaseComponentProps {
  className?: string;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

/**
 * 可关闭组件Props
 */
export interface ClosableComponentProps extends BaseComponentProps {
  onClose?: () => void;
}

/**
 * 可确认组件Props
 */
export interface ConfirmableComponentProps extends ClosableComponentProps {
  onConfirm?: () => void | Promise<void>;
  confirmText?: string;
  cancelText?: string;
  isLoading?: boolean;
}
