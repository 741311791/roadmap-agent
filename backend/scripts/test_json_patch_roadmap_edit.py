"""
JSON Patch（RFC 6902）路线图编辑脚本测试。

目标：
1. 使用真实 LLM 生成 JSON Patch。
2. 验证 add / replace / remove / 异常路径 的工程可行性。
3. 在不侵入核心工作流代码的前提下，给出可复现的验证结果。
"""

from __future__ import annotations

import asyncio
import copy
import json
import time
from dataclasses import dataclass
from typing import Any, Literal

import jsonpatch
import jsonpointer
from langchain.agents import create_agent
from langchain_litellm import ChatLiteLLM
from pydantic import BaseModel, Field, model_validator

from app.config.settings import settings
from app.models.domain import RoadmapFramework


SAMPLE_ROADMAP: dict[str, Any] = {
    "roadmap_id": "webreactnodejsexpresspostgresqlwebapi-813c5ade",
    "title": "Full-Stack Web Practice: React + Node.js + PostgreSQL",
    "stages": [
        {
            "stage_id": "s-1",
            "name": "Full-Stack Foundation and Tooling Setup",
            "description": "Build JavaScript/TypeScript fundamentals and modern toolchain.",
            "order": 1,
            "modules": [
                {
                    "module_id": "m-1-1",
                    "name": "JavaScript/TypeScript Core",
                    "description": "Core language features and engineering habits.",
                    "concepts": [
                        {
                            "concept_id": "c-1-1-1",
                            "name": "Async Programming with Promise/async-await",
                            "description": "Understand event loop and async control flow.",
                            "estimated_hours": 3.0,
                            "prerequisites": [],
                            "difficulty": "medium",
                            "keywords": [
                                "asynchronous programming",
                                "Promise",
                                "async/await",
                            ],
                            "content_status": "completed",
                            "tutorial_id": "tut-c-1-1-1",
                            "content_ref": "s3://bucket/c-1-1-1/v1.md",
                            "content_version": "v1",
                            "content_summary": "Async core concepts.",
                            "resources_status": "completed",
                            "resources_id": "res-c-1-1-1",
                            "resources_count": 3,
                            "quiz_status": "completed",
                            "quiz_id": "quiz-c-1-1-1",
                            "quiz_questions_count": 6,
                        },
                        {
                            "concept_id": "c-1-1-2",
                            "name": "Modules and ES6+ Syntax",
                            "description": "CommonJS, ESM, destructuring and template literals.",
                            "estimated_hours": 2.5,
                            "prerequisites": [],
                            "difficulty": "easy",
                            "keywords": [
                                "ES6",
                                "modules",
                                "destructuring",
                            ],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                    ],
                },
                {
                    "module_id": "m-1-2",
                    "name": "Full-Stack Toolchain",
                    "description": "Node.js, package managers and local integration workflow.",
                    "concepts": [
                        {
                            "concept_id": "c-1-2-1",
                            "name": "Node.js and Package Management",
                            "description": "Install Node.js and manage dependencies.",
                            "estimated_hours": 2.0,
                            "prerequisites": [],
                            "difficulty": "easy",
                            "keywords": ["Node.js", "npm", "yarn", "nvm"],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                    ],
                },
            ],
        },
        {
            "stage_id": "s-2",
            "name": "React and Express Core Build",
            "description": "Build reusable UI and robust REST APIs.",
            "order": 2,
            "modules": [
                {
                    "module_id": "m-2-1",
                    "name": "React Modern UI Development",
                    "description": "Reusable components and routing.",
                    "concepts": [
                        {
                            "concept_id": "c-2-1-1",
                            "name": "Components and Props",
                            "description": "Function components and one-way data flow.",
                            "estimated_hours": 3.0,
                            "prerequisites": ["c-1-1-2"],
                            "difficulty": "medium",
                            "keywords": ["components", "props", "JSX"],
                            "content_status": "pending",
                            "tutorial_id": None,
                            "content_ref": None,
                            "content_version": "v1",
                            "content_summary": None,
                            "resources_status": "pending",
                            "resources_id": None,
                            "resources_count": 0,
                            "quiz_status": "pending",
                            "quiz_id": None,
                            "quiz_questions_count": 0,
                        },
                    ],
                }
            ],
        },
    ],
    "total_estimated_hours": 200.0,
    "recommended_completion_weeks": 20,
}


SIMULATED_EDIT_REQUEST = {
    "feedback_summary": "Add distributed system fundamentals and refine one concept title.",
    "tasks": [
        {
            "action": "UPDATE",
            "stage_id": "s-1",
            "instruction": (
                "Append one module to stage s-1 for Ray foundations. "
                "All generated content fields must be English."
            ),
        },
        {
            "action": "UPDATE",
            "stage_id": "s-2",
            "instruction": "Refine concept c-2-1-1 title and description.",
        },
    ],
}


LLM_PATCH_SYSTEM_PROMPT = """# Role
You are a precise JSON Data Transformation Agent. Your sole purpose is to translate natural language update instructions into a strictly valid RFC 6902 JSON Patch array.

# Task
Analyze the <ORIGINAL_JSON_SKELETON> and the <UPDATE_TASKS>. Generate the JSON Patch array required to implement these tasks on the original data.

# Strict Rules (CRITICAL)
1. Format Constraint: Output ONLY a valid JSON array. Do not include any conversational text, explanations, or Markdown formatting (do NOT use ```json). The output must be directly parseable by a standard JSON parser.
2. Language Constraint: ALL generated content (e.g., `name`, `description`, `title` fields in the generated objects) MUST be translated into and written exclusively in English. No Chinese characters are allowed in the final JSON values.
3. Path Accuracy (RFC 6901): Use exact JSON Pointer paths. Arrays are 0-indexed. To append to an array, use the `-` character (e.g., `"path": "/stages/0/modules/-"`).
4. Schema Alignment: Ensure the `value` payload strictly matches the existing data schema. For example, a new `module` must include `module_id`, `name`, `description`, and a `concepts` array. Auto-generate semantic IDs for new elements (e.g., `"module_id": "m-1-ray-core"`).
5. Operation Types:
   - Use `"op": "add"` to insert new modules or concepts.
   - Use `"op": "replace"` to modify existing fields.
   - Use `"op": "remove"` for deletions.
"""


@dataclass
class ScenarioResult:
    name: str
    passed: bool
    elapsed_ms: int
    detail: str


class JsonPatchConceptPayload(BaseModel):
    """
    JSON Patch 中新增 concept 的最小合法结构。
    """

    concept_id: str
    name: str
    description: str
    estimated_hours: float = Field(ge=0.5)
    prerequisites: list[str]
    difficulty: Literal["easy", "medium", "hard"]
    keywords: list[str]
    content_status: Literal["pending", "generating", "completed", "failed"]
    tutorial_id: str | None
    content_ref: str | None
    content_version: str
    content_summary: str | None
    resources_status: Literal["pending", "generating", "completed", "failed"]
    resources_id: str | None
    resources_count: int
    quiz_status: Literal["pending", "generating", "completed", "failed"]
    quiz_id: str | None
    quiz_questions_count: int


class JsonPatchModulePayload(BaseModel):
    """
    JSON Patch 中新增 module 的最小合法结构。
    """

    module_id: str
    name: str
    description: str
    concepts: list[JsonPatchConceptPayload] = Field(min_length=1)


class JsonPatchOperation(BaseModel):
    """
    单条 RFC 6902 patch 操作。
    """

    op: Literal["add", "replace", "remove"]
    path: str
    value: Any | None = None

    @model_validator(mode="after")
    def validate_operation_contract(self) -> "JsonPatchOperation":
        """
        按路径语义校验 value 的基本形状，帮助 LangChain 自动重试修复。
        """
        if not self.path.startswith("/"):
            raise ValueError("path 必须是合法的 JSON Pointer。")

        if self.op in {"add", "replace"} and self.value is None:
            raise ValueError("add/replace 操作必须包含 value。")

        if self.op == "add" and self.path.endswith("/modules/-"):
            JsonPatchModulePayload.model_validate(self.value)

        if self.op == "add" and "/concepts/" in self.path and self.path.endswith("/-"):
            JsonPatchConceptPayload.model_validate(self.value)

        if self.op == "replace" and (
            self.path.endswith("/name") or self.path.endswith("/description")
        ):
            if not isinstance(self.value, str):
                raise ValueError("name/description 的 replace value 必须是字符串。")

        return self


class JsonPatchResponse(BaseModel):
    """
    LangChain 结构化输出包装对象。
    """

    patches: list[JsonPatchOperation] = Field(min_length=1)


def _apply_patch(document: dict[str, Any], patch_ops: list[dict[str, Any]]) -> dict[str, Any]:
    """
    应用 RFC 6902 补丁并返回新对象。

    Args:
        document: 原始 JSON 文档。
        patch_ops: 补丁操作数组。

    Returns:
        应用补丁后的全新文档。

    Raises:
        jsonpatch.JsonPatchException: 补丁语义错误或路径非法。
    """
    patch = jsonpatch.JsonPatch(patch_ops)
    return patch.apply(copy.deepcopy(document), in_place=False)


def _assert_valid_framework(data: dict[str, Any]) -> RoadmapFramework:
    """
    校验数据可被路线图领域模型接受。

    Args:
        data: 应用补丁后的 JSON 数据。

    Returns:
        校验通过后的 RoadmapFramework。

    Raises:
        pydantic.ValidationError: 数据结构不合法。
    """
    return RoadmapFramework.model_validate(data)


def _contains_cjk(text: str) -> bool:
    """
    判断字符串是否包含中文字符。

    Args:
        text: 待检查字符串。

    Returns:
        若包含中文字符则返回 True。
    """
    return any("\u4e00" <= ch <= "\u9fff" for ch in text)


def _build_stage_index_map(roadmap: dict[str, Any]) -> dict[str, int]:
    """
    构建 stage_id 到数组索引的映射。

    Args:
        roadmap: 路线图 JSON。

    Returns:
        stage_id -> index 映射。
    """
    return {stage["stage_id"]: idx for idx, stage in enumerate(roadmap["stages"])}


def _build_roadmap_skeleton(roadmap: dict[str, Any]) -> dict[str, Any]:
    """
    构建用于喂给 LLM 的轻量骨架，减少上下文体积。

    Args:
        roadmap: 原始路线图 JSON。

    Returns:
        仅包含层级结构和必要标识符的骨架对象。
    """
    return {
        "roadmap_id": roadmap["roadmap_id"],
        "title": roadmap["title"],
        "stages": [
            {
                "stage_id": stage["stage_id"],
                "name": stage["name"],
                "modules": [
                    {
                        "module_id": module["module_id"],
                        "name": module["name"],
                        "description": "",
                        "concepts": [
                            {
                                "concept_id": concept["concept_id"],
                                "name": concept["name"],
                                "description": "",
                            }
                            for concept in module["concepts"]
                        ],
                    }
                    for module in stage["modules"]
                ],
            }
            for stage in roadmap["stages"]
        ],
    }


def _build_llm_patch_user_prompt(roadmap: dict[str, Any], request_payload: dict[str, Any]) -> str:
    """
    构建给 LLM 的用户消息（真实编辑模拟输入）。

    Args:
        roadmap: 原始路线图 JSON。
        request_payload: 编辑请求。

    Returns:
        可直接发送给 LLM 的用户消息文本。
    """
    skeleton = _build_roadmap_skeleton(roadmap)
    return (
        "# Inputs\n\n"
        "<SCHEMA_REQUIREMENTS>\n"
        "A module object must include: module_id, name, description, concepts.\n"
        "The concepts field must be a non-empty array.\n"
        "A concept object must include: concept_id, name, description, estimated_hours, prerequisites, difficulty, keywords, content_status, tutorial_id, content_ref, content_version, content_summary, resources_status, resources_id, resources_count, quiz_status, quiz_id, quiz_questions_count.\n"
        "difficulty must be one of: easy, medium, hard.\n"
        "content_status/resources_status/quiz_status must be one of: pending, generating, completed, failed.\n"
        "</SCHEMA_REQUIREMENTS>\n\n"
        "<ORIGINAL_JSON_SKELETON>\n"
        f"{json.dumps(skeleton, ensure_ascii=False, indent=2)}\n"
        "</ORIGINAL_JSON_SKELETON>\n\n"
        "<UPDATE_TASKS>\n"
        f"{json.dumps(request_payload['tasks'], ensure_ascii=False, indent=2)}\n"
        "</UPDATE_TASKS>"
    )


def _build_langchain_model_identifier() -> str:
    """
    构建 LiteLLM 所需的模型标识。

    Returns:
        适用于 ChatLiteLLM 的 model 标识。
    """
    if "dashscope" in (settings.EDITOR_BASE_URL or "") and not settings.EDITOR_MODEL.startswith(
        "dashscope/"
    ):
        return f"dashscope/{settings.EDITOR_MODEL}"
    return settings.EDITOR_MODEL


async def _call_real_llm_for_patch(user_prompt: str) -> str:
    """
    使用 LangChain create_agent 调用真实 LLM。

    说明：
    - 官方文档推荐 `response_format` / `ToolStrategy` 做结构化输出。
    - 但当前 DashScope/Qwen 兼容层会拒绝 LangChain 发出的 `tool_choice="any"`。
    - 因此这里保留 `create_agent` 作为官方推荐入口，
      结构校验与重试仍由脚本本地完成。

    Args:
        user_prompt: 发送给模型的用户消息。

    Returns:
        模型最终文本输出。
    """
    model = ChatLiteLLM(
        model=_build_langchain_model_identifier(),
        api_key=settings.EDITOR_API_KEY,
        api_base=settings.EDITOR_BASE_URL or None,
        temperature=0.0,
        max_tokens=4096,
    )
    agent = create_agent(
        model=model,
        tools=[],
        system_prompt=LLM_PATCH_SYSTEM_PROMPT,
    )
    result = await agent.ainvoke(
        {"messages": [{"role": "user", "content": user_prompt}]},
        config={"recursion_limit": 10},
    )
    final_message = result["messages"][-1].content
    return str(final_message)


def _build_llm_retry_user_prompt(
    roadmap: dict[str, Any],
    request_payload: dict[str, Any],
    previous_output: str,
    error_message: str,
) -> str:
    """
    构建错误反馈后的二次修正提示。

    Args:
        roadmap: 原始路线图 JSON。
        request_payload: 编辑请求。
        previous_output: 上一轮模型输出。
        error_message: 本地解析或校验错误。

    Returns:
        包含错误上下文的重试提示。
    """
    base_prompt = _build_llm_patch_user_prompt(roadmap, request_payload)
    return (
        f"{base_prompt}\n\n"
        "<PREVIOUS_INVALID_OUTPUT>\n"
        f"{previous_output}\n"
        "</PREVIOUS_INVALID_OUTPUT>\n\n"
        "<ERROR_FEEDBACK>\n"
        f"{error_message}\n"
        "</ERROR_FEEDBACK>\n\n"
        "Regenerate the full JSON Patch array from scratch and fix the error. "
        "Output JSON array only."
    )


async def _generate_valid_patch_with_retry(
    roadmap: dict[str, Any],
    request_payload: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    """
    调用真实 LLM，并在本地校验失败时执行额外重试修正。

    Args:
        roadmap: 原始路线图 JSON。
        request_payload: 编辑请求。

    Returns:
        patch 数组、应用后的 JSON、最终原始输出文本。

    Raises:
        Exception: 当三轮都失败时抛出最后一次错误。
    """
    current_prompt = _build_llm_patch_user_prompt(roadmap, request_payload)
    last_error: Exception | None = None

    for attempt in range(1, 4):
        final_message = await _call_real_llm_for_patch(current_prompt)
        print(f"LangChain agent final message (attempt {attempt}):")
        print(final_message)
        print("-" * 80)

        try:
            patch_ops = _parse_llm_patch_output(final_message)
            structured_patch_json = json.dumps(patch_ops, ensure_ascii=False, indent=2)
            print(f"Parsed patch output (attempt {attempt}):")
            print(structured_patch_json)
            print("-" * 80)
            updated = _apply_patch(roadmap, patch_ops)
            _assert_valid_framework(updated)
            return patch_ops, updated, structured_patch_json
        except Exception as exc:
            last_error = exc
            fallback_output = final_message.strip()
            if fallback_output.startswith("["):
                previous_output = fallback_output
            else:
                previous_output = (
                    "The previous agent output was not directly parseable as a JSON array.\n"
                    f"{fallback_output}"
                )
            current_prompt = _build_llm_retry_user_prompt(
                roadmap=roadmap,
                request_payload=request_payload,
                previous_output=previous_output,
                error_message=str(exc),
            )

    raise RuntimeError(f"真实 LLM 在三轮修正后仍未生成有效 patch：{last_error}")


def _extract_name_description_values(value: Any) -> list[str]:
    """
    递归提取对象中的 name/description 值用于英文约束校验。

    Args:
        value: 任意 JSON 值。

    Returns:
        所有命中的文本值列表。
    """
    texts: list[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"name", "description"} and isinstance(item, str):
                texts.append(item)
            texts.extend(_extract_name_description_values(item))
        return texts
    if isinstance(value, list):
        for item in value:
            texts.extend(_extract_name_description_values(item))
    return texts


def _validate_patch_contract(patch_ops: list[dict[str, Any]]) -> None:
    """
    校验 LLM 输出是否满足本脚本定义的 JSON Patch 协议。

    Args:
        patch_ops: 解析后的补丁数组。

    Raises:
        AssertionError: 当协议不满足时抛出。
    """
    if not isinstance(patch_ops, list) or not patch_ops:
        raise AssertionError("LLM 输出必须是非空 JSON 数组。")

    allowed_ops = {"add", "replace", "remove"}
    for idx, op_item in enumerate(patch_ops):
        if not isinstance(op_item, dict):
            raise AssertionError(f"第 {idx} 个 patch 不是对象。")

        try:
            JsonPatchOperation.model_validate(op_item)
        except Exception as exc:
            raise AssertionError(f"第 {idx} 个 patch 不符合结构约束：{exc}") from exc

        op = op_item.get("op")
        path = op_item.get("path")
        if op not in allowed_ops:
            raise AssertionError(f"第 {idx} 个 patch 的 op 非法：{op}")
        if not isinstance(path, str) or not path.startswith("/"):
            raise AssertionError(f"第 {idx} 个 patch 的 path 非法：{path}")
        if op in {"add", "replace"} and "value" not in op_item:
            raise AssertionError(f"第 {idx} 个 patch 缺少 value。")

        if op in {"add", "replace"}:
            text_candidates = _extract_name_description_values(op_item.get("value"))
            if path.endswith("/name") or path.endswith("/description"):
                value = op_item.get("value")
                if isinstance(value, str):
                    text_candidates.append(value)
            for text in text_candidates:
                if _contains_cjk(text):
                    raise AssertionError(f"第 {idx} 个 patch 包含中文文本：{text}")


def _parse_llm_patch_output(raw_output: str) -> list[dict[str, Any]]:
    """
    解析并校验 LLM 输出的 patch 文本。

    Args:
        raw_output: LLM 原始输出。

    Returns:
        解析后的补丁数组。

    Raises:
        AssertionError: 输出格式不合法。
    """
    cleaned = raw_output.strip()
    if not cleaned.startswith("["):
        raise AssertionError("LLM 输出不是 JSON 数组起始格式。")
    parsed = json.loads(cleaned)
    if not isinstance(parsed, list):
        raise AssertionError("LLM 输出解析后不是数组。")
    _validate_patch_contract(parsed)
    return parsed


def _build_add_module_patch_from_request(
    roadmap: dict[str, Any],
    request_payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """
    根据模拟请求构建 add 模块补丁。

    Args:
        roadmap: 原始路线图。
        request_payload: 模拟真实编辑请求。

    Returns:
        RFC 6902 补丁数组。
    """
    _ = request_payload["tasks"][0]["instruction"]
    stage_index = _build_stage_index_map(roadmap)["s-1"]
    return [
        {
            "op": "add",
            "path": f"/stages/{stage_index}/modules/-",
            "value": {
                "module_id": "m-1-ray-foundations",
                "name": "Ray Foundations and System Design",
                "description": (
                    "Understand GCS, object store, scheduler behavior and distributed task execution."
                ),
                "concepts": [
                    {
                        "concept_id": "c-1-ray-1",
                        "name": "GCS Architecture and Object Storage",
                        "description": "Understand metadata management and object references in Ray.",
                        "estimated_hours": 2.0,
                        "prerequisites": ["c-1-1-1"],
                        "difficulty": "medium",
                        "keywords": ["GCS", "object store", "Ray architecture"],
                        "content_status": "pending",
                        "tutorial_id": None,
                        "content_ref": None,
                        "content_version": "v1",
                        "content_summary": None,
                        "resources_status": "pending",
                        "resources_id": None,
                        "resources_count": 0,
                        "quiz_status": "pending",
                        "quiz_id": None,
                        "quiz_questions_count": 0,
                    }
                ],
            },
        },
        {
            "op": "replace",
            "path": "/total_estimated_hours",
            "value": 202.0,
        },
    ]


def run_scenario_add_module() -> ScenarioResult:
    """
    场景A：在 stage s-1 末尾新增模块。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()
    patch_ops = _build_add_module_patch_from_request(SAMPLE_ROADMAP, SIMULATED_EDIT_REQUEST)
    updated = _apply_patch(SAMPLE_ROADMAP, patch_ops)
    framework = _assert_valid_framework(updated)

    s1 = next(stage for stage in framework.stages if stage.stage_id == "s-1")
    new_module = s1.modules[-1]
    if new_module.module_id != "m-1-ray-foundations":
        raise AssertionError("新增模块 ID 不符合预期。")
    if _contains_cjk(new_module.name) or _contains_cjk(new_module.description):
        raise AssertionError("新增模块存在中文，不满足全英文要求。")
    if framework.roadmap_id != SAMPLE_ROADMAP["roadmap_id"]:
        raise AssertionError("roadmap_id 发生变化。")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ScenarioResult(
        name="A-add-module",
        passed=True,
        elapsed_ms=elapsed_ms,
        detail=f"stage_s1_modules={len(s1.modules)}; total_hours={framework.total_estimated_hours}",
    )


def run_scenario_replace_concept() -> ScenarioResult:
    """
    场景B：替换既有 concept 标题和描述。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()
    patch_ops = [
        {
            "op": "replace",
            "path": "/stages/1/modules/0/concepts/0/name",
            "value": "React Components, Props and Composition",
        },
        {
            "op": "replace",
            "path": "/stages/1/modules/0/concepts/0/description",
            "value": "Build composable UI units and model one-way data flow with confidence.",
        },
    ]
    updated = _apply_patch(SAMPLE_ROADMAP, patch_ops)
    framework = _assert_valid_framework(updated)

    concept = framework.stages[1].modules[0].concepts[0]
    if concept.concept_id != "c-2-1-1":
        raise AssertionError("replace 误改了 concept_id。")

    base_concept = framework.stages[0].modules[0].concepts[0]
    if base_concept.content_status != "completed" or base_concept.tutorial_id != "tut-c-1-1-1":
        raise AssertionError("未触达 concept 的运营字段被破坏。")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ScenarioResult(
        name="B-replace-concept",
        passed=True,
        elapsed_ms=elapsed_ms,
        detail=f"concept_name={concept.name}",
    )


def run_scenario_remove_concept() -> ScenarioResult:
    """
    场景C：删除一个 concept。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()
    patch_ops = [
        {
            "op": "remove",
            "path": "/stages/0/modules/0/concepts/1",
        },
        {
            "op": "replace",
            "path": "/total_estimated_hours",
            "value": 197.5,
        },
    ]
    updated = _apply_patch(SAMPLE_ROADMAP, patch_ops)
    framework = _assert_valid_framework(updated)

    concept_ids = [c.concept_id for c in framework.stages[0].modules[0].concepts]
    if "c-1-1-2" in concept_ids:
        raise AssertionError("目标 concept 未被删除。")
    if len(framework.stages[0].modules[0].concepts) != 1:
        raise AssertionError("删除后 concepts 数量不正确。")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ScenarioResult(
        name="C-remove-concept",
        passed=True,
        elapsed_ms=elapsed_ms,
        detail=f"remaining_concepts={len(framework.stages[0].modules[0].concepts)}",
    )


def run_scenario_invalid_path() -> ScenarioResult:
    """
    场景D：非法路径应抛出异常。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()
    patch_ops = [
        {
            "op": "replace",
            "path": "/stages/99/modules/0/name",
            "value": "Will Fail",
        }
    ]
    try:
        _apply_patch(SAMPLE_ROADMAP, patch_ops)
        raise AssertionError("非法 path 未触发异常。")
    except (jsonpatch.JsonPatchException, jsonpointer.JsonPointerException) as exc:
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        return ScenarioResult(
            name="D-invalid-path",
            passed=True,
            elapsed_ms=elapsed_ms,
            detail=f"captured_exception={exc.__class__.__name__}",
        )


def run_scenario_index_shift_safe_remove() -> ScenarioResult:
    """
    场景E：同一数组多次删除时按降序索引避免偏移问题。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()
    extended = copy.deepcopy(SAMPLE_ROADMAP)
    extended["stages"][0]["modules"][0]["concepts"].append(
        {
            "concept_id": "c-1-1-3",
            "name": "Type Inference and Generic Constraints",
            "description": "Use generic constraints to enforce safe APIs.",
            "estimated_hours": 2.0,
            "prerequisites": ["c-1-1-2"],
            "difficulty": "medium",
            "keywords": ["TypeScript", "generics"],
            "content_status": "pending",
            "tutorial_id": None,
            "content_ref": None,
            "content_version": "v1",
            "content_summary": None,
            "resources_status": "pending",
            "resources_id": None,
            "resources_count": 0,
            "quiz_status": "pending",
            "quiz_id": None,
            "quiz_questions_count": 0,
        }
    )

    patch_ops = [
        {"op": "remove", "path": "/stages/0/modules/0/concepts/2"},
        {"op": "remove", "path": "/stages/0/modules/0/concepts/1"},
    ]
    updated = _apply_patch(extended, patch_ops)
    framework = _assert_valid_framework(updated)
    concept_ids = [c.concept_id for c in framework.stages[0].modules[0].concepts]
    if concept_ids != ["c-1-1-1"]:
        raise AssertionError(f"索引偏移防护失败，剩余 concept_ids={concept_ids}")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ScenarioResult(
        name="E-index-shift-safe-remove",
        passed=True,
        elapsed_ms=elapsed_ms,
        detail=f"remaining_ids={concept_ids}",
    )


async def run_scenario_real_llm_patch_result() -> ScenarioResult:
    """
    场景F：真实“喂给 LLM -> 接收 patch -> 校验并应用”的完整链路。

    Returns:
        场景执行结果。
    """
    start = time.perf_counter()

    preview_prompt = _build_llm_patch_user_prompt(SAMPLE_ROADMAP, SIMULATED_EDIT_REQUEST)
    if "<ORIGINAL_JSON_SKELETON>" not in preview_prompt or "<UPDATE_TASKS>" not in preview_prompt:
        raise AssertionError("LLM 用户消息构建失败。")

    patch_ops, updated, _ = await _generate_valid_patch_with_retry(
        roadmap=SAMPLE_ROADMAP,
        request_payload=SIMULATED_EDIT_REQUEST,
    )
    framework = _assert_valid_framework(updated)

    s1 = next(stage for stage in framework.stages if stage.stage_id == "s-1")
    if len(patch_ops) < 2:
        raise AssertionError("真实 LLM 返回的 patch 数量过少，不符合当前任务预期。")
    if len(s1.modules) < 2:
        raise AssertionError("真实 LLM patch 应用后 Stage s-1 模块数量异常。")

    elapsed_ms = int((time.perf_counter() - start) * 1000)
    return ScenarioResult(
        name="F-real-llm-patch-result",
        passed=True,
        elapsed_ms=elapsed_ms,
        detail=f"patch_ops={len(patch_ops)}; s1_modules={len(s1.modules)}; model={settings.EDITOR_MODEL}",
    )


async def main() -> None:
    """
    运行所有 JSON Patch 场景并打印结果汇总。
    """
    print("=" * 80)
    print("JSON Patch Roadmap Edit Script Test")
    print("=" * 80)
    print("Simulated request:")
    print(json.dumps(SIMULATED_EDIT_REQUEST, ensure_ascii=False, indent=2))
    print("-" * 80)
    print("LLM system prompt:")
    print(LLM_PATCH_SYSTEM_PROMPT)
    print("-" * 80)
    print("LLM user prompt preview:")
    llm_user_prompt = _build_llm_patch_user_prompt(SAMPLE_ROADMAP, SIMULATED_EDIT_REQUEST)
    preview_len = 680
    preview = llm_user_prompt[:preview_len]
    suffix = " ...<truncated>" if len(llm_user_prompt) > preview_len else ""
    print(preview + suffix)
    print("-" * 80)

    scenarios = [
        run_scenario_add_module,
        run_scenario_replace_concept,
        run_scenario_remove_concept,
        run_scenario_invalid_path,
        run_scenario_index_shift_safe_remove,
    ]

    results: list[ScenarioResult] = []
    for scenario in scenarios:
        result = scenario()
        results.append(result)
        status = "PASS" if result.passed else "FAIL"
        print(f"[{status}] {result.name} ({result.elapsed_ms} ms) -> {result.detail}")

    real_result = await run_scenario_real_llm_patch_result()
    results.append(real_result)
    real_status = "PASS" if real_result.passed else "FAIL"
    print(f"[{real_status}] {real_result.name} ({real_result.elapsed_ms} ms) -> {real_result.detail}")

    failed = [item for item in results if not item.passed]
    print("-" * 80)
    if failed:
        raise SystemExit(f"脚本失败：{len(failed)} 个场景未通过。")

    total_ms = sum(item.elapsed_ms for item in results)
    print(f"全部通过：{len(results)} / {len(results)}，总耗时 {total_ms} ms")


if __name__ == "__main__":
    asyncio.run(main())
