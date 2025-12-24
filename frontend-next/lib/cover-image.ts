/**
 * Cover Image Utility
 * 
 * Provides functions for generating cover images using Unsplash
 * with beautiful gradient fallbacks when images fail to load.
 */

// API 配置
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Unsplash image configuration
const UNSPLASH_BASE = 'https://images.unsplash.com';

// 封面图缓存（避免重复请求）
const coverImageCache = new Map<string, string | null>();

// Topic to Unsplash image mapping with curated high-quality images
const TOPIC_IMAGE_MAP: Record<string, string> = {
  // Programming Languages
  python: 'photo-1526379095098-d400fd0bf935',
  javascript: 'photo-1627398242454-45a1465c2479',
  typescript: 'photo-1516116216624-53e697fedbea',
  java: 'photo-1517694712202-14dd9538aa97',
  rust: 'photo-1558494949-ef010cbdcc31',
  go: 'photo-1555949963-ff9fe0c870eb',
  cpp: 'photo-1629654297299-c8506221ca97',
  
  // Web Development
  react: 'photo-1633356122544-f134324a6cee',
  nextjs: 'photo-1618477388954-7852f32655ec',
  vue: 'photo-1614741118887-7a4ee193a5fa',
  angular: 'photo-1593720213428-28a5b9e94613',
  frontend: 'photo-1507003211169-0a1dd7228f2d',
  backend: 'photo-1558494949-ef010cbdcc31',
  fullstack: 'photo-1571171637578-41bc2dd41cd2',
  web: 'photo-1460925895917-afdab827c52f',
  
  // Data & AI
  'data science': 'photo-1551288049-bebda4e38f71',
  'machine learning': 'photo-1555255707-c07966088b7b',
  ai: 'photo-1677442136019-21780ecad995',
  'deep learning': 'photo-1620712943543-bcc4688e7485',
  analytics: 'photo-1551288049-bebda4e38f71',
  
  // Cloud & DevOps
  aws: 'photo-1451187580459-43490279c0fa',
  cloud: 'photo-1544197150-b99a580bb7a8',
  devops: 'photo-1667372393119-3d4c48d07fc9',
  kubernetes: 'photo-1667372393119-3d4c48d07fc9',
  docker: 'photo-1605745341112-85968b19335b',
  
  // Mobile
  mobile: 'photo-1512941937669-90a1b58e7e9c',
  ios: 'photo-1512941937669-90a1b58e7e9c',
  android: 'photo-1607252650355-f7fd0460ccdb',
  flutter: 'photo-1617040619263-41c5a9ca7521',
  
  // Design
  design: 'photo-1561070791-2526d30994b5',
  ui: 'photo-1545235617-9465d2a55698',
  ux: 'photo-1586717791821-3f44a563fa4c',
  
  // Database
  database: 'photo-1544383835-bda2bc66a55d',
  sql: 'photo-1544383835-bda2bc66a55d',
  mongodb: 'photo-1558494949-ef010cbdcc31',
  
  // Security
  security: 'photo-1555949963-aa79dcee981c',
  cybersecurity: 'photo-1550751827-4bd374c3f58b',
  
  // General Tech
  programming: 'photo-1461749280684-dccba630e2f6',
  coding: 'photo-1515879218367-8466d910aaa4',
  technology: 'photo-1518770660439-4636190af475',
  software: 'photo-1504639725590-34d0984388bd',
  
  // Default fallbacks
  default: 'photo-1516321318423-f06f85e504b3',
  learning: 'photo-1434030216411-0b793f4b4173',
  study: 'photo-1456513080510-7bf3a84b82f8',
};

// Beautiful gradient combinations for fallbacks
const GRADIENT_PALETTES = [
  { from: 'from-emerald-500', to: 'to-teal-700', text: 'text-white' },
  { from: 'from-sage-400', to: 'to-sage-700', text: 'text-white' },
  { from: 'from-indigo-500', to: 'to-purple-700', text: 'text-white' },
  { from: 'from-amber-400', to: 'to-orange-600', text: 'text-white' },
  { from: 'from-rose-400', to: 'to-pink-700', text: 'text-white' },
  { from: 'from-cyan-400', to: 'to-blue-600', text: 'text-white' },
  { from: 'from-violet-500', to: 'to-indigo-700', text: 'text-white' },
  { from: 'from-lime-400', to: 'to-green-600', text: 'text-white' },
  { from: 'from-fuchsia-500', to: 'to-pink-700', text: 'text-white' },
  { from: 'from-sky-400', to: 'to-cyan-600', text: 'text-white' },
];

/**
 * Generate a deterministic hash from a string
 */
