"""
Prompt 模板加载器（Jinja2）
"""
import os
from pathlib import Path
from typing import Dict, Any
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import structlog

logger = structlog.get_logger()


def to_json_filter(value):
    """Jinja2 自定义过滤器：将对象转换为 JSON 字符串"""
    if value is None:
        return "null"
    if isinstance(value, (str, int, float, bool)):
        return json.dumps(value, ensure_ascii=False)
    try:
        # 如果是 Pydantic 模型，使用 model_dump_json
        if hasattr(value, 'model_dump_json'):
            return value.model_dump_json(ensure_ascii=False)
        # 如果是 Pydantic 模型，使用 model_dump
        elif hasattr(value, 'model_dump'):
            return json.dumps(value.model_dump(), ensure_ascii=False, indent=2)
        # 否则使用标准 json.dumps
        else:
            return json.dumps(value, ensure_ascii=False, indent=2, default=str)
    except Exception as e:
        logger.warning("json_filter_error", error=str(e), value_type=type(value).__name__)
        return str(value)


class PromptLoader:
    """Prompt 模板加载器"""
    
    def __init__(self, template_dir: str | None = None):
        """
        初始化 Prompt 加载器
        
        Args:
            template_dir: 模板目录路径，默认为项目根目录下的 prompts/
        """
        if template_dir is None:
            # 获取项目根目录（backend/）
            current_file = Path(__file__)
            project_root = current_file.parent.parent.parent
            template_dir = str(project_root / "prompts")
        
        self.template_dir = template_dir
        self.env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(['html', 'xml']),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        # 注册自定义过滤器
        self.env.filters['to_json'] = to_json_filter
        logger.info("prompt_loader_initialized", template_dir=template_dir)
    
    def render(self, template_name: str, **kwargs) -> str:
        """
        渲染模板
        
        Args:
            template_name: 模板文件名（如 'intent_analyzer.j2'）
            **kwargs: 模板变量
            
        Returns:
            渲染后的字符串
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**kwargs)
        except Exception as e:
            logger.error(
                "prompt_render_failed",
                template_name=template_name,
                error=str(e)
            )
            raise

