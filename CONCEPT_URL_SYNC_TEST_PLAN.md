# Concept URL 同步修复 - 测试计划

## 📋 测试清单

### ✅ 功能测试

#### 1. 基础 Concept 切换

- [ ] **测试步骤：**
  1. 打开路线图详情页
  2. 点击左侧导航栏中的 Concept A
  3. 观察 URL 是否变为 `/roadmap/[id]?concept=A`
  4. 观察中间内容区域是否加载 Concept A 的内容
  5. 点击 Concept B
  6. 观察 URL 是否变为 `/roadmap/[id]?concept=B`
  7. 观察内容是否切换到 Concept B

- [ ] **预期结果：**
  - URL 正常切换，无循环
  - 内容正确加载
  - 浏览器控制台无错误或警告

#### 2. 深度链接访问

- [ ] **测试步骤：**
  1. 在浏览器地址栏直接输入 `/roadmap/[id]?concept=stage_1:module_2:concept_3`
  2. 按回车访问

- [ ] **预期结果：**
  - 页面加载后自动选中对应的 Concept
  - 左侧导航栏高亮显示该 Concept
  - 中间内容区域显示该 Concept 的内容

#### 3. 浏览器历史记录

- [ ] **测试步骤：**
  1. 依次访问 Concept A → B → C
  2. 点击浏览器的后退按钮
  3. 观察是否回到 Concept B
  4. 再次点击后退
  5. 观察是否回到 Concept A
  6. 点击前进按钮
  7. 观察是否前进到 Concept B

- [ ] **预期结果：**
  - 浏览器前进/后退按钮正常工作
  - URL 和内容同步切换
  - 无循环或卡顿

#### 4. 页面刷新

- [ ] **测试步骤：**
  1. 访问 `/roadmap/[id]?concept=A`
  2. 按 F5 刷新页面

- [ ] **预期结果：**
  - 刷新后自动选中 Concept A
  - URL 保持不变
  - 内容正确加载

#### 5. 分享链接

- [ ] **测试步骤：**
  1. 选中 Concept A
  2. 复制浏览器地址栏中的 URL
  3. 在新标签页中粘贴并访问

- [ ] **预期结果：**
  - 新标签页中正确打开并选中 Concept A
  - 内容正确显示

### 🔍 性能测试

#### 6. 无循环验证

- [ ] **测试步骤：**
  1. 打开浏览器开发者工具的 Network 面板
  2. 点击切换 Concept
  3. 观察 Network 面板中的请求数量

- [ ] **预期结果：**
  - 每次切换只触发 1 次内容加载请求
  - 无重复或多余的请求

- [ ] **测试步骤（控制台日志）：**
  1. 打开浏览器控制台
  2. 点击切换 Concept
  3. 观察控制台输出

- [ ] **预期结果：**
  - 只看到一次 "Navigating to concept" 日志
  - 只看到一次 "Syncing concept from URL" 日志
  - 无重复日志

#### 7. 快速连续切换

- [ ] **测试步骤：**
  1. 快速连续点击多个不同的 Concepts（A → B → C → D）
  2. 观察 URL 和内容是否正常切换

- [ ] **预期结果：**
  - 所有切换都正常完成
  - 最终显示最后一个点击的 Concept
  - 无卡顿或错误

### 🚨 边界情况测试

#### 8. 无效的 Concept ID

- [ ] **测试步骤：**
  1. 在地址栏输入 `/roadmap/[id]?concept=invalid_concept_id`
  2. 访问该 URL

- [ ] **预期结果：**
  - 页面正常加载，但不选中任何 Concept
  - 控制台显示警告："Invalid concept ID in URL"
  - 无错误或崩溃

#### 9. 特殊字符的 Concept ID

- [ ] **测试步骤：**
  1. 点击包含特殊字符的 Concept（如 `stage_1:module_2:concept_3`）
  2. 观察 URL 中的编码

- [ ] **预期结果：**
  - URL 正确编码特殊字符（如冒号编码为 `%3A`）
  - 内容正确加载
  - 刷新后仍能正确恢复

#### 10. 空 Concept 参数

- [ ] **测试步骤：**
  1. 访问 `/roadmap/[id]?concept=`（concept 参数为空）
  2. 观察页面状态

- [ ] **预期结果：**
  - 页面正常加载
  - 不选中任何 Concept
  - 中间内容区域显示提示信息

#### 11. 多个路线图切换

- [ ] **测试步骤：**
  1. 访问 Roadmap A 并选中 Concept X
  2. 访问 Roadmap B
  3. 观察是否自动清空选中状态

- [ ] **预期结果：**
  - 切换路线图后，选中状态正确重置
  - 无残留的旧 Concept 数据

## 🐛 Bug 验证

### 原 Bug 验证（确保已修复）

- [ ] **测试步骤：**
  1. 选中 Concept A
  2. 点击 Concept B
  3. 观察浏览器地址栏

- [ ] **预期结果：**
  - ✅ URL 稳定在 `/roadmap/[id]?concept=B`
  - ✅ 无频繁切换或闪烁
  - ✅ 浏览器历史记录中只有一条记录

- [ ] **失败标志（Bug 未修复）：**
  - ❌ URL 在 `?concept=A` 和 `?concept=B` 之间快速切换
  - ❌ 浏览器历史记录中出现大量重复记录
  - ❌ 内容区域闪烁或重复加载

