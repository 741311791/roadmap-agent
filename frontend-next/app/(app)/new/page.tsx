/**
 * New Roadmap Page - Server Component
 * 
 * 性能优化：
 * - 服务端组件减少客户端 bundle 大小
 * - 可选服务端数据预取
 */

import NewRoadmapClient from './new-roadmap-client';

export const metadata = {
  title: 'Create Learning Roadmap | Fast Learning',
  description: 'Create a personalized AI-powered learning roadmap',
};

export default async function NewRoadmapPage() {
  // 可选：服务端预取数据
  // 暂时不实现，因为需要用户认证信息
  // 未来可以通过 cookies 获取用户信息并预取 profile
  
  return <NewRoadmapClient />;
}
