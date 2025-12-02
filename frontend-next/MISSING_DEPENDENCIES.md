# 缺失依赖安装指南

在运行项目前，请安装以下缺失的依赖包：

## 必需依赖

### 1. highlight.js (代码语法高亮)

```bash
npm install highlight.js
```

或使用 pnpm:

```bash
pnpm add highlight.js
```

## 安装所有依赖

如果你还没有安装项目依赖，请运行:

```bash
npm install
```

这将安装 `package.json` 中列出的所有依赖，包括:
- react-markdown
- remark-gfm
- rehype-highlight
- 以及其他所有必需的包

## 验证安装

安装完成后，运行以下命令验证:

```bash
npm run type-check
```

如果没有类型错误，说明依赖安装成功。

## 已创建的 UI 组件

以下 shadcn/ui 组件已自动创建:
- ✅ Skeleton
- ✅ Input
- ✅ Textarea

这些组件已添加到 `components/ui/index.ts` 中。

