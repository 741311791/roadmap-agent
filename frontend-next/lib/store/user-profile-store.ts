/**
 * 用户画像状态管理 Store
 * 
 * 使用 Zustand 管理用户画像数据
 * 支持自动保存、本地缓存和乐观更新
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { getUserProfile, saveUserProfile } from '@/lib/api/endpoints';
import type { UserProfileData, TechStackItem } from '@/lib/api/endpoints';

type LearningStyleType = 'visual' | 'text' | 'audio' | 'hands_on';

export interface UserProfileState {
  // 状态
  profile: UserProfileData | null;
  isLoading: boolean;
  isSaving: boolean;
  lastSaved: Date | null;
  error: string | null;
  
  // 操作
  loadProfile: (userId: string) => Promise<void>;
  updateProfile: (updates: Partial<UserProfileData>) => void;
  saveProfile: (userId: string) => Promise<boolean>;
  
  // 技术栈操作
  addTechStack: (item: TechStackItem) => void;
  updateTechStack: (technology: string, updates: Partial<TechStackItem>) => void;
  removeTechStack: (technology: string) => void;
  
  // 学习风格操作
  toggleLearningStyle: (style: LearningStyleType) => void;
  setLearningStyles: (styles: LearningStyleType[]) => void;
  
  // 工具方法
  reset: () => void;
  getTechStack: () => TechStackItem[];
}

const initialState = {
  profile: null,
  isLoading: false,
  isSaving: false,
  lastSaved: null,
  error: null,
};

/**
 * 用户画像 Store
 * 
 * 管理用户画像数据，支持自动持久化和乐观更新
 */
export const useUserProfileStore = create<UserProfileState>()(
  persist(
    (set, get) => ({
      ...initialState,
      
      /**
       * 从后端加载用户画像
       * 
       * @param userId - 用户 ID
       */
      loadProfile: async (userId: string) => {
        set({ isLoading: true, error: null });
        
        try {
          const profile = await getUserProfile(userId);
          set({ 
            profile, 
            isLoading: false,
            error: null,
          });
          console.log('[UserProfileStore] Profile loaded:', profile);
        } catch (error) {
          console.error('[UserProfileStore] Failed to load profile:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to load profile',
            isLoading: false,
          });
        }
      },
      
      /**
       * 更新用户画像（本地更新，不立即保存）
       * 
       * @param updates - 要更新的字段
       */
      updateProfile: (updates: Partial<UserProfileData>) => {
        const { profile } = get();
        if (!profile) return;
        
        set({ 
          profile: { 
            ...profile, 
            ...updates,
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Profile updated locally:', updates);
      },
      
      /**
       * 保存用户画像到后端
       * 
       * @param userId - 用户 ID
       * @returns 成功返回 true
       */
      saveProfile: async (userId: string) => {
        const { profile } = get();
        if (!profile) return false;
        
        set({ isSaving: true, error: null });
        
        try {
          // 准备保存的数据
          const saveData = {
            industry: profile.industry,
            current_role: profile.current_role,
            tech_stack: profile.tech_stack,
            primary_language: profile.primary_language,
            secondary_language: profile.secondary_language,
            weekly_commitment_hours: profile.weekly_commitment_hours,
            learning_style: profile.learning_style,
            ai_personalization: profile.ai_personalization,
          };
          
          const updatedProfile = await saveUserProfile(userId, saveData);
          
          set({ 
            profile: updatedProfile,
            isSaving: false,
            lastSaved: new Date(),
            error: null,
          });
          
          console.log('[UserProfileStore] Profile saved successfully');
          return true;
        } catch (error) {
          console.error('[UserProfileStore] Failed to save profile:', error);
          set({ 
            error: error instanceof Error ? error.message : 'Failed to save profile',
            isSaving: false,
          });
          return false;
        }
      },
      
      /**
       * 添加技术栈项
       * 
       * @param item - 技术栈项
       */
      addTechStack: (item: TechStackItem) => {
        const { profile } = get();
        if (!profile) return;
        
        // 检查是否已存在
        const exists = profile.tech_stack.some(
          (t) => t.technology === item.technology
        );
        
        if (exists) {
          console.warn('[UserProfileStore] Tech stack already exists:', item.technology);
          return;
        }
        
        set({
          profile: {
            ...profile,
            tech_stack: [...profile.tech_stack, item],
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Tech stack added:', item.technology);
      },
      
      /**
       * 更新技术栈项
       * 
       * @param technology - 技术栈名称
       * @param updates - 要更新的字段
       */
      updateTechStack: (technology: string, updates: Partial<TechStackItem>) => {
        const { profile } = get();
        if (!profile) return;
        
        set({
          profile: {
            ...profile,
            tech_stack: profile.tech_stack.map((item) =>
              item.technology === technology
                ? { ...item, ...updates }
                : item
            ),
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Tech stack updated:', technology, updates);
      },
      
      /**
       * 移除技术栈项
       * 
       * @param technology - 技术栈名称
       */
      removeTechStack: (technology: string) => {
        const { profile } = get();
        if (!profile) return;
        
        set({
          profile: {
            ...profile,
            tech_stack: profile.tech_stack.filter(
              (item) => item.technology !== technology
            ),
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Tech stack removed:', technology);
      },
      
      /**
       * 切换学习风格
       * 
       * @param style - 学习风格
       */
      toggleLearningStyle: (style: LearningStyleType) => {
        const { profile } = get();
        if (!profile) return;
        
        const currentStyles = profile.learning_style;
        const newStyles = currentStyles.includes(style)
          ? currentStyles.filter((s) => s !== style)
          : [...currentStyles, style];
        
        set({
          profile: {
            ...profile,
            learning_style: newStyles,
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Learning style toggled:', style);
      },
      
      /**
       * 设置学习风格列表
       * 
       * @param styles - 学习风格列表
       */
      setLearningStyles: (styles: LearningStyleType[]) => {
        const { profile } = get();
        if (!profile) return;
        
        set({
          profile: {
            ...profile,
            learning_style: styles,
            updated_at: new Date().toISOString(),
          },
        });
        
        console.log('[UserProfileStore] Learning styles set:', styles);
      },
      
      /**
       * 获取技术栈列表
       * 
       * @returns 技术栈列表
       */
      getTechStack: () => {
        const { profile } = get();
        return profile?.tech_stack || [];
      },
      
      /**
       * 重置状态
       */
      reset: () => {
        set(initialState);
        console.log('[UserProfileStore] State reset');
      },
    }),
    {
      name: 'fast-learning-user-profile-storage',
      // 只持久化必要的状态
      partialize: (state) => ({ 
        profile: state.profile,
        lastSaved: state.lastSaved,
      }),
    }
  )
);

