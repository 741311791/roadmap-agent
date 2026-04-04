"""
Linear 产品路书同步服务
"""
import re
from datetime import datetime
from typing import Any

import httpx
import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.config.settings import settings
from app.models.database import RoadmapFeature, RoadmapMilestone
from app.models.domain import RoadmapSyncResponse

logger = structlog.get_logger()

LINEAR_GRAPHQL_ENDPOINT = "https://api.linear.app/graphql"
MEDIA_URL_PATTERN = re.compile(
    r"(https?://[^\s)]+(?:youtube\.com/watch\?v=[^\s)]+|youtu\.be/[^\s)]+|bilibili\.com/video/[^\s)]+))",
    re.IGNORECASE,
)


class LinearSyncService:
    """
    Linear 产品路书同步服务
    """

    async def sync_all(self, db: AsyncSession) -> RoadmapSyncResponse:
        """
        从 Linear 拉取产品路书数据并全量覆盖本地快照
        """
        self._ensure_configured()
        snapshot = await self._fetch_linear_snapshot()
        response = await self._replace_snapshot(db, snapshot)
        logger.info(
            "linear_roadmap_sync_completed",
            milestone_count=response.milestone_count,
            feature_count=response.feature_count,
            upcoming_feature_count=response.upcoming_feature_count,
        )
        return response

    def _ensure_configured(self) -> None:
        """
        检查 Linear 同步配置
        """
        if not settings.LINEAR_API_KEY:
            raise RuntimeError("LINEAR_API_KEY 未配置，无法同步产品路书。")

    async def _fetch_linear_snapshot(self) -> dict[str, list[dict[str, Any]]]:
        """
        拉取 Linear 快照数据
        """
        team_id = await self._resolve_team_id()
        projects = await self._fetch_projects(team_id)

        milestones: list[dict[str, Any]] = []
        features: list[dict[str, Any]] = []
        seen_milestone_ids: set[str] = set()
        seen_feature_ids: set[str] = set()

        for project in projects:
            milestone_linear_id = str(project["id"])
            if milestone_linear_id in seen_milestone_ids:
                continue

            project_issues = await self._fetch_project_issues(milestone_linear_id)
            if not project_issues:
                continue

            seen_milestone_ids.add(milestone_linear_id)
            milestones.append(
                {
                    "linear_id": milestone_linear_id,
                    "title": project.get("name") or "Untitled Project",
                    "description": project.get("description"),
                    "status": self._resolve_milestone_status(
                        completed_at=project.get("completedAt"),
                        start_date=project.get("startDate"),
                    ),
                    "start_date": self._parse_datetime(project.get("startDate")),
                    "end_date": self._parse_datetime(project.get("targetDate")),
                }
            )
            for index, issue in enumerate(project_issues):
                feature_linear_id = str(issue["id"])
                if feature_linear_id in seen_feature_ids:
                    continue
                seen_feature_ids.add(feature_linear_id)
                features.append(
                    self._build_feature_payload(
                        issue=issue,
                        milestone_linear_id=milestone_linear_id,
                        sort_order=index,
                    )
                )

        return {
            "milestones": milestones,
            "features": features,
        }

    async def _resolve_team_id(self) -> str:
        """
        根据配置解析 Team ID
        """
        query = """
        query RoadmapTeams {
          teams(first: 100) {
            nodes {
              id
              key
              name
            }
          }
        }
        """
        payload = await self._execute_graphql(query=query, variables={})
        teams = payload.get("teams", {}).get("nodes", []) or []
        configured_team = (settings.LINEAR_TEAM_ID or "").strip()

        for team in teams:
            if configured_team in {
                str(team.get("id", "")),
                str(team.get("key", "")),
                str(team.get("name", "")),
            }:
                return str(team["id"])

        raise RuntimeError(f"未找到 Linear Team：{configured_team}")

    async def _fetch_projects(self, team_id: str) -> list[dict[str, Any]]:
        """
        拉取指定 Team 下的 Project 列表
        """
        query = """
        query RoadmapProjects($teamId: ID!) {
          projects(
            first: 50
            filter: {
              accessibleTeams: { some: { id: { eq: $teamId } } }
            }
          ) {
            nodes {
              id
              name
              description
              startDate
              targetDate
              completedAt
            }
          }
        }
        """
        payload = await self._execute_graphql(
            query=query,
            variables={"teamId": team_id},
        )
        return payload.get("projects", {}).get("nodes", []) or []

    async def _fetch_project_issues(self, project_id: str) -> list[dict[str, Any]]:
        """
        拉取指定 Project 下的 Issue 列表
        """
        query = """
        query RoadmapProjectIssues($projectId: String!) {
          project(id: $projectId) {
            issues(first: 100) {
              nodes {
                id
                title
                description
                url
                state {
                  type
                }
                labels {
                  nodes {
                    name
                  }
                }
              }
            }
          }
        }
        """
        payload = await self._execute_graphql(
            query=query,
            variables={"projectId": project_id},
        )
        project = payload.get("project")
        if not project:
            return []
        return project.get("issues", {}).get("nodes", []) or []

    def _build_feature_payload(
        self,
        *,
        issue: dict[str, Any],
        milestone_linear_id: str | None,
        sort_order: int,
    ) -> dict[str, Any]:
        """
        构建单个功能卡片载荷
        """
        description = issue.get("description")
        labels = [
            str(label.get("name"))
            for label in issue.get("labels", {}).get("nodes", []) or []
            if label.get("name")
        ]
        return {
            "linear_id": str(issue["id"]),
            "milestone_linear_id": milestone_linear_id,
            "title": issue.get("title") or "Untitled Feature",
            "description": description,
            "status": self._resolve_feature_status(issue.get("state", {}).get("type")),
            "demo_url": self._extract_demo_url(description),
            "labels": labels,
            "linear_url": issue.get("url"),
            "sort_order": sort_order,
        }

    async def _replace_snapshot(
        self,
        db: AsyncSession,
        snapshot: dict[str, list[dict[str, Any]]],
    ) -> RoadmapSyncResponse:
        """
        使用最新快照替换本地产品路书数据
        """
        await db.execute(delete(RoadmapFeature))
        await db.execute(delete(RoadmapMilestone))
        await db.flush()

        milestone_id_map: dict[str, int] = {}
        milestone_records: list[RoadmapMilestone] = []

        for index, milestone in enumerate(snapshot["milestones"]):
            record = RoadmapMilestone(
                linear_id=milestone["linear_id"],
                title=milestone["title"],
                description=milestone["description"],
                status=milestone["status"],
                start_date=milestone["start_date"],
                end_date=milestone["end_date"],
                sort_order=index,
            )
            db.add(record)
            milestone_records.append(record)

        await db.flush()

        for record in milestone_records:
            if record.id is not None:
                milestone_id_map[record.linear_id] = record.id

        upcoming_feature_count = 0
        feature_count = 0
        for feature in snapshot["features"]:
            milestone_id = milestone_id_map.get(feature["milestone_linear_id"])
            if milestone_id is None and feature["status"] == "planned":
                upcoming_feature_count += 1

            db.add(
                RoadmapFeature(
                    linear_id=feature["linear_id"],
                    milestone_id=milestone_id,
                    title=feature["title"],
                    description=feature["description"],
                    status=feature["status"],
                    demo_url=feature["demo_url"],
                    labels=feature["labels"],
                    linear_url=feature["linear_url"],
                    sort_order=feature["sort_order"],
                )
            )
            feature_count += 1

        await db.flush()

        return RoadmapSyncResponse(
            milestone_count=len(milestone_records),
            feature_count=feature_count,
            upcoming_feature_count=upcoming_feature_count,
        )

    async def _execute_graphql(
        self,
        *,
        query: str,
        variables: dict[str, Any],
    ) -> dict[str, Any]:
        """
        执行一次 Linear GraphQL 请求
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                LINEAR_GRAPHQL_ENDPOINT,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": settings.LINEAR_API_KEY or "",
                },
                json={
                    "query": query,
                    "variables": variables,
                },
            )
            response.raise_for_status()
            payload = response.json()

        if payload.get("errors"):
            first_error = payload["errors"][0]
            raise RuntimeError(first_error.get("message", "Linear GraphQL 请求失败。"))

        data = payload.get("data")
        if not data:
            raise RuntimeError("Linear GraphQL 未返回 data 字段。")
        return data

    def _resolve_milestone_status(
        self,
        *,
        completed_at: str | None,
        start_date: str | None,
    ) -> str:
        """
        解析里程碑状态
        """
        if completed_at:
            return "completed"

        parsed_start_date = self._parse_datetime(start_date)
        if parsed_start_date and parsed_start_date > datetime.utcnow():
            return "upcoming"

        return "active"

    def _resolve_feature_status(self, state_type: str | None) -> str:
        """
        将 Linear 状态映射为公开页功能状态
        """
        normalized_state = (state_type or "").lower()
        if normalized_state in {"completed", "done"}:
            return "released"
        if normalized_state in {"started", "in_progress", "inprogress"}:
            return "in_progress"
        return "planned"

    def _extract_demo_url(self, description: str | None) -> str | None:
        """
        从描述中提取媒体演示链接
        """
        if not description:
            return None
        match = MEDIA_URL_PATTERN.search(description)
        return match.group(1) if match else None

    def _parse_datetime(self, raw_value: str | None) -> datetime | None:
        """
        将 Linear 日期字符串解析为 datetime
        """
        if not raw_value:
            return None

        normalized = raw_value.replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(normalized).replace(tzinfo=None)
        except ValueError:
            return None


linear_sync_service = LinearSyncService()


def get_linear_sync_service() -> LinearSyncService:
    """
    获取 Linear 产品路书同步服务单例
    """
    return linear_sync_service
