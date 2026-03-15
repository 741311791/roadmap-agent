"""
JSON Patch 路线图编辑 Agent。

核心思路：
1. 将局部编辑建模为受约束的 RFC 6902 patch 操作。
2. 仅允许修改白名单路径，避免误伤运营字段和派生字段。
3. patch 应用失败时由适配层回退到传统全量编辑器。
"""
from __future__ import annotations

import copy
import json
import math
import re
from typing import Any, Literal

import jsonpatch
import structlog
from pydantic import BaseModel, Field, model_validator

from app.agents.base import BaseAgent
from app.agents.framework_diff import compute_modified_node_ids
from app.config.settings import settings
from app.models.domain import (
    Concept,
    ConstraintNames,
    EditPlan,
    LearningPreferences,
    Module,
    RoadmapEditInput,
    RoadmapEditOutput,
    RoadmapFramework,
    Stage,
)

logger = structlog.get_logger()

EDITABLE_REPLACE_PATTERNS = (
    re.compile(r"^/stages/\d+/name$"),
    re.compile(r"^/stages/\d+/description$"),
    re.compile(r"^/stages/\d+/modules/\d+/name$"),
    re.compile(r"^/stages/\d+/modules/\d+/description$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/name$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/description$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/estimated_hours$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/difficulty$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/prerequisites$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+/keywords$"),
)
EDITABLE_ADD_PATTERNS = (
    re.compile(r"^/stages(?:/\d+|/-)$"),
    re.compile(r"^/stages/\d+/modules(?:/\d+|/-)$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts(?:/\d+|/-)$"),
)
EDITABLE_REMOVE_PATTERNS = (
    re.compile(r"^/stages/\d+$"),
    re.compile(r"^/stages/\d+/modules/\d+$"),
    re.compile(r"^/stages/\d+/modules/\d+/concepts/\d+$"),
)


class JsonPatchOperation(BaseModel):
    """单条 JSON Patch 操作。"""

    op: Literal["add", "replace", "remove"] = Field(..., description="RFC 6902 操作类型")
    path: str = Field(..., description="RFC 6901 JSON Pointer 路径")
    value: Any | None = Field(default=None, description="add/replace 操作值")

    @model_validator(mode="after")
    def validate_contract(self) -> "JsonPatchOperation":
        """校验操作基础契约。"""
        if not self.path.startswith("/"):
            raise ValueError("patch path 必须以 '/' 开头。")
        if self.op in {"add", "replace"} and self.value is None:
            raise ValueError("add/replace 操作必须包含 value。")
        return self


class JsonPatchResponse(BaseModel):
    """JSON Patch 结构化输出包装。"""

    patches: list[JsonPatchOperation] = Field(..., min_length=1, description="patch 操作数组")