function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash = hash & hash;
  }
  return Math.abs(hash);
}

/**
 * 从后端 API 获取路线图封面图 URL（带缓存）
 * 
 * @param roadmapId - 路线图 ID
 * @returns 封面图 URL，如果不存在返回 null
 */
export async function fetchCoverImageFromAPI(roadmapId: string): Promise<string | null> {
  // 检查缓存
  if (coverImageCache.has(roadmapId)) {
    return coverImageCache.get(roadmapId) || null;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/v1/roadmap/${roadmapId}/cover-image`, {
      credentials: 'include',
      // 添加超时和缓存控制
      signal: AbortSignal.timeout(5000), // 5秒超时
    });
    
    if (!response.ok) {
      coverImageCache.set(roadmapId, null);
      return null;
    }
    
    const data = await response.json();
    
    // 只有在成功生成的情况下才返回 URL
    if (data.status === 'success' && data.cover_image_url) {
      const url = data.cover_image_url;
      coverImageCache.set(roadmapId, url);
      return url;
    }
    
    coverImageCache.set(roadmapId, null);
    return null;
  } catch (error) {
    // 超时或其他错误，不记录到缓存，允许重试
    if (error instanceof Error && error.name === 'TimeoutError') {
      console.warn('Cover image fetch timeout:', roadmapId);
    } else {
      console.error('Failed to fetch cover image from API:', error);
    }
    return null;
  }
}

/**
 * Get a cover image URL based on the topic
 * Uses Unsplash for high-quality images
 * 
 * @param topic - The topic/title of the roadmap
 * @param width - Desired image width (default: 800)
 * @param height - Desired image height (default: 600)
 * @returns Unsplash image URL
 */
export function getCoverImage(
  topic: string,
  width: number = 800,
  height: number = 600
): string {
  const normalizedTopic = topic.toLowerCase().trim();
  
  // Try to find a matching image
  let imageId = TOPIC_IMAGE_MAP.default;
  
  // Check for exact match first
  if (TOPIC_IMAGE_MAP[normalizedTopic]) {
    imageId = TOPIC_IMAGE_MAP[normalizedTopic];
  } else {
    // Check for partial matches
    for (const [key, value] of Object.entries(TOPIC_IMAGE_MAP)) {
      if (normalizedTopic.includes(key) || key.includes(normalizedTopic)) {
        imageId = value;
        break;
      }
    }
  }
  
  return `${UNSPLASH_BASE}/${imageId}?w=${width}&h=${height}&fit=crop&q=80`;
}

/**
 * 获取封面图 URL（优先使用后端生成的封面图，降级到 Unsplash）
 * 
 * @param roadmapId - 路线图 ID（可选）
 * @param topic - 主题/标题（用于 Unsplash 降级）
 * @param width - 图片宽度
 * @param height - 图片高度
 * @returns 封面图 URL
 */
export async function getCoverImageWithFallback(
  roadmapId: string | undefined,
  topic: string,
  width: number = 800,
  height: number = 600
): Promise<string> {
  // 如果有 roadmap_id，尝试从 API 获取
  if (roadmapId) {
    const apiUrl = await fetchCoverImageFromAPI(roadmapId);
    if (apiUrl) {
      return apiUrl;
    }
  }
  
  // 降级到 Unsplash
  return getCoverImage(topic, width, height);
}

/**
 * Get a gradient fallback configuration for a topic
 * Returns consistent gradient for the same topic
 * 
 * @param topic - The topic/title of the roadmap
 * @returns Gradient configuration with Tailwind classes
 */
export function getGradientFallback(topic: string): {
  from: string;
  to: string;
  text: string;
  className: string;
} {
  const hash = hashString(topic);
  const palette = GRADIENT_PALETTES[hash % GRADIENT_PALETTES.length];
  
  return {
    ...palette,
    className: `bg-gradient-to-br ${palette.from} ${palette.to}`,
  };
}

/**
 * Get the initial/icon for a topic (first letter capitalized)
 * 
 * @param topic - The topic/title of the roadmap
 * @returns The first letter capitalized
 */
export function getTopicInitial(topic: string): string {
  return topic.trim().charAt(0).toUpperCase();
}

/**
 * Check if an image URL is valid/loadable
 * 
 * @param url - The image URL to check
 * @returns Promise that resolves to true if image loads successfully
 */
export function checkImageValidity(url: string): Promise<boolean> {
  return new Promise((resolve) => {
    if (typeof window === 'undefined') {
      resolve(true);
      return;
    }
    
    const img = new Image();
    img.onload = () => resolve(true);
    img.onerror = () => resolve(false);
    img.src = url;
  });
}

