"""
笔记记录Agent

负责从用户消息中提取关键知识点并整理成结构化笔记。
"""
import json
from typing import AsyncIterator, Optional
from app.agents.base import BaseAgent
from app.models.domain import MentorAgentInput, NoteRecordResult
from app.config.settings import settings
from app.core.tool_registry import tool_registry
import structlog

logger = structlog.get_logger()


class NoteRecorderAgent(BaseAgent):
    """
    笔记记录Agent
    
    功能：
    1. 从用户消息中提取关键知识点
    2. 格式化笔记内容
    3. 调用note_tool保存到数据库
    
    配置从环境变量加载：
    - MENTOR_PROVIDER / ANALYZER_PROVIDER: 模型提供商
    - MENTOR_MODEL / ANALYZER_MODEL: 模型名称
    """
    
    def __init__(
        self,
        agent_id: str = "note_recorder_agent",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or getattr(settings, 'NOTE_RECORDER_PROVIDER', None) or settings.ANALYZER_PROVIDER,
            model_name=model_name or getattr(settings, 'NOTE_RECORDER_MODEL', None) or settings.ANALYZER_MODEL,
            base_url=base_url or getattr(settings, 'NOTE_RECORDER_BASE_URL', None) or settings.ANALYZER_BASE_URL,
            api_key=api_key or getattr(settings, 'NOTE_RECORDER_API_KEY', None) or settings.ANALYZER_API_KEY,
            temperature=0.3,  # 较低温度确保结构化输出
            max_tokens=1024,
        )
    
    async def execute(self, input_data: MentorAgentInput) -> Optional[NoteRecordResult]:
        """
        提取并格式化笔记内容
        
        Args:
            input_data: 伴学Agent输入
            
        Returns:
            笔记记录结果，如果无法识别为笔记请求则返回None
        """
        logger.info(
            "note_recorder_started",
            user_id=input_data.user_id,
            message_preview=input_data.user_message[:50],
        )
        
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "note_recorder.j2",
            user_message=input_data.user_message,
            concept_name=input_data.concept_name,
            concept_description=input_data.concept_description,
            roadmap_title=input_data.roadmap_title,
            chat_history=input_data.session_history,
        )
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": input_data.user_message},
        ]
        
        try:
            response = await self._call_llm(messages)
            content = response.choices[0].message.content.strip()
            
            # 解析JSON响应
            result = self._parse_result(content)
            
            if result:
                logger.info(
                    "note_recorder_completed",
                    title=result.title,
                    tags=result.tags,
                )
            else:
                logger.info("note_recorder_not_note_request")
            
            return result
        
        except Exception as e:
            logger.error(
                "note_recorder_failed",
                error=str(e),
                user_id=input_data.user_id,
            )
            return None
    
    async def execute_stream(
        self,
        input_data: MentorAgentInput,
    ) -> AsyncIterator[str]:
        """
        流式执行笔记记录
        
        先提取笔记内容，然后保存，最后返回确认消息。
        
        Args:
            input_data: 伴学Agent输入
            
        Yields:
            流式文本片段
        """
        # 提取笔记内容
        note_result = await self.execute(input_data)
        
        if not note_result:
            yield "抱歉，我无法识别你想要记录什么内容。\n\n"
            yield "你可以这样告诉我：\n"
            yield "- \"帮我记录一下刚才学的内容\"\n"
            yield "- \"保存这个知识点：XXX\"\n"
            yield "- \"记下这个重点\"\n"
            return
        
        # 显示笔记预览
        yield f"📝 **笔记预览**\n\n"
        yield f"### {note_result.title}\n\n"
        
        # 逐行输出内容
        for line in note_result.content.split('\n'):
            yield line + '\n'
        
        yield f"\n**标签**: {', '.join(note_result.tags)}\n\n"
        
        # 保存笔记
        yield "正在保存笔记...\n"
        
        try:
            note_tool = tool_registry.get("note_recorder_v1")
            if note_tool:
                from app.tools.mentor.note_recorder_tool import NoteRecorderInput
                
                save_input = NoteRecorderInput(
                    user_id=input_data.user_id,
                    roadmap_id=input_data.roadmap_id,
                    concept_id=input_data.concept_id or "",
                    content=note_result.content,
                    title=note_result.title,
                    tags=note_result.tags,
                    source="ai_generated",
                )
                
                save_result = await note_tool.execute(save_input)
                
                if save_result.success:
                    yield f"\n✅ 笔记已保存！(ID: {save_result.note_id[:8]}...)\n"
                else:
                    yield f"\n❌ 保存失败: {save_result.message}\n"
            else:
                yield "\n⚠️ 笔记工具不可用，内容未保存\n"
        
        except Exception as e:
            logger.error(
                "note_save_failed",
                error=str(e),
                user_id=input_data.user_id,
            )
            yield f"\n❌ 保存出错: {str(e)}\n"
    
    def _parse_result(self, content: str) -> Optional[NoteRecordResult]:
        """
        解析LLM返回的JSON结果
        
        Args:
            content: LLM返回的内容
            
        Returns:
            笔记记录结果，如果解析失败或是错误响应则返回None
        """
        # 尝试从可能的代码块中提取JSON
        if "```json" in content:
            start = content.find("```json") + 7
            end = content.find("```", start)
            content = content[start:end].strip()
        elif "```" in content:
            start = content.find("```") + 3
            end = content.find("```", start)
            content = content[start:end].strip()
        
        try:
            data = json.loads(content)
            
            # 检查是否是错误响应
            if "error" in data:
                return None
            
            return NoteRecordResult(
                title=data.get("title", "学习笔记"),
                content=data.get("content", ""),
                tags=data.get("tags", []),
                key_points=data.get("key_points", []),
            )
        
        except json.JSONDecodeError:
            logger.warning(
                "note_recorder_json_parse_failed",
                content=content[:100],
            )
            return None
