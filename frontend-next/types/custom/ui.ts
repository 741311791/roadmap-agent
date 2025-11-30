/**
 * Frontend UI-specific Types
 * These types are used only in the frontend and not shared with backend
 */

// View modes for roadmap display
export type ViewMode = 'tree' | 'flow';

// Sidebar collapse states
export interface SidebarState {
  leftCollapsed: boolean;
  rightCollapsed: boolean;
}

// Toast notification config
export interface ToastConfig {
  id: string;
  title: string;
  description?: string;
  variant: 'default' | 'success' | 'error' | 'warning';
  duration?: number;
}

// Dialog state
export interface DialogState {
  isOpen: boolean;
  title?: string;
  content?: React.ReactNode;
  onConfirm?: () => void;
  onCancel?: () => void;
}

// Theme mode
export type ThemeMode = 'light' | 'dark' | 'system';

// Navigation item
export interface NavItem {
  id: string;
  label: string;
  href: string;
  icon?: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

// Breadcrumb item
export interface BreadcrumbItem {
  label: string;
  href?: string;
}

