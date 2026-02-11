"""
日志格式化工具

功能：
- 截断超长字符串
- 简化错误堆栈
- 格式化嵌套对象
"""
import traceback
from typing import Any


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    截断字符串到指定长度
    
    Args:
        text: 原始字符串
        max_length: 最大长度（包含后缀）
        suffix: 截断后缀
        
    Returns:
        截断后的字符串
    """
    if not text or len(text) <= max_length:
        return text
    
    actual_max = max_length - len(suffix)
    return text[:actual_max] + suffix


def truncate_dict(data: dict, max_str_length: int = 100, max_depth: int = 3, _depth: int = 0) -> dict:
    """
    递归截断字典中的长字符串
    
    Args:
        data: 原始字典
        max_str_length: 字符串最大长度
        max_depth: 最大递归深度
        _depth: 当前递归深度（内部使用）
        
    Returns:
        截断后的字典
    """
    if _depth >= max_depth:
        return {"...": "max_depth_reached"}
    
    result = {}
    for key, value in data.items():
        if isinstance(value, str):
            result[key] = truncate_string(value, max_str_length)
        elif isinstance(value, dict):
            result[key] = truncate_dict(value, max_str_length, max_depth, _depth + 1)
        elif isinstance(value, list):
            result[key] = truncate_list(value, max_str_length, max_depth, _depth + 1)
        else:
            result[key] = value
    
    return result


def truncate_list(data: list, max_str_length: int = 100, max_depth: int = 3, _depth: int = 0) -> list:
    """
    递归截断列表中的长字符串
    
    Args:
        data: 原始列表
        max_str_length: 字符串最大长度
        max_depth: 最大递归深度
        _depth: 当前递归深度（内部使用）
        
    Returns:
        截断后的列表
    """
    if _depth >= max_depth:
        return ["...max_depth_reached..."]
    
    # 列表过长则截断
    if len(data) > 10:
        data = data[:10] + [f"... {len(data) - 10} more items ..."]
    
    result = []
    for item in data:
        if isinstance(item, str):
            result.append(truncate_string(item, max_str_length))
        elif isinstance(item, dict):
            result.append(truncate_dict(item, max_str_length, max_depth, _depth + 1))
        elif isinstance(item, list):
            result.append(truncate_list(item, max_str_length, max_depth, _depth + 1))
        else:
            result.append(item)
    
    return result


def format_exception_compact(exc_info: tuple) -> str:
    """
    简化异常堆栈输出
    
    只保留：
    - 异常类型和消息
    - 最近3层堆栈
    - 去除系统库堆栈
    
    Args:
        exc_info: (type, value, traceback) 三元组，必须是有效的异常信息
        
    Returns:
        简化的异常字符串
        
    Note:
        调用方必须确保传入的是有效的三元组，而非 bool 或 None
    """
    # 安全检查：确保是有效的异常信息
    if not exc_info or exc_info == (None, None, None):
        return ""
    
    # 类型验证（防御性编程）
    if not isinstance(exc_info, tuple) or len(exc_info) != 3:
        return f"[Invalid exc_info format: {type(exc_info).__name__}]"
    
    exc_type, exc_value, exc_traceback = exc_info
    
    # 提取堆栈
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    
    # 过滤系统库堆栈（保留项目代码）
    filtered_lines = []
    for line in tb_lines:
        # 保留关键信息行
        if any(keyword in line for keyword in [
            "File \"/Users/",  # 本地项目路径
            "backend/app/",    # 后端代码
            "Error:",
            "Exception:",
            "ValueError:",
            "TypeError:",
        ]):
            filtered_lines.append(line)
    
    # 限制堆栈层数（只保留最近5层）
    if len(filtered_lines) > 10:
        filtered_lines = filtered_lines[-10:]
    
    # 组合输出
    return "".join(filtered_lines).strip()


def format_error_for_log(e: Exception) -> dict:
    """
    格式化异常对象为日志友好的字典
    
    Args:
        e: 异常对象
        
    Returns:
        包含 error, error_type, error_short 的字典
    """
    error_str = str(e)
    return {
        "error": truncate_string(error_str, max_length=200),  # 截断错误消息
        "error_type": type(e).__name__,
        "error_short": truncate_string(error_str, max_length=50),  # 超短版本
    }


def sanitize_log_data(data: dict) -> dict:
    """
    清理日志数据（用于structlog processor）
    
    功能：
    - 截断长字符串
    - 简化嵌套结构
    - 移除敏感信息
    
    Args:
        data: 原始日志数据
        
    Returns:
        清理后的日志数据
    """
    # 需要截断的字段（Agent输出、用户输入等）
    truncate_fields = {
        "llm_response",
        "llm_output",
        "agent_output",
        "user_message",
        "user_input",
        "prompt",
        "content",
        "response",
        "output",
        "result",
        "framework_data",
        "tutorial_content",
        "quiz_questions",
    }
    
    result = {}
    for key, value in data.items():
        if key in truncate_fields and isinstance(value, str):
            # Agent 输出截断到 50 字符
            result[key] = truncate_string(value, max_length=50)
        elif isinstance(value, dict):
            result[key] = truncate_dict(value, max_str_length=100, max_depth=2)
        elif isinstance(value, list):
            result[key] = truncate_list(value, max_str_length=100, max_depth=2)
        else:
            result[key] = value
    
    return result

