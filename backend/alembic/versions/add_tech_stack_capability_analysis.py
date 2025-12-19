"""add tech stack capability analysis

添加技术栈能力分析字段到 user_profiles 表

Revision ID: add_tech_capability_analysis
Revises: add_user_profile
Create Date: 2025-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tech_capability_analysis'
down_revision: Union[str, None] = 'add_user_profile'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    为 user_profiles.tech_stack 添加能力分析字段
    
    tech_stack 的新结构：
    [
        {
            "technology": "python",
            "proficiency": "intermediate",
            "capability_analysis": {
                "overall_assessment": "整体评价文本",
                "strengths": ["优势1", "优势2"],
                "weaknesses": ["薄弱点1", "薄弱点2"],
                "knowledge_gaps": [
                    {
                        "topic": "主题",
                        "description": "说明",
                        "priority": "high/medium/low",
                        "recommendations": ["建议1"]
                    }
                ],
                "learning_suggestions": ["建议1", "建议2"],
                "proficiency_verification": {
                    "claimed_level": "intermediate",
                    "verified_level": "intermediate",
                    "confidence": "high",
                    "reasoning": "依据"
                },
                "score_breakdown": {
                    "easy": {"correct": 6, "total": 7, "percentage": 85.7},
                    "medium": {"correct": 5, "total": 7, "percentage": 71.4},
                    "hard": {"correct": 2, "total": 6, "percentage": 33.3}
                },
                "analyzed_at": "2025-12-19T10:00:00"
            }
        }
    ]
    
    注意：这是一个数据结构变更，不需要修改表结构，
    因为 tech_stack 已经是 JSON 类型，可以存储任意结构。
    此迁移文件主要用于文档记录和版本管理。
    """
    # 无需修改表结构，tech_stack 已经是 JSON 类型
    # 此迁移仅用于记录数据结构变更
    pass


def downgrade() -> None:
    """
    降级：移除能力分析数据
    
    注意：这会删除所有已存储的能力分析数据
    """
    # 无需修改表结构
    # 如需清理数据，可在应用层处理
    pass

