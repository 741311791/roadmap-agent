'use client';

/**
 * Auto-save hook for user profile
 * 
 * 自动保存用户资料的防抖hook
 */

import { useEffect, useRef, useState } from 'react';
import { useUserProfileStore } from '@/lib/store/user-profile-store';
import { useAuthStore } from '@/lib/store/auth-store';
import { saveUserProfile, type UserProfileRequest } from '@/lib/api/endpoints';

export type SaveStatus = 'idle' | 'saving' | 'saved' | 'error';

interface AutoSaveOptions {
  /** 防抖延迟（毫秒） */
  debounceMs?: number;
  /** 是否启用自动保存 */
  enabled?: boolean;
}

interface SaveStatusState {
  /** 当前保存状态 */
  status: SaveStatus;
  /** 状态消息 */
  message: string;
}

// 全局状态（用于跨hook共享）
let globalSaveStatus: SaveStatusState = {
  status: 'idle',
  message: '',
};

const saveStatusListeners = new Set<(status: SaveStatusState) => void>();

function updateSaveStatus(status: SaveStatus, message: string) {
  globalSaveStatus = { status, message };
  saveStatusListeners.forEach(listener => listener(globalSaveStatus));
}

/**
 * Hook for auto-saving user profile with debounce
 */
export function useAutoSave(options: AutoSaveOptions = {}) {
  const { debounceMs = 2000, enabled = true } = options;
  const { profile } = useUserProfileStore();
  const { getUserId } = useAuthStore();
  const timeoutRef = useRef<NodeJS.Timeout | null>(null);
  const previousProfileRef = useRef<string>('');
  const isInitialMount = useRef(true);

  useEffect(() => {
    if (!enabled) return;
    
    // 跳过初始挂载
    if (isInitialMount.current) {
      isInitialMount.current = false;
      previousProfileRef.current = JSON.stringify(profile);
      return;
    }

    const currentProfileStr = JSON.stringify(profile);
    
    // 如果profile没有变化，不执行保存
    if (currentProfileStr === previousProfileRef.current) {
      return;
    }

    previousProfileRef.current = currentProfileStr;

    // 清除之前的定时器
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // 设置新的防抖定时器
    timeoutRef.current = setTimeout(async () => {
      const userId = getUserId();
      if (!userId) {
        console.warn('[AutoSave] No user ID found');
        return;
      }

      try {
        updateSaveStatus('saving', 'Saving...');

        if (!profile) {
          console.warn('[AutoSave] No profile found');
          return;
        }

        const request: UserProfileRequest = {
          industry: profile.industry || null,
          current_role: profile.current_role || null,
          tech_stack: profile.tech_stack || [],
          primary_language: profile.primary_language || 'English',
          secondary_language: profile.secondary_language || null,
          weekly_commitment_hours: profile.weekly_commitment_hours || 10,
          learning_style: profile.learning_style || [],
          ai_personalization: profile.ai_personalization ?? true,
        };

        await saveUserProfile(userId, request);
        updateSaveStatus('saved', 'Profile saved');

        // 2秒后重置状态
        setTimeout(() => {
          if (globalSaveStatus.status === 'saved') {
            updateSaveStatus('idle', '');
          }
        }, 2000);
      } catch (error) {
        console.error('[AutoSave] Failed to save profile:', error);
        updateSaveStatus('error', 'Failed to save');
        
        // 5秒后重置错误状态
        setTimeout(() => {
          if (globalSaveStatus.status === 'error') {
            updateSaveStatus('idle', '');
          }
        }, 5000);
      }
    }, debounceMs);

    // 清理函数
    return () => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
    };
  }, [profile, enabled, debounceMs, getUserId]);
}

/**
 * Hook for reading save status
 */
export function useSaveStatus(): SaveStatusState {
  const [status, setStatus] = useState<SaveStatusState>(globalSaveStatus);

  useEffect(() => {
    const listener = (newStatus: SaveStatusState) => {
      setStatus(newStatus);
    };

    saveStatusListeners.add(listener);
    return () => {
      saveStatusListeners.delete(listener);
    };
  }, []);

  return status;
}

