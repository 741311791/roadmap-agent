import { describe, it, expect, beforeEach } from 'vitest';
import { useUIStore } from '@/lib/store/ui-store';
import { act, renderHook } from '@testing-library/react';

describe('UIStore', () => {
  beforeEach(() => {
    // 在每个测试前重置store
    const { result } = renderHook(() => useUIStore());
    act(() => {
      result.current.setLeftSidebarCollapsed(false);
      result.current.setRightSidebarCollapsed(false);
      result.current.setMobileMenuOpen(false);
      result.current.closeDialog('tutorial');
      result.current.closeDialog('review');
    });
  });

  describe('侧边栏状态', () => {
    it('应该切换左侧边栏', () => {
      const { result } = renderHook(() => useUIStore());

      const initial = result.current.leftSidebarCollapsed;

      act(() => {
        result.current.toggleLeftSidebar();
      });

      expect(result.current.leftSidebarCollapsed).toBe(!initial);

      act(() => {
        result.current.toggleLeftSidebar();
      });

      expect(result.current.leftSidebarCollapsed).toBe(initial);
    });

    it('应该设置左侧边栏状态', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setLeftSidebarCollapsed(true);
      });

      expect(result.current.leftSidebarCollapsed).toBe(true);
    });
  });

  describe('视图模式', () => {
    it('应该设置视图模式', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setViewMode('flow');
      });

      expect(result.current.viewMode).toBe('flow');

      act(() => {
        result.current.setViewMode('list');
      });

      expect(result.current.viewMode).toBe('list');
    });
  });

  describe('对话框状态', () => {
    it('应该打开和关闭教程对话框', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.tutorialDialog.isOpen).toBe(false);

      act(() => {
        result.current.openDialog('tutorial', { conceptId: 'c1' });
      });

      expect(result.current.tutorialDialog.isOpen).toBe(true);
      expect(result.current.tutorialDialog.data).toEqual({ conceptId: 'c1' });

      act(() => {
        result.current.closeDialog('tutorial');
      });

      expect(result.current.tutorialDialog.isOpen).toBe(false);
    });

    it('应该打开和关闭审核对话框', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.reviewDialog.isOpen).toBe(false);

      act(() => {
        result.current.openDialog('review');
      });

      expect(result.current.reviewDialog.isOpen).toBe(true);

      act(() => {
        result.current.closeDialog('review');
      });

      expect(result.current.reviewDialog.isOpen).toBe(false);
    });

    it('应该关闭所有对话框', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.openDialog('tutorial');
        result.current.openDialog('review');
      });

      expect(result.current.tutorialDialog.isOpen).toBe(true);
      expect(result.current.reviewDialog.isOpen).toBe(true);

      act(() => {
        result.current.closeDialog('tutorial');
        result.current.closeDialog('review');
      });

      expect(result.current.tutorialDialog.isOpen).toBe(false);
      expect(result.current.reviewDialog.isOpen).toBe(false);
    });
  });

  describe('移动端菜单', () => {
    it('应该切换移动端菜单', () => {
      const { result } = renderHook(() => useUIStore());

      expect(result.current.isMobileMenuOpen).toBe(false);

      act(() => {
        result.current.toggleMobileMenu();
      });

      expect(result.current.isMobileMenuOpen).toBe(true);

      act(() => {
        result.current.toggleMobileMenu();
      });

      expect(result.current.isMobileMenuOpen).toBe(false);
    });

    it('应该设置移动端菜单状态', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setMobileMenuOpen(true);
      });

      expect(result.current.isMobileMenuOpen).toBe(true);
    });
  });

  describe('主题', () => {
    it('应该设置主题', () => {
      const { result } = renderHook(() => useUIStore());

      act(() => {
        result.current.setTheme('dark');
      });

      expect(result.current.theme).toBe('dark');

      act(() => {
        result.current.setTheme('light');
      });

      expect(result.current.theme).toBe('light');
    });
  });
});

