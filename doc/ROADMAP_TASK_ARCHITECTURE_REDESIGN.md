# Roadmap Task Architecture Redesign

> **Date**: 2025-12-12  
> **Type**: Architecture Improvement  
> **Priority**: High  
> **Status**: 📋 Design Proposal

---

## 📋 Problem Analysis

### 1. Current Architecture Issues

#### Issue A: `roadmap_metadata.task_id` is Too Restrictive

**Current Schema**:
```sql
CREATE TABLE roadmap_metadata (
    roadmap_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    task_id VARCHAR NOT NULL,  -- ❌ Only stores the CREATION task
    title VARCHAR NOT NULL,
    framework_data JSON NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

**Problem**:
- A roadmap can have **multiple tasks** (creation + retry tasks)
- But `task_id` only stores the initial creation task
- Retry tasks are **not linked** to the roadmap in the database
- `checkRoadmapStatusQuick()` can't detect active retry tasks

#### Issue B: Retry Tasks Not Persisted

**Code Analysis**:

| Task Type | Creates `RoadmapTask`? | Updates `roadmap_metadata`? | WebSocket? |
|-----------|------------------------|----------------------------|------------|
| **Roadmap Creation** | ✅ Yes (`repo.create_task()`) | ✅ Yes | ✅ Yes |
| **Batch Retry** (`/retry-failed`) | ✅ Yes (`repo.create_task()`) | ❌ No | ✅ Yes |
| **Single Concept Retry** (`/concepts/{id}/tutorial/retry`) | ❌ **No** | ❌ No | ✅ Yes |

**Evidence** (from `backend/app/api/v1/endpoints/generation.py`):

```python
# retry_tutorial/retry_resources/retry_quiz endpoints
@router.post("/{roadmap_id}/concepts/{concept_id}/tutorial/retry")
async def retry_tutorial(...):
    # Generate task_id
    task_id = _generate_retry_task_id(roadmap_id, concept_id, "tutorial")
    
    # ❌ Missing: No repo.create_task() call
    # ❌ Missing: No task persistence
    # ✅ Only: WebSocket events
    
    # Update concept status
    await _update_concept_status_in_framework(...)
    
    # Publish WebSocket events
    await notification_service.publish_concept_start(task_id, ...)
```

**Consequences**:
1. ❌ No task record in `roadmap_tasks` table
2. ❌ No execution logs in `roadmap_execution_logs`
3. ❌ Can't query task status after WebSocket disconnects
4. ❌ Can't detect stale status (task killed but status stuck at 'generating')
5. ❌ No audit trail for retry operations

#### Issue C: Stale Status Detection is Broken

**Current Logic** (`backend/app/api/v1/roadmap.py:327-412`):

```python
@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status_quick(roadmap_id: str, ...):
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    
    # ❌ Only checks the CREATION task
    task = await repo.get_task(metadata.task_id)
    has_active_task = task and task.status in ['pending', 'processing', ...]
    
    # ❌ Missing: Retry tasks are NOT checked
    # Result: False positives for stale status
```

**Scenario**:
1. User creates roadmap → `task_id = "task-001"` (completed)
2. User retries resources → `task_id = "task-002"` (active, but **not persisted**)
3. User switches tabs and returns
4. Frontend calls `checkRoadmapStatusQuick(roadmap_id)`
5. Backend checks `metadata.task_id` (`"task-001"`) → status: `completed`
6. Backend sees `resources_status = 'generating'` but no active task
7. **False positive**: Marked as "stale status" ❌

---

## ✅ Proposed Solution: Task-Roadmap Linking Table

### New Schema Design

#### 1. Add `roadmap_task_links` Table (Many-to-Many)

```sql
CREATE TABLE roadmap_task_links (
    id SERIAL PRIMARY KEY,
    roadmap_id VARCHAR NOT NULL,
    task_id VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,  -- 'creation', 'retry_tutorial', 'retry_resources', 'retry_quiz', 'retry_batch'
    concept_id VARCHAR,           -- For single-concept retries
    content_type VARCHAR,         -- 'tutorial', 'resources', 'quiz' (for single-concept retries)
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    
    UNIQUE(roadmap_id, task_id),
    INDEX(roadmap_id, created_at DESC),  -- Query latest tasks for a roadmap
    INDEX(task_id)
);
```

**Benefits**:
- ✅ One roadmap can have multiple tasks
- ✅ Can query all tasks (creation + retries) for a roadmap
- ✅ Preserves audit trail
- ✅ Enables accurate stale status detection

#### 2. Keep `roadmap_metadata.task_id` for Backward Compatibility

```sql
-- Keep existing column, but mark as deprecated
ALTER TABLE roadmap_metadata 
    ADD COLUMN task_id_deprecated VARCHAR;  -- Optional: Rename in migration

