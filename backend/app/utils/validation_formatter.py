"""
ValidationOutput 格式化器

将 StructureValidatorAgent 的 ValidationOutput 转换为自然语言 user_feedback，
供 EditPlanAnalyzerAgent 使用。

核心职责：
- 将结构化的验证结果转换为自然语言描述
- 保持与人工反馈相同的格式风格
- 确保 EditPlanAnalyzerAgent 能正确解析修改意图
"""
from app.models.domain import ValidationOutput


def format_validation_to_feedback(validation_output: ValidationOutput) -> str:
    """
    将 ValidationOutput 格式化为自然语言 user_feedback
    
    格式化策略：
    - Critical 问题 → 必须修复的问题（优先级最高）
    - Warning 问题 → 建议修复的问题
    - StructuralSuggestion → 可选优化建议
    - 维度评分 → 作为上下文参考
    
    Args:
        validation_output: 验证器的输出结果
        
    Returns:
        格式化后的自然语言 feedback，可直接传给 EditPlanAnalyzerAgent
    """
    lines = []
    
    # 1. 总体状态摘要
    status = "未通过" if not validation_output.is_valid else "通过"
    lines.append(f"路线图结构验证{status}（评分：{validation_output.overall_score:.0f}/100）")
    lines.append("")
    
    # 2. Critical 问题（必须修复）
    critical_issues = [i for i in validation_output.issues if i.severity == "critical"]
    if critical_issues:
        lines.append("## 必须修复的问题：")
        for issue in critical_issues:
            lines.append(f"- 【{issue.location}】{issue.issue}")
            lines.append(f"  建议：{issue.suggestion}")
            # 如果有结构化建议，添加具体操作指导
            if issue.structural_suggestion:
                suggestion = issue.structural_suggestion
                lines.append(f"  具体操作：在 {suggestion.target_location} 执行 {suggestion.action}")
                if suggestion.content:
                    lines.append(f"  内容：{suggestion.content}")
        lines.append("")
    
    # 3. Warning 问题（建议修复）
    warning_issues = [i for i in validation_output.issues if i.severity == "warning"]
    if warning_issues:
        lines.append("## 建议修复的问题：")
        for issue in warning_issues:
            lines.append(f"- 【{issue.location}】{issue.issue}")
            lines.append(f"  建议：{issue.suggestion}")
            # 如果有结构化建议，添加具体操作指导
            if issue.structural_suggestion:
                suggestion = issue.structural_suggestion
                lines.append(f"  具体操作：在 {suggestion.target_location} 执行 {suggestion.action}")
        lines.append("")
    
    # 4. 改进建议（可选优化）
    if validation_output.improvement_suggestions:
        lines.append("## 可选优化建议：")
        for suggestion in validation_output.improvement_suggestions:
            lines.append(f"- 在 {suggestion.target_location} 执行 {suggestion.action}")
            lines.append(f"  原因：{suggestion.reason}")
            if suggestion.content:
                lines.append(f"  内容：{suggestion.content}")
        lines.append("")
    
    # 5. 维度评分摘要（作为上下文参考）
    if validation_output.dimension_scores:
        lines.append("## 各维度评分参考：")
        for score in validation_output.dimension_scores:
            lines.append(f"- {score.dimension}: {score.score:.0f}/100（{score.rationale}）")
        lines.append("")
    
    # 6. 验证摘要（如果有）
    if validation_output.validation_summary:
        lines.append(f"## 验证摘要：{validation_output.validation_summary}")
    
    return "\n".join(lines)

