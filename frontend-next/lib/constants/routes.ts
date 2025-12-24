/**
 * 路由常量
 */

/**
 * 应用路由
 * 注意：使用路由组 (app)，URL 中不包含 /app 前缀
 */
export const APP_ROUTES = {
  HOME: '/home',
  NEW_ROADMAP: '/new',
  ROADMAPS: '/roadmaps',
  ROADMAP_DETAIL: (id: string) => `/roadmap/${id}`,
  ROADMAP_LEARN: (id: string, conceptId: string) => `/roadmap/${id}/learn/${conceptId}`,
  PROFILE: '/profile',
  SETTINGS: '/settings',
} as const;

/**
 * 营销页面路由
 */
export const MARKETING_ROUTES = {
  LANDING: '/',
  PRICING: '/pricing',
  METHODOLOGY: '/methodology',
} as const;

/**
 * 认证路由
 */
export const AUTH_ROUTES = {
  LOGIN: '/login',
  REGISTER: '/register',
  LOGOUT: '/logout',
} as const;
