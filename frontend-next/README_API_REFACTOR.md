# Frontend API Refactor - Quick Reference

## 🚀 Quick Start

```bash
# 1. Generate types
npm run generate:types

# 2. Run tests
npm run test

# 3. Type check
npm run type-check

# 4. Start dev server
npm run dev
```

---

## 📦 New API Structure

### Import Pattern

```typescript
// ✅ Recommended: Import by business domain
import { 
  authApi,      // Authentication & Authorization
  usersApi,     // User Management
  tasksApi,     // Task Management (NEW)
  roadmapsApi,  // Roadmap Management
  contentApi,   // Content Management
  adminApi,     // Platform Admin (NEW)
} from '@/lib/api/endpoints';
```

---

## 🔄 API Migration Map

### Tasks API (NEW)

| Old | New |
|-----|-----|
| `roadmapsApi.generate()` | `tasksApi.generate()` |
| `/workflows/generation/generate` | `/tasks/generate` |
| `/admin/trace/{id}/logs` | `/tasks/{id}/logs` |

```typescript
// Before
import { generateRoadmapAsync } from '@/lib/api/endpoints';
const result = await generateRoadmapAsync(request);

// After
import { tasksApi } from '@/lib/api/endpoints';
const result = await tasksApi.generate(request);
```

---

### Roadmaps API

| Old | New | Param Change |
|-----|-----|-------------|
| `/users/{id}/roadmaps` | `/roadmaps/users/{id}` | - |
| `delete(id, userId)` | `delete(id)` | ❌ Remove userId |
| `restore(id, userId)` | `restore(id)` | ❌ Remove userId |

```typescript
// Before
import { deleteRoadmap } from '@/lib/api/endpoints';
await deleteRoadmap(roadmapId, userId);

// After
import { roadmapsApi } from '@/lib/api/endpoints';
await roadmapsApi.delete(roadmapId);  // userId from JWT
```

---

### Users API

| Old | New | Param Change |
|-----|-----|-------------|
| `/users/{userId}/profile` | `/users/profile` | ❌ Remove userId |

```typescript
// Before
import { getUserProfile } from '@/lib/api/endpoints';
const profile = await getUserProfile(userId);

// After
import { usersApi } from '@/lib/api/endpoints';
const profile = await usersApi.getUserProfile();  // userId from JWT
```

---

## 🛠️ Error Handling

```typescript
import { handleApiError } from '@/lib/utils/error-handler';

try {
  const data = await tasksApi.generate(request);
} catch (error) {
  handleApiError(error, { 
    context: 'Task Generation',
    showToast: true,
  });
}
```

---

## 📝 Type System

```typescript
// ✅ Auto-generated types (from backend)
import type { RoadmapFramework, Concept } from '@/types/generated';

// ✅ Frontend-specific types
import type { RoadmapWithUI, ViewMode } from '@/types/custom/api';

// ✅ Store types
import type { RoadmapStore, TaskStore } from '@/types/custom/store';
```

---

## 🔗 Documentation

- [API Migration Guide](docs/API_MIGRATION_GUIDE.md)
- [Frontend API Refactor Summary](../doc/20260117_前端API重构完成总结.md)
- [Backend API Refactor Summary](../doc/20260114_API路由重构完成总结.md)

---

**Last Updated**: 2026-01-17  
**Status**: ✅ Core refactor completed (80%)

