# Pull Request

## Description

<!-- 简要描述本次 PR 的目的和内容 -->

## Type of Change

<!-- 请勾选适用的选项 -->

- [ ] 🐛 Bug fix (修复问题)
- [ ] ✨ New feature (新功能)
- [ ] 💥 Breaking change (破坏性变更)
- [ ] 📝 Documentation (文档更新)
- [ ] ♻️ Refactor (代码重构)
- [ ] 🎨 Style (代码格式调整)
- [ ] ⚡ Performance (性能优化)
- [ ] ✅ Test (测试相关)
- [ ] 🔧 Chore (构建/工具链相关)

## Backend Schema Changes

<!-- 如果修改了后端 Schema/API，请勾选以下项 -->

- [ ] 修改了 Pydantic Models (`backend/app/schemas/`)
- [ ] 修改了 API 路由 (`backend/app/api/`)
- [ ] 修改了数据库模型 (`backend/app/models/`)

### Schema Sync Checklist

<!-- 如果勾选了上述任何一项，请完成以下步骤 -->

- [ ] 已运行 `make sync` 或 `npm run generate:types` 生成前端类型
- [ ] 已提交生成的类型文件 (`frontend-next/types/generated/`)
- [ ] 已提交 Schema 缓存 (`frontend-next/.openapi-cache.json`)
- [ ] 已运行 `npm run type-check` 验证类型正确性
- [ ] 已更新前端调用代码（如有 Breaking Changes）

## Breaking Changes

<!-- 如果有破坏性变更，请详细说明 -->

- [ ] 移除了 API 端点
- [ ] 修改了请求/响应格式
- [ ] 修改了字段类型或名称

**迁移指南**:
<!-- 如果有 Breaking Changes，请提供迁移指南 -->

```typescript
// Before
const response = await oldApi();

// After
const response = await newApi();
```

## Testing

<!-- 描述如何测试本次变更 -->

- [ ] 已添加单元测试
- [ ] 已添加集成测试
- [ ] 已手动测试功能
- [ ] 已验证前后端集成

## Screenshots / Videos

<!-- 如果有 UI 变更，请提供截图或视频 -->

## Checklist

- [ ] 代码遵循项目规范
- [ ] 已添加必要的注释（中文）
- [ ] 已更新相关文档
- [ ] 没有引入新的 linter 错误
- [ ] 所有测试通过
- [ ] 已自测功能正常

## Related Issues

<!-- 关联的 Issue 编号，例如: Closes #123 -->

## Additional Notes

<!-- 其他需要说明的内容 -->

---

## For Reviewers

### Review Checklist

- [ ] 代码质量和可读性
- [ ] 测试覆盖率
- [ ] 文档完整性
- [ ] 前后端类型同步（如适用）
- [ ] Breaking Changes 处理（如适用）
- [ ] 性能影响评估

### Schema Sync Validation

如果 PR 包含后端 Schema 变更，请验证：

1. CI 中的 "Schema Sync Check" 通过
2. `frontend-next/types/generated/` 已更新
3. `.openapi-cache.json` 已更新
4. 前端类型检查通过

如果 CI 失败，请要求作者运行：

```bash
make sync
git add frontend-next/types/generated/ frontend-next/.openapi-cache.json
git commit --amend --no-edit
git push --force-with-lease
```

