# 配置文件更新指南

> 重构过程中需要更新的配置文件清单

---

## 📦 package.json 更新

### 添加新依赖

```json
{
  "dependencies": {
    "@microsoft/fetch-event-source": "^2.0.1",
    "@tanstack/react-query": "^5.60.5",
    "axios": "^1.7.7",
    "zod": "^4.1.13",
    "zustand": "^5.0.1"
  },
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/react-hooks": "^8.0.1",
    "@playwright/test": "^1.40.0",
    "msw": "^2.0.0",
    "@next/bundle-analyzer": "^14.0.0"
  }
}
```

### 更新 scripts

```json
{
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit",
    "test": "vitest",
    "test:unit": "vitest run",
    "test:watch": "vitest watch",
    "test:e2e": "playwright test",
    "test:coverage": "vitest run --coverage",
    "generate:types": "tsx scripts/generate-types.ts",
    "check:types": "tsx scripts/check-types.ts",
    "analyze": "ANALYZE=true next build",
    "prepare": "husky install"
  }
}
```

---

## ⚙️ TypeScript 配置

### tsconfig.json - 添加路径别名

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [{ "name": "next" }],
    "paths": {
      "@/*": ["./*"],
      "@/lib/*": ["./lib/*"],
      "@/components/*": ["./components/*"],
      "@/types/*": ["./types/*"],
      "@/app/*": ["./app/*"]
    },
    "baseUrl": "."
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

---

## 🧪 测试配置

### vitest.config.ts（新建）

```typescript
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'types/generated/',
        '**/*.config.ts',
        '**/*.d.ts',
      ],
    },
    globals: true,
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
    },
  },
});
```

### vitest.setup.ts（新建）

```typescript
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock environment variables
process.env.NEXT_PUBLIC_API_URL = 'http://localhost:8000/api/v1';
process.env.NEXT_PUBLIC_ENV = 'test';

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  useParams: () => ({}),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/',
}));

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
```

### playwright.config.ts（新建）

```typescript
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './__tests__/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
  },
});
```

---

## 🔨 代码质量工具

### .eslintrc.json - 更新规则

```json
{
  "extends": [
    "next/core-web-vitals",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-unused-vars": [
      "error",
      { "argsIgnorePattern": "^_" }
    ],
    "@typescript-eslint/no-explicit-any": "warn",
    "react-hooks/rules-of-hooks": "error",
    "react-hooks/exhaustive-deps": "warn",
    "no-console": ["warn", { "allow": ["warn", "error"] }],
    
    // 自定义规则：禁止直接导入生成的 API services
    "no-restricted-imports": [
      "error",
      {
        "patterns": [
          {
            "group": ["@/types/generated/services/*"],
            "message": "请使用 @/lib/api/endpoints 而不是直接使用生成的 services"
          }
        ]
      }
    ]
  }
}
```

### .prettierrc（新建）

```json
{
  "semi": true,
  "trailingComma": "es5",
  "singleQuote": true,
  "printWidth": 100,
  "tabWidth": 2,
  "useTabs": false,
  "endOfLine": "lf"
}
```

### .prettierignore（新建）

```
node_modules/
.next/
out/
build/
types/generated/
*.lock
```

---

## 🪝 Git Hooks

### 安装 Husky

```bash
npm install -D husky lint-staged
npx husky install
npx husky add .husky/pre-commit "npx lint-staged"
npx husky add .husky/pre-push "npm run type-check && npm run test:unit"
```

### .husky/pre-commit

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npx lint-staged
```

### .husky/pre-push

```bash
#!/usr/bin/env sh
. "$(dirname -- "$0")/_/husky.sh"

npm run type-check
npm run test:unit
```

### lint-staged.config.js（新建）

```javascript
module.exports = {
  '*.{ts,tsx}': [
    'eslint --fix',
    'prettier --write',
    'vitest related --run',
  ],
  '*.{json,md,css}': ['prettier --write'],
};
```

---

## 🌍 环境变量

### .env.local（新建，不提交）

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Environment
NEXT_PUBLIC_ENV=development

# Feature Flags
NEXT_PUBLIC_ENABLE_DEV_TOOLS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false
```

### .env.example（更新）

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_WS_URL=ws://localhost:8000/ws

# Environment (development | staging | production)
NEXT_PUBLIC_ENV=development

# Feature Flags
NEXT_PUBLIC_ENABLE_DEV_TOOLS=true
NEXT_PUBLIC_ENABLE_ANALYTICS=false

# Optional: Sentry (for error tracking)
# NEXT_PUBLIC_SENTRY_DSN=

