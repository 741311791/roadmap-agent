"""
Structure Validator Agent（结构审查员）
"""
import json
from app.agents.base import BaseAgent
from app.models.domain import (
    RoadmapFramework,
    LearningPreferences,
    ValidationOutput,
    ValidationInput,
)
from app.config.settings import settings
import structlog

logger = structlog.get_logger()


class StructureValidatorAgent(BaseAgent):
    """
    结构审查员 Agent
    
    配置从环境变量加载：
    - VALIDATOR_PROVIDER: 模型提供商（默认: openai）
    - VALIDATOR_MODEL: 模型名称（默认: gpt-4o-mini）
    - VALIDATOR_BASE_URL: 自定义 API 端点（可选）
    - VALIDATOR_API_KEY: API 密钥（必需）
    """
    
    def __init__(
        self,
        agent_id: str = "structure_validator",
        model_provider: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        api_key: str | None = None,
    ):
        super().__init__(
            agent_id=agent_id,
            model_provider=model_provider or settings.VALIDATOR_PROVIDER,
            model_name=model_name or settings.VALIDATOR_MODEL,
            base_url=base_url or settings.VALIDATOR_BASE_URL,
            api_key=api_key or settings.VALIDATOR_API_KEY,
            temperature=0.2,  # 低温度，确保审查的严谨性
            max_tokens=4096,
        )
    
    async def validate(
        self,
        framework: RoadmapFramework,
        user_preferences: LearningPreferences,
    ) -> ValidationOutput:
        """
        验证路线图框架的结构合理性
        
        Args:
            framework: 待验证的路线图框架
            user_preferences: 用户偏好
            
        Returns:
            验证结果
        """
        # 加载 System Prompt
        system_prompt = self._load_system_prompt(
            "structure_validator.j2",
            agent_name="Structure Validator",
            role_description="批判性审查员，专门检查课程架构师设计的路线图是否存在逻辑漏洞、知识断层、时间不合理等问题（对抗原则）。",
            user_goal=user_preferences.learning_goal,
            framework=framework,
        )
        
        # 构建用户消息
        user_message = f"""
请仔细审查以下学习路线图框架，检查是否存在结构问题：

**路线图框架**:
- 标题: {framework.title}
- 总预估时长: {framework.total_estimated_hours} 小时
- 推荐完成周数: {framework.recommended_completion_weeks} 周
- 阶段数量: {len(framework.stages)}

**路线图结构**:
{json.dumps(framework.model_dump(mode='json'), ensure_ascii=False, indent=2)}

**用户约束**:
- 每周可投入时间: {user_preferences.available_hours_per_week} 小时
- 当前水平: {user_preferences.current_level}
- 学习目标: {user_preferences.learning_goal}

请从以下维度进行审查：
1. **结构完整性**：检查所有前置关系是否有效，是否存在循环依赖
2. **知识递进性**：检查概念之间的难度是否合理递增，是否存在知识断层
3. **时间合理性**：检查总学习时长是否符合用户的时间约束
4. **逻辑一致性**：检查阶段顺序是否合理，模块划分是否清晰
5. **用户适配性**：检查路线图是否符合用户的当前水平和学习目标

请以 JSON 格式返回验证结果，严格遵循 ValidationOutput Schema。
"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
        
        # 调用 LLM
        response = await self._call_llm(messages)
        
        # 解析输出
        content = response.choices[0].message.content
        
        try:
            # 提取 JSON（可能包含 markdown 代码块）
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                content = content[json_start:json_end].strip()
            
            # 解析 JSON
            result_dict = json.loads(content)
            
            # 验证并构建输出
            result = ValidationOutput.model_validate(result_dict)
            
            # 记录验证结果
            log_data = {
                "roadmap_id": framework.roadmap_id,
                "roadmap_title": framework.title,
                "stages_count": len(framework.stages),
                "total_hours": framework.total_estimated_hours,
                "recommended_weeks": framework.recommended_completion_weeks,
                "is_valid": result.is_valid,
                "overall_score": result.overall_score,
                "issues_count": len(result.issues),
            }
            
            if result.is_valid:
                # 验证通过
                logger.info("structure_validation_completed", **log_data)
            else:
                # 验证失败：记录详细的失败原因
                critical_issues = [issue for issue in result.issues if issue.severity == "critical"]
                warning_issues = [issue for issue in result.issues if issue.severity == "warning"]
                suggestion_issues = [issue for issue in result.issues if issue.severity == "suggestion"]
                
                # 记录完整的路线图框架内容（用于调试和问题排查）
                # 使用 model_dump 获取完整的 JSON 表示，包含所有 stages、modules 和 concepts
                framework_full = framework.model_dump(mode='json')
                
                # 记录失败原因（限制数量，避免日志过长）
                max_issues_to_log = 10  # 最多记录10个问题
                issues_to_log = result.issues[:max_issues_to_log]
                
                log_data.update({
                    "framework": framework_full,  # 完整的路线图框架内容
                    "critical_issues_count": len(critical_issues),
                    "warning_issues_count": len(warning_issues),
                    "suggestion_issues_count": len(suggestion_issues),
                    "critical_issues": [
                        {
                            "location": issue.location,
                            "issue": issue.issue,
                            "suggestion": issue.suggestion,
                        }
                        for issue in critical_issues[:5]  # 最多记录5个严重问题
                    ],
                    "validation_failed_reasons": [
                        f"[{issue.severity.upper()}] {issue.location}: {issue.issue}"
                        for issue in issues_to_log
                    ],
                    "total_issues": len(result.issues),
                    "logged_issues": len(issues_to_log),
                })
                
                logger.warning(
                    "structure_validation_failed",
                    **log_data,
                    message=(
                        f"路线图验证失败 (ID: {framework.roadmap_id}, 标题: {framework.title})："
                        f"发现 {len(result.issues)} 个问题（严重: {len(critical_issues)}, "
                        f"警告: {len(warning_issues)}, 建议: {len(suggestion_issues)}）"
                    ),
                )
            
            return result
            
        except json.JSONDecodeError as e:
            logger.error("structure_validation_json_parse_error", error=str(e), content=content)
            raise ValueError(f"LLM 输出不是有效的 JSON 格式: {e}")
        except Exception as e:
            logger.error("structure_validation_output_invalid", error=str(e), content=content)
            raise ValueError(f"LLM 输出格式不符合 Schema: {e}")
    
    async def execute(self, input_data: ValidationInput) -> ValidationOutput:
        """实现基类的抽象方法"""
        return await self.validate(
            framework=input_data.framework,
            user_preferences=input_data.user_preferences,
        )

