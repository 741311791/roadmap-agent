"""migrate_full_analysis_data_to_constraints_format

Revision ID: bd3a3251d400
Revises: 2db1e86f6eee
Create Date: 2026-01-31 11:13:55.000018

"""
from typing import Sequence, Union
import json

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = 'bd3a3251d400'
down_revision: Union[str, None] = '2db1e86f6eee'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """将旧格式的 full_analysis_data 转换为约束文本格式"""
    
    conn = op.get_bind()
    
    # 查询所有记录
    result = conn.execute(text("""
        SELECT intent_id, full_analysis_data, 
               parsed_goal, difficulty_profile, time_constraint,
               skill_gap_analysis, recommended_focus,
               content_format_weights, language_preferences,
               key_technologies, personalized_suggestions,
               estimated_learning_path_type, user_profile_summary
        FROM intent_analysis_metadata
        WHERE full_analysis_data IS NOT NULL
    """))
    
    rows = result.fetchall()
    migrated_count = 0
    skipped_count = 0
    
    # 遍历每条记录，转换格式
    for row in rows:
        intent_id = row[0]
        old_data = row[1]  # 旧的 full_analysis_data
        
        # 如果已经是新格式（字典的第一个 key 是中文约束名称），则跳过
        if old_data and isinstance(old_data, dict):
            first_key = next(iter(old_data.keys()), None)
            if first_key and ("约束" in first_key):
                skipped_count += 1
                continue  # 已经是新格式
        
        # 生成新的约束字典
        new_constraints = {}
        
        # 通用约束
        if row[12]:  # user_profile_summary
            new_constraints["用户画像约束"] = f"用户画像：{row[12]}"
        
        if row[2]:  # parsed_goal
            new_constraints["用户目标约束"] = f"用户学习目标：{row[2]}"
        
        language_prefs = row[8]  # language_preferences
        if language_prefs:
            if isinstance(language_prefs, str):
                language_prefs = json.loads(language_prefs)
            if language_prefs.get("primary_language"):
                lang_map = {"zh-CN": "简体中文", "zh": "简体中文", "en": "英语", "ja": "日语"}
                primary_lang = language_prefs["primary_language"]
                new_constraints["生成语言约束"] = f"请使用{lang_map.get(primary_lang, primary_lang)}生成响应内容"
        
        # 特定约束
        if row[3]:  # difficulty_profile
            new_constraints["难度约束"] = f"用户难度画像：{row[3]}，请确保内容难度适中"
        
        if row[4]:  # time_constraint
            new_constraints["时间约束"] = f"时间约束：{row[4]}"
        
        if row[11]:  # estimated_learning_path_type
            new_constraints["学习路径类型约束"] = f"学习路径类型：{row[11]}"
        
        if row[5]:  # skill_gap_analysis
            if isinstance(row[5], str):
                skill_gaps_list = json.loads(row[5])
            else:
                skill_gaps_list = row[5] if isinstance(row[5], list) else []
            
            if skill_gaps_list:
                skill_gaps = "、".join(skill_gaps_list[:3])
                new_constraints["技能差距约束"] = f"用户技能差距：{skill_gaps}，需重点补强这些方面"
        
        if row[6]:  # recommended_focus
            if isinstance(row[6], str):
                focus_list = json.loads(row[6])
            else:
                focus_list = row[6] if isinstance(row[6], list) else []
            
            if focus_list:
                focus = "、".join(focus_list)
                new_constraints["推荐重点约束"] = f"推荐学习重点：{focus}"
        
        if row[7]:  # content_format_weights
            if isinstance(row[7], str):
                weights = json.loads(row[7])
            else:
                weights = row[7] if isinstance(row[7], dict) else {}
            
            if weights:
                preferences = []
                if weights.get("visual", 0) > 0.3:
                    preferences.append("视觉化内容（图表、图示）")
                if weights.get("hands_on", 0) > 0.3:
                    preferences.append("实践性内容（代码示例、项目）")
                if preferences:
                    new_constraints["内容格式偏好约束"] = f"用户偏好：{'、'.join(preferences)}"
        
        if row[8]:  # language_preferences (再次检查次要语言)
            if isinstance(row[8], str):
                lang_prefs = json.loads(row[8])
            else:
                lang_prefs = row[8] if isinstance(row[8], dict) else {}
            
            if lang_prefs.get("secondary_language"):
                primary = lang_prefs.get("primary_language", "zh")
                secondary = lang_prefs["secondary_language"]
                if secondary and secondary != primary:
                    new_constraints["语言资源分配约束"] = f"主要语言：{primary}，次要语言：{secondary}，建议资源比例为 8:2"
        
        if row[9]:  # key_technologies
            if isinstance(row[9], str):
                techs_list = json.loads(row[9])
            else:
                techs_list = row[9] if isinstance(row[9], list) else []
            
            if techs_list:
                techs = "、".join(techs_list[:5])
                new_constraints["技术栈约束"] = f"关键技术栈：{techs}"
        
        if row[10]:  # personalized_suggestions
            if isinstance(row[10], str):
                suggestions_list = json.loads(row[10])
            else:
                suggestions_list = row[10] if isinstance(row[10], list) else []
            
            if suggestions_list:
                suggestions = "；".join(suggestions_list[:3])
                new_constraints["个性化建议约束"] = f"个性化建议：{suggestions}"
        
        # 更新记录（使用 JSON 类型）
        conn.execute(
            text("""
                UPDATE intent_analysis_metadata
                SET full_analysis_data = CAST(:new_data AS JSONB)
                WHERE intent_id = :intent_id
            """),
            {"new_data": json.dumps(new_constraints, ensure_ascii=False), "intent_id": intent_id}
        )
        migrated_count += 1
    
    print(f"✅ Migration completed: {migrated_count} records migrated, {skipped_count} records skipped (already in new format)")


def downgrade() -> None:
    """回滚不支持（数据转换是单向的）"""
    print("⚠️ Downgrade not supported for this migration (data conversion is one-way)")