class JsonPatchEditorAgent(BaseAgent):
    """
    基于 JSON Patch 的路线图编辑 Agent。

    适用场景：
    - UPDATE：局部修改 Stage / Module / Concept
    - CREATE：新增 Stage / Module / Concept

    不适用场景：
    - REGENERATE：整图重建由传统编辑器处理
    """

    def __init__(
        self,
        agent_id: str = "json_patch_editor",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.EDITOR_PROVIDER,
            model_name=model_name or settings.EDITOR_MODEL,
            base_url=base_url or settings.EDITOR_BASE_URL,
            api_key=api_key or settings.EDITOR_API_KEY,
            temperature=0.0,
            max_tokens=4096,
        )

    def _get_required_constraints(self) -> list[str]:
        """JSON Patch 编辑器需要的约束。"""
        return [
            ConstraintNames.LANGUAGE,
            ConstraintNames.USER_GOAL,
            ConstraintNames.USER_PROFILE,
            ConstraintNames.SKILL_GAP,
            ConstraintNames.RECOMMENDED_FOCUS,
        ]

    async def execute(self, input_data: RoadmapEditInput) -> RoadmapEditOutput:
        """
        执行局部 patch 编辑。

        Args:
            input_data: 路线图编辑输入。

        Returns:
            路线图编辑输出。
        """
        if any(task.action == "REGENERATE" for task in input_data.edit_plan.tasks):
            raise ValueError("REGENERATE 不支持 JSON Patch 编辑。")

        existing_framework = input_data.existing_framework
        user_preferences = input_data.user_preferences
        edit_plan = input_data.edit_plan
        user_constraints = await self._load_user_constraints(
            roadmap_id=existing_framework.roadmap_id
        )

        logger.info(
            "json_patch_edit_started",
            roadmap_id=existing_framework.roadmap_id,
            tasks_count=len(edit_plan.tasks),
        )

        system_prompt = self._load_system_prompt(
            "json_patch_editor.j2",
            user_constraints=user_constraints,
            agent_name="JSON Patch Editor",
            role_description="根据编辑计划生成受约束的 JSON Patch 操作。",
        )
        user_message = self._build_user_message(
            existing_framework=existing_framework,
            user_preferences=user_preferences,
            edit_plan=edit_plan,
        )
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        last_error: Exception | None = None
        updated_framework: RoadmapFramework | None = None
        patch_ops: list[dict[str, Any]] = []

        for attempt in range(1, 4):
            response = await self._generate_patch_response(messages)
            patch_ops = [patch.model_dump(exclude_none=True) for patch in response.patches]
            try:
                updated_framework = self._apply_patch_and_validate(
                    existing_framework=existing_framework,
                    user_preferences=user_preferences,
                    patch_ops=patch_ops,
                )
                break
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "json_patch_apply_retry",
                    attempt=attempt,
                    error=str(exc),
                )
                messages = messages + [
                    {
                        "role": "assistant",
                        "content": json.dumps(
                            {"patches": patch_ops},
                            ensure_ascii=False,
                            indent=2,
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "上一轮 patch 无法通过本地校验，请重新生成完整 patch。"
                            f"错误原因：{exc}。"
                            "请严格使用 easy/medium/hard 难度值，并确保新增节点符合模板。"
                        ),
                    },
                ]

        if updated_framework is None:
            raise ValueError(f"JSON Patch 编辑失败：{last_error}")

        modified_node_ids = compute_modified_node_ids(
            old_framework=existing_framework,
            new_framework=updated_framework,
        )
        modification_summary = self._build_summary(
            edit_plan=edit_plan,
            old_framework=existing_framework,
            new_framework=updated_framework,
            modified_node_ids=modified_node_ids,
        )

        logger.info(
            "json_patch_edit_completed",
            roadmap_id=updated_framework.roadmap_id,
            patch_count=len(patch_ops),
            modified_nodes_count=len(modified_node_ids),
        )

        return RoadmapEditOutput(
            framework=updated_framework,
            modification_summary=modification_summary,
            modified_node_ids=modified_node_ids,
        )

    def _build_user_message(
        self,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
        edit_plan: EditPlan,
    ) -> str:
        """构建用户消息。"""
        tasks_text = "\n".join(
            f"- [{task.action}] {task.stage_id or 'NEW'}: {task.instruction}"
            for task in edit_plan.tasks
        )
        return f"""
## 编辑目标

**反馈摘要**:
{edit_plan.feedback_summary}

**修改任务**:
{tasks_text}

**用户背景**:
- 学习目标: {user_preferences.learning_goal}
- 当前水平: {user_preferences.current_level}
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时

## 当前路线图骨架

```json
{self._build_framework_skeleton(existing_framework)}
```

## 新增节点模板

### Stage 模板
```json
{{
  "stage_id": "stage-new-topic",
  "name": "新阶段名称",
  "description": "阶段描述",
  "order": 999,
  "modules": [
    {{
      "module_id": "module-new-topic",
      "name": "模块名称",
      "description": "模块描述",
      "concepts": [
        {{
          "concept_id": "concept-new-topic",
          "name": "概念名称",
          "description": "概念描述",
          "estimated_hours": 2.0,
          "difficulty": "medium",
          "prerequisites": [],
          "keywords": ["keyword-1", "keyword-2"]
        }}
      ]
    }}
  ]
}}
```

### Module 模板
```json
{{
  "module_id": "module-new-topic",
  "name": "模块名称",
  "description": "模块描述",
  "concepts": [
    {{
      "concept_id": "concept-new-topic",
      "name": "概念名称",
      "description": "概念描述",
      "estimated_hours": 2.0,
      "difficulty": "medium",
      "prerequisites": [],
      "keywords": ["keyword-1", "keyword-2"]
    }}
  ]
}}
```

### Concept 模板
```json
{{
  "concept_id": "concept-new-topic",
  "name": "概念名称",
  "description": "概念描述",
  "estimated_hours": 2.0,
  "difficulty": "medium",
  "prerequisites": [],
  "keywords": ["keyword-1", "keyword-2"]
}}
```
"""

    def _build_framework_skeleton(self, framework: RoadmapFramework) -> str:
        """构建轻量结构骨架，减少上下文体积。"""
        skeleton = {
            "roadmap_id": framework.roadmap_id,
            "title": framework.title,
            "stages": [
                {
                    "stage_id": stage.stage_id,
                    "name": stage.name,
                    "modules": [
                        {
                            "module_id": module.module_id,
                            "name": module.name,
                            "concepts": [
                                {
                                    "concept_id": concept.concept_id,
                                    "name": concept.name,
                                    "difficulty": concept.difficulty,
                                }
                                for concept in module.concepts
                            ],
                        }
                        for module in stage.modules
                    ],
                }
                for stage in framework.stages
            ],
        }
        return json.dumps(skeleton, ensure_ascii=False, indent=2)

    async def _generate_patch_response(
        self,
        messages: list[dict[str, str]],
        max_attempts: int = 3,
    ) -> JsonPatchResponse:
        """
        生成并校验 patch 响应。

        某些兼容层对结构化 parse 稳定性较差，这里改为：
        1. 普通文本输出
        2. 本地 JSON 解析
        3. 失败后带错误反馈重试
        """
        current_messages = list(messages)
        last_error: Exception | None = None

        for attempt in range(1, max_attempts + 1):
            raw_response = await self._call_llm(messages=current_messages)
            content = raw_response.choices[0].message.content or ""
            try:
                parsed_payload = self._parse_patch_payload(content)
                return JsonPatchResponse.model_validate(parsed_payload)
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "json_patch_parse_retry",
                    attempt=attempt,
                    error=str(exc),
                )
                current_messages = current_messages + [
                    {
                        "role": "assistant",
                        "content": content,
                    },
                    {
                        "role": "user",
                        "content": (
                            "上一轮输出不符合要求，请重新输出完整 JSON 对象。"
                            "错误原因："
                            f"{exc}。"
                            "只允许输出 {\"patches\": [...]}，不要使用 Markdown 代码块。"
                            "不要输出任何 /index 路径，也不要在新增对象里包含 index 字段。"
                        ),
                    },
                ]

        raise ValueError(f"JSON Patch 生成失败：{last_error}")

    def _parse_patch_payload(self, raw_content: str) -> dict[str, Any]:
        """解析模型输出的 patch 文本。"""
        cleaned = raw_content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        payload = json.loads(cleaned)
        if isinstance(payload, list):
            return {"patches": payload}
        if not isinstance(payload, dict):
            raise ValueError("patch 输出必须是 JSON 对象或数组。")
        return payload

    def _apply_patch_and_validate(
        self,
        existing_framework: RoadmapFramework,
        user_preferences: LearningPreferences,
        patch_ops: list[dict[str, Any]],
    ) -> RoadmapFramework:
        """
        应用 patch 并校验结果。

        Args:
            existing_framework: 原始路线图。
            user_preferences: 用户偏好。
            patch_ops: patch 操作列表。

        Returns:
            校验后的路线图框架。
        """
        normalized_patch_ops: list[dict[str, Any]] = []
        for patch_op in patch_ops:
            operation = JsonPatchOperation.model_validate(patch_op)
            operation.value = self._normalize_patch_value_literals(operation.value)
            operation = self._sanitize_operation(operation)
            if operation is None:
                continue
            self._validate_patch_permission(operation)
            normalized_patch_ops.append(operation.model_dump(exclude_none=True))

        patched_document = jsonpatch.JsonPatch(normalized_patch_ops).apply(
            copy.deepcopy(existing_framework.model_dump()),
            in_place=False,
        )
        patched_document["roadmap_id"] = existing_framework.roadmap_id
        patched_document["title"] = existing_framework.title
        self._normalize_document(
            document=patched_document,
            user_preferences=user_preferences,
        )

        updated_framework = RoadmapFramework.model_validate(patched_document)
        is_valid, issues = updated_framework.validate_structure()
        if not is_valid:
            issue_message = "；".join(issue.issue for issue in issues[:3])
            raise ValueError(f"JSON Patch 编辑后的路线图结构非法：{issue_message}")
        return updated_framework

    def _sanitize_operation(
        self,
        operation: JsonPatchOperation,
    ) -> JsonPatchOperation | None:
        """
        清理模型常见的无效 patch。

        当前主要处理两类噪音：
        1. 误把只读定位信息当成真实字段去修改 `/index`
        2. 新增 payload 中夹带的 `index`
        """
        if operation.path.endswith("/index"):
            logger.info(
                "json_patch_index_operation_ignored",
                path=operation.path,
            )
            return None

        if operation.op == "add" and isinstance(operation.value, dict):
            cleaned_value = self._strip_index_fields(operation.value)
            if re.match(r"^/stages(?:/\d+|/-)$", operation.path):
                cleaned_value.setdefault("order", 999)
            operation.value = cleaned_value
        return operation

    def _strip_index_fields(self, value: Any) -> Any:
        """递归移除 payload 中的辅助 index 字段。"""
        if isinstance(value, dict):
            return {
                key: self._strip_index_fields(item)
                for key, item in value.items()
                if key != "index"
            }
        if isinstance(value, list):
            return [self._strip_index_fields(item) for item in value]
        return value

    def _normalize_patch_value_literals(self, value: Any) -> Any:
        """归一化 patch payload 中的常见枚举字面量。"""
        difficulty_map = {
            "beginner": "easy",
            "intermediate": "medium",
            "advanced": "hard",
        }
        if isinstance(value, dict):
            normalized: dict[str, Any] = {}
            for key, item in value.items():
                if key == "difficulty" and isinstance(item, str):
                    normalized[key] = difficulty_map.get(item, item)
                else:
                    normalized[key] = self._normalize_patch_value_literals(item)
            return normalized
        if isinstance(value, list):
            return [self._normalize_patch_value_literals(item) for item in value]
        return value

    def _validate_patch_permission(self, operation: JsonPatchOperation) -> None:
        """校验 patch 是否命中白名单路径。"""
        patterns = {
            "add": EDITABLE_ADD_PATTERNS,
            "replace": EDITABLE_REPLACE_PATTERNS,
            "remove": EDITABLE_REMOVE_PATTERNS,
        }[operation.op]

        if not any(pattern.match(operation.path) for pattern in patterns):
            raise ValueError(f"不允许修改该路径：{operation.path}")

        if operation.op == "add":
            self._validate_add_payload(operation.path, operation.value)
        if operation.op == "replace":
            self._validate_replace_payload(operation.path, operation.value)

    def _validate_add_payload(self, path: str, value: Any) -> None:
        """校验新增 payload。"""
        if re.match(r"^/stages(?:/\d+|/-)$", path):
            Stage.model_validate(value)
            return
        if re.match(r"^/stages/\d+/modules(?:/\d+|/-)$", path):
            Module.model_validate(value)
            return
        if re.match(r"^/stages/\d+/modules/\d+/concepts(?:/\d+|/-)$", path):
            Concept.model_validate(value)
            return
        raise ValueError(f"无法识别的 add 路径：{path}")

    def _validate_replace_payload(self, path: str, value: Any) -> None:
        """校验 replace payload。"""
        if path.endswith(("/name", "/description")) and not isinstance(value, str):
            raise ValueError("name/description 的 replace value 必须是字符串。")
        if path.endswith("/estimated_hours") and not isinstance(value, (int, float)):
            raise ValueError("estimated_hours 的 replace value 必须是数字。")
        if path.endswith("/difficulty") and value not in {"easy", "medium", "hard"}:
            raise ValueError("difficulty 的 replace value 非法。")
        if path.endswith("/prerequisites"):
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError("prerequisites 的 replace value 必须是字符串数组。")
        if path.endswith("/keywords"):
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ValueError("keywords 的 replace value 必须是字符串数组。")

    def _normalize_document(
        self,
        document: dict[str, Any],
        user_preferences: LearningPreferences,
    ) -> None:
        """重算派生字段并修正顺序。"""
        total_hours = 0.0
        for stage_index, stage in enumerate(document.get("stages", []), start=1):
            stage["order"] = stage_index
            for module in stage.get("modules", []):
                for concept in module.get("concepts", []):
                    total_hours += float(concept["estimated_hours"])
        document["total_estimated_hours"] = round(total_hours, 1)
        weekly_hours = max(1, user_preferences.available_hours_per_week)
        document["recommended_completion_weeks"] = max(1, math.ceil(total_hours / weekly_hours))

    def _build_summary(
        self,
        edit_plan: EditPlan,
        old_framework: RoadmapFramework,
        new_framework: RoadmapFramework,
        modified_node_ids: list[str],
    ) -> str:
        """生成本地修改摘要。"""
        task_summary = "；".join(
            f"{task.action} {task.stage_id or 'new'}"
            for task in edit_plan.tasks
        )
        hours_diff = new_framework.total_estimated_hours - old_framework.total_estimated_hours
        hours_sign = "+" if hours_diff >= 0 else ""
        feedback_summary = edit_plan.feedback_summary.rstrip("。.!！?")
        return (
            f"{feedback_summary}。"
            f"执行了 {len(edit_plan.tasks)} 个修改任务（{task_summary}），"
            f"修改了 {len(modified_node_ids)} 个节点，"
            f"总时长变化: {hours_sign}{hours_diff:.1f}h"
        )


class AdaptiveRoadmapEditorAgent:
    """
    路线图编辑适配层。

    UPDATE/CREATE 优先走 JSON Patch 路径；
    REGENERATE 走快速全量重建路径；
    patch 失败时回退到传统全量编辑器。
    """

    def __init__(
        self,
        patch_editor: JsonPatchEditorAgent,
        regenerate_editor: Any,
        legacy_editor: Any,
        agent_id: str = "adaptive_roadmap_editor",
    ):
        self.patch_editor = patch_editor
        self.regenerate_editor = regenerate_editor
        self.legacy_editor = legacy_editor
        self.agent_id = agent_id

    async def execute(self, input_data: RoadmapEditInput) -> RoadmapEditOutput:
        """执行编辑。"""
        if any(task.action == "REGENERATE" for task in input_data.edit_plan.tasks):
            logger.info(
                "adaptive_roadmap_editor_route_regenerate_editor",
                reason="regenerate_requested",
            )
            return await self.regenerate_editor.execute(input_data)

        try:
            return await self.patch_editor.execute(input_data)
        except Exception as exc:
            logger.warning(
                "adaptive_roadmap_editor_fallback",
                error=str(exc),
                fallback="legacy_editor",
            )
            return await self.legacy_editor.execute(input_data)