# Optional: Analytics
# NEXT_PUBLIC_GA_ID=
```

---

## 📝 Next.js 配置

### next.config.js - 添加 Bundle Analyzer

```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  swcMinify: true,
  
  // Bundle Analyzer
  webpack: (config, { isServer }) => {
    if (process.env.ANALYZE === 'true') {
      const { BundleAnalyzerPlugin } = require('webpack-bundle-analyzer');
      config.plugins.push(
        new BundleAnalyzerPlugin({
          analyzerMode: 'static',
          reportFilename: isServer
            ? '../analyze/server.html'
            : './analyze/client.html',
        })
      );
    }
    return config;
  },

  // 环境变量验证
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Credentials', value: 'true' },
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'X-CSRF-Token, X-Requested-With, Accept, Accept-Version, Content-Length, Content-MD5, Content-Type, Date, X-Api-Version' },
        ],
      },
    ];
  },
};

module.exports = nextConfig;
```

---

## 🎨 Tailwind 配置

### tailwind.config.ts - 保持现有配置

```typescript
import type { Config } from 'tailwindcss';

const config: Config = {
  darkMode: ['class'],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        sage: {
          50: 'hsl(140, 15%, 97%)',
          100: 'hsl(140, 15%, 90%)',
          200: 'hsl(140, 15%, 80%)',
          300: 'hsl(140, 15%, 70%)',
          400: 'hsl(140, 15%, 60%)',
          500: 'hsl(140, 15%, 55%)',
          600: 'hsl(140, 15%, 45%)',
          700: 'hsl(140, 15%, 35%)',
          800: 'hsl(140, 15%, 25%)',
          900: 'hsl(140, 15%, 15%)',
        },
        // ... 其他颜色配置
      },
      // ... 其他主题配置
    },
  },
  plugins: [require('tailwindcss-animate')],
};

export default config;
```

---

## 📊 VS Code 配置

### .vscode/settings.json（新建）

```json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "typescript.tsdk": "node_modules/typescript/lib",
  "typescript.enablePromptUseWorkspaceTsdk": true,
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "files.exclude": {
    "**/.next": true,
    "**/node_modules": true
  },
  "search.exclude": {
    "**/.next": true,
    "**/node_modules": true,
    "**/package-lock.json": true
  }
}
```

### .vscode/extensions.json（新建）

```json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    "ZixuanChen.vitest-explorer",
    "ms-playwright.playwright"
  ]
}
```

---

## 🚀 CI/CD 配置

### .github/workflows/ci.yml（示例）

```yaml
name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
      
      - name: Install dependencies
        run: npm ci
      
      - name: Type check
        run: npm run type-check
      
      - name: Lint
        run: npm run lint
      
      - name: Unit tests
        run: npm run test:unit
      
      - name: E2E tests
        run: npm run test:e2e
      
      - name: Build
        run: npm run build
```

---

## 📦 依赖安装顺序

### 步骤 1: 安装测试框架

```bash
npm install -D vitest @testing-library/react @testing-library/react-hooks @testing-library/jest-dom
npm install -D @vitejs/plugin-react
```

### 步骤 2: 安装 E2E 测试

```bash
npm install -D @playwright/test
npx playwright install
```

### 步骤 3: 安装 MSW（Mock Service Worker）

```bash
npm install -D msw
```

### 步骤 4: 安装 SSE 支持

```bash
npm install @microsoft/fetch-event-source
```

### 步骤 5: 安装代码质量工具

```bash
npm install -D husky lint-staged prettier
npm install -D @next/bundle-analyzer
```

### 步骤 6: 初始化 Husky

```bash
npx husky install
npm pkg set scripts.prepare="husky install"
```

---

## ✅ 验证配置

### 验证 TypeScript

```bash
npm run type-check
```

### 验证 ESLint

```bash
npm run lint
```

### 验证测试框架

```bash
npm run test:unit
npm run test:e2e
```

### 验证 Git Hooks

```bash
# 创建一个测试提交
git add .
git commit -m "test: verify git hooks"
```

---

## 🔍 故障排查

### TypeScript 类型错误

```bash
# 清理 TypeScript 缓存
rm -rf .next
rm tsconfig.tsbuildinfo
npm run type-check
```

### ESLint 缓存问题

```bash
# 清理 ESLint 缓存
rm -rf .eslintcache
npm run lint
```

### 测试失败

```bash
# 清理测试缓存
npx vitest run --clearCache
```

### Playwright 问题

```bash
# 重新安装浏览器
npx playwright install
npx playwright install-deps
```

---

## 📚 参考资源

- [Vitest 文档](https://vitest.dev/)
- [Playwright 文档](https://playwright.dev/)
- [TanStack Query 文档](https://tanstack.com/query/latest)
- [Zustand 文档](https://docs.pmnd.rs/zustand/getting-started/introduction)
- [MSW 文档](https://mswjs.io/)

---

**最后更新**: 2025-12-06  
**维护者**: Frontend Team
