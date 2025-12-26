"""
Tutorial Modifier Agent（教程修改师）

负责根据用户修改要求调整现有教程内容。
实现增量修改：下载现有内容 → LLM 调整 → 上传新版本。
"""
import json
import uuid
from datetime import datetime
from typing import List, Dict, Any
from app.agents.base import BaseAgent
from app.models.domain import (
    Concept,
    LearningPreferences,
    TutorialModificationInput,
    TutorialModificationOutput,
    S3DownloadRequest,
    S3UploadRequest,
)
from app.core.tool_registry import tool_registry
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class TutorialModifierAgent(BaseAgent):
    """
    教程修改师 Agent
    
    配置从环境变量加载：
    - TUTORIAL_MODIFIER_PROVIDER: 模型提供商（默认: openai）
    - TUTORIAL_MODIFIER_MODEL: 模型名称（默认: gpt-4o）
    - TUTORIAL_MODIFIER_BASE_URL: 自定义 API 端点（可选）
    - TUTORIAL_MODIFIER_API_KEY: API 密钥（默认复用 RECOMMENDER_API_KEY）
    """
    
    def __init__(
        self,
        agent_id: str = "tutorial_modifier",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.TUTORIAL_MODIFIER_PROVIDER,
            model_name=model_name or settings.TUTORIAL_MODIFIER_MODEL,
            base_url=base_url or settings.TUTORIAL_MODIFIER_BASE_URL,
            api_key=api_key or settings.get_tutorial_modifier_api_key,
            temperature=0.7,
            max_tokens=16384,
        )
    
    async def modify(
        self,
        input_data: TutorialModificationInput,
    ) -> TutorialModificationOutput:
        """
        修改教程内容
        
        流程：
        1. 从 S3 下载现有教程内容
        2. 使用 LLM 基于修改要求调整内容
        3. 将新内容上传到 S3（新版本）
        4. 返回修改结果
        
        Args:
            input_data: 教程修改输入
            
        Returns:
            教程修改输出
        """
        concept = input_data.concept
        context = input_data.context
        user_preferences = input_data.user_preferences
        existing_content_url = input_data.existing_content_url
        modification_requirements = input_data.modification_requirements
        
        import time
        start_time = time.time()
        
        logger.info(
            "tutorial_modification_started",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            concept_name=concept.name,
            requirements_count=len(modification_requirements),
            requirements=modification_requirements,
            existing_url=existing_content_url,
        )
        
        # 1. 下载现有教程内容
        logger.info(
            "tutorial_modification_downloading",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            url=existing_content_url,
        )
        download_start = time.time()
        existing_content = await self._download_existing_content(existing_content_url)
        
        download_duration = time.time() - download_start
        
        if not existing_content:
            logger.error(
                "tutorial_modification_download_failed",
                agent="tutorial_modifier",
                concept_id=concept.concept_id,
                url=existing_content_url,
                download_duration_seconds=download_duration,
            )
            raise ValueError(f"无法下载现有教程内容: {existing_content_url}")
        
        logger.info(
            "tutorial_modification_content_downloaded",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            content_length=len(existing_content),
            content_preview=existing_content[:100].replace('\n', ' '),
            download_duration_seconds=download_duration,
        )
        
        # 2. 使用 LLM 修改内容
        logger.info(
            "tutorial_modification_calling_llm",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            model=self.model_name,
        )
        llm_start = time.time()
        
        modified_content, metadata = await self._modify_content(
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            existing_content=existing_content,
            modification_requirements=modification_requirements,
        )
        
        llm_duration = time.time() - llm_start
        logger.info(
            "tutorial_modification_llm_completed",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            modified_content_length=len(modified_content),
            llm_duration_seconds=llm_duration,
        )
        
        # 3. 上传新版本到 S3
        roadmap_id = context.get("roadmap_id", "unknown")
        current_version = context.get("content_version", 1)
        new_version = current_version + 1
        
        logger.info(
            "tutorial_modification_uploading",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            roadmap_id=roadmap_id,
            new_version=new_version,
        )
        upload_start = time.time()
        
        new_content_url = await self._upload_new_version(
            roadmap_id=roadmap_id,
            concept_id=concept.concept_id,
            content=modified_content,
            version=new_version,
        )
        
        upload_duration = time.time() - upload_start
        logger.info(
            "tutorial_modification_uploaded",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            new_url=new_content_url,
            upload_duration_seconds=upload_duration,
        )
        
        # 4. 构建输出
        result = TutorialModificationOutput(
            concept_id=concept.concept_id,
            tutorial_id=str(uuid.uuid4()),
            title=metadata.get("title", concept.name),
            summary=metadata.get("summary", "")[:500],
            content_url=new_content_url,
            content_version=new_version,
            modification_summary=metadata.get("modification_summary", "教程已按要求修改"),
            changes_made=metadata.get("changes_made", modification_requirements),
            estimated_completion_time=metadata.get("estimated_completion_time", 60),
            generated_at=datetime.now(),
        )
        
        total_duration = time.time() - start_time
        logger.info(
            "tutorial_modification_completed",
            agent="tutorial_modifier",
            concept_id=concept.concept_id,
            new_version=new_version,
            new_url=new_content_url,
            changes_count=len(result.changes_made),
            modification_summary=result.modification_summary[:100] if result.modification_summary else "",
            total_duration_seconds=total_duration,
        )
        
        return result
    
    async def _download_existing_content(self, content_url: str) -> str | None:
        """从 S3 下载现有教程内容"""
        try:
            # 从 URL 提取 S3 key
            # URL 格式可能是：
            # - 完整 URL: http://minio:9000/bucket/key
            # - 或者只是 key: roadmaps/{id}/concepts/{cid}/v1.md
            
            s3_key = content_url
            if "://" in content_url:
                # 从 URL 中提取 key
                parts = content_url.split("/")
                # 假设格式是 http://host:port/bucket/path/to/file
                # 找到 bucket 之后的部分
                bucket_name = settings.S3_BUCKET_NAME
                if bucket_name in parts:
                    bucket_idx = parts.index(bucket_name)
                    s3_key = "/".join(parts[bucket_idx + 1:])
                else:
                    # 尝试提取最后的路径部分
                    s3_key = "/".join(parts[-4:])  # roadmaps/{id}/concepts/{cid}/v{n}.md
            
            # 移除 URL 参数
            if "?" in s3_key:
                s3_key = s3_key.split("?")[0]
            
            logger.debug(
                "tutorial_modifier_downloading",
                original_url=content_url,
                s3_key=s3_key,
            )
            
            # 获取 S3 存储工具
            s3_tool = tool_registry.get("s3_storage_v1")
            if not s3_tool:
                raise RuntimeError("S3 Storage Tool 未注册")
            
            # 下载内容
            download_request = S3DownloadRequest(key=s3_key)
            download_result = await s3_tool.download(download_request)
            
            if download_result.success:
                return download_result.content
            else:
                logger.error(
                    "tutorial_modifier_download_failed",
                    s3_key=s3_key,
                )
                return None
                
        except Exception as e:
            logger.error(
                "tutorial_modifier_download_error",
                url=content_url,
                error=str(e),
                error_type=type(e).__name__,
            )
            return None
    
    async def _modify_content(
        self,
        concept: Concept,
        context: Dict[str, Any],
        user_preferences: LearningPreferences,
        existing_content: str,
        modification_requirements: List[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        使用 LLM 修改教程内容
        
        Returns:
            (修改后的内容, 元数据字典)
        """
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "tutorial_modifier.j2",
            agent_name="Tutorial Modifier",
            role_description="专业的教程内容编辑师，擅长根据用户反馈精准修改教程内容，保留优质部分，改进不足之处。",
            concept=concept,
            context=context,
            user_preferences=user_preferences,
            modification_requirements=modification_requirements,
        )
        
        # 构建用户消息
        requirements_text = "\n".join([f"- {req}" for req in modification_requirements])
        
        user_message = f"""
请根据以下修改要求调整教程内容：

**修改要求**:
{requirements_text}

**现有教程内容**:
{existing_content}

**要求**:
1. 根据修改要求精准调整内容
2. 保留教程中好的部分
3. 确保修改后的内容仍然结构完整
4. 输出格式与原教程保持一致

请直接输出修改后的完整教程内容，然后在末尾添加修改元数据。
使用以下分隔符分隔内容和元数据：
===MODIFICATION_METADATA===
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        logger.info(
            "tutorial_modifier_calling_llm",
            concept_id=concept.concept_id,
            model=self.model_name,
        )
        
        response = await self._call_llm(messages)
        content = response.choices[0].message.content
        
        # 解析输出
        modified_content, metadata = self._parse_modification_output(
            content, 
            concept, 
            modification_requirements
        )
        
        return modified_content, metadata
    
    def _parse_modification_output(
        self,
        llm_output: str,
        concept: Concept,
        requirements: List[str],
    ) -> tuple[str, Dict[str, Any]]:
        """
        解析 LLM 输出，分离教程内容和元数据
        
        Returns:
            (教程内容, 元数据字典)
        """
        # 默认元数据
        default_metadata = {
            "title": concept.name,
            "summary": concept.description,
            "modification_summary": "教程已按要求修改",
            "changes_made": requirements,
            "estimated_completion_time": int(concept.estimated_hours * 60),
        }
        
        # 尝试分离内容和元数据
        separator = "===MODIFICATION_METADATA==="
        
        if separator in llm_output:
            parts = llm_output.split(separator)
            tutorial_content = parts[0].strip()
            metadata_str = parts[1].strip() if len(parts) > 1 else ""
            
            # 尝试解析元数据 JSON
            if metadata_str:
                try:
                    # 提取 JSON
                    if "```json" in metadata_str:
                        json_start = metadata_str.find("```json") + 7
                        json_end = metadata_str.find("```", json_start)
                        metadata_str = metadata_str[json_start:json_end].strip()
                    elif "```" in metadata_str:
                        json_start = metadata_str.find("```") + 3
                        json_end = metadata_str.find("```", json_start)
                        metadata_str = metadata_str[json_start:json_end].strip()
                    
                    # 找到 JSON 对象
                    start = metadata_str.find("{")
                    end = metadata_str.rfind("}") + 1
                    if start >= 0 and end > start:
                        metadata_str = metadata_str[start:end]
                    
                    parsed_metadata = json.loads(metadata_str)
                    # 合并解析的元数据
                    default_metadata.update(parsed_metadata)
                except (json.JSONDecodeError, ValueError) as e:
                    logger.warning(
                        "tutorial_modifier_metadata_parse_failed",
                        error=str(e),
                    )
            
            return tutorial_content, default_metadata
        else:
            # 没有分隔符，整个输出就是教程内容
            return llm_output.strip(), default_metadata
    
    async def _upload_new_version(
        self,
        roadmap_id: str,
        concept_id: str,
        content: str,
        version: int,
    ) -> str:
        """
        上传新版本到 S3
        
        Returns:
            S3 Key（不是预签名 URL）
        """
        s3_key = f"{roadmap_id}/concepts/{concept_id}/v{version}.md"
        
        # 获取 S3 存储工具
        s3_tool = tool_registry.get("s3_storage_v1")
        if not s3_tool:
            raise RuntimeError("S3 Storage Tool 未注册")
        
        # 上传内容
        upload_request = S3UploadRequest(
            key=s3_key,
            content=content,
            content_type="text/markdown",
        )
        
        upload_result = await s3_tool.execute(upload_request)
        
        if not upload_result.success:
            raise RuntimeError(f"上传新版本失败: {s3_key}")
        
        logger.info(
            "tutorial_modifier_uploaded",
            s3_key=s3_key,
            size_bytes=upload_result.size_bytes,
        )
        
        # ✅ 返回 S3 Key 而不是预签名 URL
        return s3_key
    
    async def execute(self, input_data: TutorialModificationInput) -> TutorialModificationOutput:
        """实现基类的抽象方法"""
        return await self.modify(input_data)

