/**
 * UI 状态管理 Store
 * 使用 Zustand 管理全局 UI 状态
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

/**
 * 视图模式
 */
export type ViewMode = 'list' | 'flow';

/**
 * 对话框状态
 */
export interface DialogState {
  isOpen: boolean;
  data?: any;
}

/**
 * UI Store 状态
 */
export interface UIState {
  // 侧边栏
  leftSidebarCollapsed: boolean;
  rightSidebarCollapsed: boolean;

  // 视图模式
  viewMode: ViewMode;

  // 对话框状态
  tutorialDialog: DialogState;
  reviewDialog: DialogState;
  
  // 移动端菜单
  isMobileMenuOpen: boolean;

  // 主题
  theme: 'light' | 'dark' | 'system';
}

/**
 * UI Store Actions
 */
export interface UIActions {
  // 侧边栏
  toggleLeftSidebar: () => void;
  toggleRightSidebar: () => void;
  setLeftSidebarCollapsed: (collapsed: boolean) => void;
  setRightSidebarCollapsed: (collapsed: boolean) => void;

  // 视图模式
  setViewMode: (mode: ViewMode) => void;

  // 对话框
  openDialog: (dialog: 'tutorial' | 'review', data?: any) => void;
  closeDialog: (dialog: 'tutorial' | 'review') => void;

  // 移动端菜单
  toggleMobileMenu: () => void;
  setMobileMenuOpen: (open: boolean) => void;

  // 主题
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

/**
 * UI Store 类型
 */
export type UIStore = UIState & UIActions;

/**
 * 创建 UI Store
 */
export const useUIStore = create<UIStore>()(
  devtools(
    persist(
      (set) => ({
        // 初始状态
        leftSidebarCollapsed: false,
        rightSidebarCollapsed: true,
        viewMode: 'list',
        tutorialDialog: { isOpen: false },
        reviewDialog: { isOpen: false },
        isMobileMenuOpen: false,
        theme: 'system',

        // 侧边栏
        toggleLeftSidebar: () =>
          set((state) => ({
            leftSidebarCollapsed: !state.leftSidebarCollapsed,
          })),

        toggleRightSidebar: () =>
          set((state) => ({
            rightSidebarCollapsed: !state.rightSidebarCollapsed,
          })),

        setLeftSidebarCollapsed: (collapsed) =>
          set({ leftSidebarCollapsed: collapsed }),

        setRightSidebarCollapsed: (collapsed) =>
          set({ rightSidebarCollapsed: collapsed }),

        // 视图模式
        setViewMode: (mode) => set({ viewMode: mode }),

        // 对话框
        openDialog: (dialog, data) =>
          set((state) => ({
            [dialog + 'Dialog']: { isOpen: true, data },
          })),

        closeDialog: (dialog) =>
          set((state) => ({
            [dialog + 'Dialog']: { isOpen: false, data: undefined },
          })),

        // 移动端菜单
        toggleMobileMenu: () =>
          set((state) => ({
            isMobileMenuOpen: !state.isMobileMenuOpen,
          })),

        setMobileMenuOpen: (open) => set({ isMobileMenuOpen: open }),

        // 主题
        setTheme: (theme) => set({ theme }),
      }),
      {
        name: 'ui-storage',
        // 持久化所有状态
      }
    ),
    {
      name: 'UIStore',
    }
  )
);