## 🔧 开发者工具检查

### 控制台日志

打开控制台，切换 Concept 时应该看到以下日志模式：

```
[RoadmapDetail] Navigating to concept: concept_b
[RoadmapDetail] Syncing concept from URL: concept_b
```

**正常模式：** 每次切换只出现上述两条日志各一次

**异常模式（Bug 未修复）：**
```
[RoadmapDetail] Navigating to concept: concept_b
[RoadmapDetail] Syncing concept from URL: concept_b
[RoadmapDetail] Syncing concept from URL: concept_b
[RoadmapDetail] Syncing concept from URL: concept_b
... (重复多次)
```

### React DevTools

- [ ] 打开 React DevTools
- [ ] 选中 `RoadmapDetailPage` 组件
- [ ] 点击切换 Concept
- [ ] 观察 `selectedConceptId` state 的变化次数

**预期：** 每次切换只变化一次

### Performance 分析

- [ ] 打开 Chrome DevTools 的 Performance 面板
- [ ] 开始录制
- [ ] 切换 Concept
- [ ] 停止录制
- [ ] 观察是否有重复的渲染或函数调用

**预期：** 无明显的重复渲染峰值

## 📊 测试报告模板

```markdown
## 测试结果

**测试日期：** YYYY-MM-DD
**测试人员：** [姓名]
**测试环境：**
- 浏览器：Chrome / Firefox / Safari [版本号]
- 操作系统：Windows / macOS / Linux

### 功能测试
- [x] 基础 Concept 切换 - ✅ 通过
- [x] 深度链接访问 - ✅ 通过
- [x] 浏览器历史记录 - ✅ 通过
- [x] 页面刷新 - ✅ 通过
- [x] 分享链接 - ✅ 通过

### 性能测试
- [x] 无循环验证 - ✅ 通过
- [x] 快速连续切换 - ✅ 通过

### 边界情况测试
- [x] 无效的 Concept ID - ✅ 通过
- [x] 特殊字符的 Concept ID - ✅ 通过
- [x] 空 Concept 参数 - ✅ 通过
- [x] 多个路线图切换 - ✅ 通过

### Bug 验证
- [x] 原 Bug 已修复 - ✅ 确认

### 发现的问题
1. [如有问题，在此列出]

### 总结
[测试总结]
```

## 🎯 自动化测试脚本

创建 E2E 测试（使用 Playwright）：

```typescript
// e2e/concept-url-sync.spec.ts
import { test, expect } from '@playwright/test';

test.describe('Concept URL Sync', () => {
  test('should not cause URL loop when switching concepts', async ({ page }) => {
    // 访问路线图页面
    await page.goto('/roadmap/test-roadmap-id');
    
    // 记录 URL 变化次数
    let urlChangeCount = 0;
    page.on('framenavigated', () => {
      urlChangeCount++;
    });
    
    // 点击 Concept A
    await page.click('[data-concept-id="concept_a"]');
    await page.waitForURL('**/roadmap/test-roadmap-id?concept=concept_a');
    
    // 重置计数器
    const beforeCount = urlChangeCount;
    
    // 点击 Concept B
    await page.click('[data-concept-id="concept_b"]');
    await page.waitForURL('**/roadmap/test-roadmap-id?concept=concept_b');
    
    // 验证 URL 只变化了一次
    expect(urlChangeCount - beforeCount).toBe(1);
    
    // 验证内容正确加载
    await expect(page.locator('h1')).toContainText('Concept B');
  });

  test('should support deep linking', async ({ page }) => {
    // 直接访问带 concept 参数的 URL
    await page.goto('/roadmap/test-roadmap-id?concept=concept_c');
    
    // 验证自动选中
    await expect(page.locator('[data-concept-id="concept_c"]')).toHaveClass(/active/);
    
    // 验证内容加载
    await expect(page.locator('h1')).toContainText('Concept C');
  });

  test('should work with browser back/forward', async ({ page }) => {
    await page.goto('/roadmap/test-roadmap-id');
    
    // 依次访问多个 Concepts
    await page.click('[data-concept-id="concept_a"]');
    await page.waitForURL('**/concept=concept_a');
    
    await page.click('[data-concept-id="concept_b"]');
    await page.waitForURL('**/concept=concept_b');
    
    // 后退
    await page.goBack();
    await expect(page).toHaveURL(/concept=concept_a/);
    
    // 前进
    await page.goForward();
    await expect(page).toHaveURL(/concept=concept_b/);
  });
});
```

## 📞 问题上报

如果测试发现问题，请提供以下信息：

1. **测试步骤**：详细描述如何重现问题
2. **预期结果**：应该发生什么
3. **实际结果**：实际发生了什么
4. **截图/视频**：如有可能，提供问题的可视化证据
5. **控制台日志**：复制控制台中的错误或警告信息
6. **环境信息**：浏览器版本、操作系统等

## 🎉 测试完成标准

所有测试项都标记为 ✅ 通过，且：
- 无重复的 Network 请求
- 控制台无错误或警告
- URL 切换流畅，无卡顿
- 浏览器历史记录正常
- 深度链接功能正常

## 📚 相关文档

- [Concept URL 同步修复说明](./CONCEPT_URL_SYNC_FIX.md)
- [Concept 深度链接与性能优化](./CONCEPT_DEEP_LINKING_AND_PERFORMANCE.md)