-- Or add a computed column for convenience
ALTER TABLE roadmap_metadata
    ADD COLUMN latest_task_id VARCHAR GENERATED ALWAYS AS (
        SELECT task_id FROM roadmap_task_links 
        WHERE roadmap_id = roadmap_metadata.roadmap_id 
        ORDER BY created_at DESC LIMIT 1
    ) STORED;
```

**Alternative (Cleaner)**:
```sql
-- Remove task_id from roadmap_metadata entirely
ALTER TABLE roadmap_metadata DROP COLUMN task_id;

-- Query latest task via roadmap_task_links
```

#### 3. Update `roadmap_tasks` Table (No Changes Needed)

```sql
-- Current schema is fine
CREATE TABLE roadmap_tasks (
    task_id VARCHAR PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'pending',  -- pending, processing, completed, failed
    current_step VARCHAR DEFAULT 'init',
    user_request JSON,
    roadmap_id VARCHAR,  -- Can be NULL initially (set after intent_analysis)
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## 🔧 Implementation Plan

### Phase 1: Database Schema Migration

**Migration File**: `backend/alembic/versions/XXXX_add_roadmap_task_links.py`

```python
"""Add roadmap_task_links table for many-to-many relationship

Revision ID: XXXX
Revises: YYYY
Create Date: 2025-12-12
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    # 1. Create roadmap_task_links table
    op.create_table(
        'roadmap_task_links',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('roadmap_id', sa.String(), nullable=False),
        sa.Column('task_id', sa.String(), nullable=False),
        sa.Column('task_type', sa.String(), nullable=False),
        sa.Column('concept_id', sa.String(), nullable=True),
        sa.Column('content_type', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
    )
    
    # 2. Add indexes
    op.create_index('idx_roadmap_task_links_roadmap_id', 'roadmap_task_links', ['roadmap_id', 'created_at'], postgresql_using='btree')
    op.create_index('idx_roadmap_task_links_task_id', 'roadmap_task_links', ['task_id'])
    
    # 3. Add unique constraint
    op.create_unique_constraint('uq_roadmap_task_links', 'roadmap_task_links', ['roadmap_id', 'task_id'])
    
    # 4. Migrate existing data (optional: preserve history)
    # Populate roadmap_task_links from existing roadmap_metadata.task_id
    op.execute("""
        INSERT INTO roadmap_task_links (roadmap_id, task_id, task_type, created_at)
        SELECT roadmap_id, task_id, 'creation', created_at
        FROM roadmap_metadata
        WHERE task_id IS NOT NULL
    """)
    
    # 5. Optional: Mark old column as deprecated (don't drop yet for safety)
    # op.alter_column('roadmap_metadata', 'task_id', new_column_name='task_id_deprecated')

def downgrade():
    op.drop_table('roadmap_task_links')
    # op.alter_column('roadmap_metadata', 'task_id_deprecated', new_column_name='task_id')
```

### Phase 2: Repository Layer Updates

**File**: `backend/app/db/repositories/roadmap_repo.py`

```python
class RoadmapRepository:
    
    # ✅ New method: Link task to roadmap
    async def link_task_to_roadmap(
        self,
        roadmap_id: str,
        task_id: str,
        task_type: str,  # 'creation', 'retry_tutorial', 'retry_resources', 'retry_quiz', 'retry_batch'
        concept_id: str | None = None,
        content_type: str | None = None,
    ) -> None:
        """
        将任务关联到路线图（支持多对多关系）
        
        Args:
            roadmap_id: 路线图 ID
            task_id: 任务 ID
            task_type: 任务类型
            concept_id: 概念 ID（单 Concept 重试时需要）
            content_type: 内容类型（单 Concept 重试时需要）
        """
        query = text("""
            INSERT INTO roadmap_task_links (roadmap_id, task_id, task_type, concept_id, content_type)
            VALUES (:roadmap_id, :task_id, :task_type, :concept_id, :content_type)
            ON CONFLICT (roadmap_id, task_id) DO NOTHING
        """)
        
        await self.session.execute(
            query,
            {
                "roadmap_id": roadmap_id,
                "task_id": task_id,
                "task_type": task_type,
                "concept_id": concept_id,
                "content_type": content_type,
            }
        )
    
    # ✅ New method: Get active tasks for roadmap
    async def get_active_tasks_for_roadmap(self, roadmap_id: str) -> list[RoadmapTask]:
        """
        获取路线图的所有活跃任务（包括重试任务）
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            活跃任务列表
        """
        query = text("""
            SELECT t.*
            FROM roadmap_tasks t
            JOIN roadmap_task_links l ON t.task_id = l.task_id
            WHERE l.roadmap_id = :roadmap_id
            AND t.status IN ('pending', 'processing', 'human_review_pending')
            ORDER BY l.created_at DESC
        """)
        
        result = await self.session.execute(query, {"roadmap_id": roadmap_id})
        rows = result.fetchall()
        
        return [
            RoadmapTask(
                task_id=row.task_id,
                user_id=row.user_id,
                status=row.status,
                current_step=row.current_step,
                user_request=row.user_request,
                roadmap_id=row.roadmap_id,
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
            for row in rows
        ]
    
    # ✅ New method: Get all tasks for roadmap (including completed)
    async def get_all_tasks_for_roadmap(self, roadmap_id: str) -> list[dict]:
        """
        获取路线图的所有任务（包括已完成的）
        
        Args:
            roadmap_id: 路线图 ID
            
        Returns:
            任务列表，包含任务类型和概念信息
        """
        query = text("""
            SELECT t.*, l.task_type, l.concept_id, l.content_type
            FROM roadmap_tasks t
            JOIN roadmap_task_links l ON t.task_id = l.task_id
            WHERE l.roadmap_id = :roadmap_id
            ORDER BY l.created_at DESC
        """)
        
        result = await self.session.execute(query, {"roadmap_id": roadmap_id})
        rows = result.fetchall()
        
        return [
            {
                "task_id": row.task_id,
                "task_type": row.task_type,
                "status": row.status,
                "current_step": row.current_step,
                "concept_id": row.concept_id,
                "content_type": row.content_type,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ]
```

### Phase 3: Update Retry Endpoints

**File**: `backend/app/api/v1/endpoints/generation.py`

```python
@router.post("/{roadmap_id}/concepts/{concept_id}/tutorial/retry")
async def retry_tutorial(...):
    task_id = _generate_retry_task_id(roadmap_id, concept_id, "tutorial")
    
    # ✅ FIX 1: Create task record
    async with repo_factory.create_session() as session:
        task_repo = repo_factory.create_task_repo(session)
        await task_repo.create_task(
            task_id=task_id,
            user_id=concept.user_id,  # Get from roadmap_metadata
            user_request={
                "type": "retry_tutorial",
                "roadmap_id": roadmap_id,
                "concept_id": concept_id,
                "preferences": request.preferences.model_dump(mode='json'),
            },
        )
        await task_repo.update_task_status(
            task_id=task_id,
            status="processing",
            current_step="tutorial_generation",
            roadmap_id=roadmap_id,
        )
        
        # ✅ FIX 2: Link task to roadmap
        roadmap_repo = repo_factory.create_roadmap_repo(session)
        await roadmap_repo.link_task_to_roadmap(
            roadmap_id=roadmap_id,
            task_id=task_id,
            task_type="retry_tutorial",
            concept_id=concept_id,
            content_type="tutorial",
        )
        
        await session.commit()
    
    # Continue with existing logic...
    try:
        # Generate tutorial...
        
        # ✅ FIX 3: Update task status on completion
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="completed",
                current_step="completed",
            )
            await session.commit()
            
    except Exception as e:
        # ✅ FIX 4: Update task status on failure
        async with repo_factory.create_session() as session:
            task_repo = repo_factory.create_task_repo(session)
            await task_repo.update_task_status(
                task_id=task_id,
                status="failed",
                current_step="failed",
                error_message=str(e),
            )
            await session.commit()
        raise
```

### Phase 4: Fix Stale Status Detection

**File**: `backend/app/api/v1/roadmap.py`

```python
@router.get("/{roadmap_id}/status-check")
async def check_roadmap_status_quick(roadmap_id: str, db: AsyncSession = Depends(get_db)):
    """
    快速检查路线图状态，用于检测僵尸状态
    
    改进：检查所有与该路线图相关的活跃任务（包括重试任务）
    """
    repo = RoadmapRepository(db)
    
    # 获取路线图元数据
    metadata = await repo.get_roadmap_metadata(roadmap_id)
    if not metadata:
        raise HTTPException(status_code=404, detail="路线图不存在")
    
    # ✅ FIX: Get ALL active tasks for this roadmap (not just metadata.task_id)
    active_tasks = await repo.get_active_tasks_for_roadmap(roadmap_id)
    has_active_task = len(active_tasks) > 0
    
    if has_active_task:
        return {
            "roadmap_id": roadmap_id,
            "has_active_task": True,
            "active_tasks": [
                {
                    "task_id": task.task_id,
                    "status": task.status,
                    "current_step": task.current_step,
                }
                for task in active_tasks
            ],
            "stale_concepts": [],
        }
    
    # No active tasks, check for stale concepts
    framework_data = metadata.framework_data
    stale_concepts = []
    
    for stage in framework_data.get("stages", []):
        for module in stage.get("modules", []):
            for concept in module.get("concepts", []):
                # Check for 'generating' or 'pending' status without active task
                for content_type, status_key in [
                    ("tutorial", "content_status"),
                    ("resources", "resources_status"),
                    ("quiz", "quiz_status"),
                ]:
                    status = concept.get(status_key)
                    if status in ["pending", "generating"]:
                        stale_concepts.append({
                            "concept_id": concept.get("concept_id"),
                            "concept_name": concept.get("name"),
                            "content_type": content_type,
                            "current_status": status,
                        })
    
    return {
        "roadmap_id": roadmap_id,
        "has_active_task": False,
        "active_tasks": [],
        "stale_concepts": stale_concepts,
    }
```

---

## 📊 Benefits Summary

| Aspect | Before | After |
|--------|--------|-------|
| **Roadmap-Task Relationship** | 1:1 (only creation task) | 1:N (creation + retries) |
| **Retry Task Persistence** | ❌ Not saved to DB | ✅ Saved to `roadmap_tasks` + linked |
| **Stale Status Detection** | ❌ False positives | ✅ Accurate (checks all tasks) |
| **Audit Trail** | ❌ Missing retry history | ✅ Complete history |
| **Task Status Query** | ❌ Can't query retry tasks | ✅ Can query all tasks |
| **Execution Logs** | ❌ Missing for retries | ✅ Complete logs |
| **WebSocket Recovery** | ⚠️ Only via WebSocket | ✅ Can recover from DB |

---

## 🧪 Testing Checklist

### Database Migration
- [ ] Migration creates `roadmap_task_links` table
- [ ] Migration populates existing data from `roadmap_metadata.task_id`
- [ ] Indexes are created correctly
- [ ] Rollback works correctly

### Repository Layer
- [ ] `link_task_to_roadmap()` inserts link correctly
- [ ] `get_active_tasks_for_roadmap()` returns only active tasks
- [ ] `get_all_tasks_for_roadmap()` returns all tasks with metadata
- [ ] Duplicate links are handled (ON CONFLICT)

### Retry Endpoints
- [ ] `retry_tutorial` creates task record
- [ ] `retry_resources` creates task record
- [ ] `retry_quiz` creates task record
- [ ] Task status updates on completion
- [ ] Task status updates on failure
- [ ] Links are created correctly

### Stale Status Detection
- [ ] No false positives when retry task is active
- [ ] Correctly identifies stale concepts when no tasks active
- [ ] Returns all active tasks in response

### End-to-End
- [ ] Create roadmap → task linked
- [ ] Retry tutorial → new task created and linked
- [ ] Check status during retry → no false positive
- [ ] Switch tabs and return → status accurate
- [ ] Task killed → stale status detected correctly

---

## 🎯 Migration Strategy

### Stage 1: Schema Migration (No Breaking Changes)
1. Add `roadmap_task_links` table
2. Migrate existing data
3. Keep `roadmap_metadata.task_id` for backward compatibility

### Stage 2: Repository Updates
1. Add new methods for linking and querying
2. Update existing code to use new methods

### Stage 3: Endpoint Updates
1. Update retry endpoints to persist tasks
2. Update stale status detection logic

### Stage 4: Cleanup (Optional)
1. Deprecate `roadmap_metadata.task_id` column
2. Add migration to drop column (after validation)

---

## 📚 Related Files

### To Create
- `backend/alembic/versions/XXXX_add_roadmap_task_links.py` - Migration
- `backend/app/models/database.py` - Add `RoadmapTaskLink` model (optional)

### To Modify
- `backend/app/db/repositories/roadmap_repo.py` - Add linking methods
- `backend/app/api/v1/endpoints/generation.py` - Fix retry endpoints
- `backend/app/api/v1/roadmap.py` - Fix stale status detection
- `backend/app/api/v1/endpoints/retry.py` - Update batch retry if needed

---

## 🎉 Conclusion

This redesign:
- ✅ **Decouples** roadmap and task relationship (1:N instead of 1:1)
- ✅ **Fixes** retry task persistence issue
- ✅ **Enables** accurate stale status detection
- ✅ **Preserves** complete audit trail
- ✅ **Maintains** backward compatibility during migration
- ✅ **Simplifies** future task management

**Status**: Ready for implementation approval

