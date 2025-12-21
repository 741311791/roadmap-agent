/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  
  // 性能优化：启用 SWC 压缩
  swcMinify: true,
  
  // 编译优化
  compiler: {
    // 生产环境移除 console.log
    removeConsole: process.env.NODE_ENV === 'production' ? {
      exclude: ['error', 'warn'],
    } : false,
  },
  
  // 实验性功能：优化包导入
  experimental: {
    // 自动优化包导入，减少 bundle 大小
    optimizePackageImports: [
      'lucide-react',
      '@radix-ui/react-avatar',
      '@radix-ui/react-dialog',
      '@radix-ui/react-dropdown-menu',
      '@radix-ui/react-checkbox',
      '@radix-ui/react-label',
      '@radix-ui/react-progress',
      '@radix-ui/react-radio-group',
      '@radix-ui/react-scroll-area',
      '@radix-ui/react-select',
      '@radix-ui/react-separator',
      '@radix-ui/react-slider',
      '@radix-ui/react-slot',
      '@radix-ui/react-switch',
      '@radix-ui/react-tabs',
    ],
  },
  
  // 模块化导入优化（tree-shaking）
  modularizeImports: {
    'lucide-react': {
      transform: 'lucide-react/dist/esm/icons/{{kebabCase member}}',
      skipDefaultConversion: true,
    },
  },
  
  // 配置外部图片
  images: {
    remotePatterns: [
      {
        protocol: 'https',
        hostname: 'images.unsplash.com',
        pathname: '/**',
      },
      {
        protocol: 'https',
        hostname: 'pub-443fbce7c4544cb2905ed48fe58e66e8.r2.dev',
        pathname: '/**',
      },
    ],
    // 禁用某些域名的图片优化以避免连接问题
    unoptimized: false,
    // 增加超时时间
    minimumCacheTTL: 60,
    // 允许的图片格式
    formats: ['image/avif', 'image/webp'],
  },
  
  // 开发环境 API 代理
  async rewrites() {
    return [
      {
        source: '/api/v1/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/v1/:path*`,
      },
    ];
  },
};

module.exports = nextConfig;

