/**
 * 产品路书公开页 API
 */
import { apiClient } from '@/lib/api/client';
import type { Locale } from '@/i18n/config';

export type PublicMilestoneStatus = 'active' | 'completed' | 'upcoming';
export type PublicFeatureStatus = 'released' | 'in_progress' | 'planned';
export type PlanningItemStatus = 'open' | 'accepted' | 'rejected';

export interface PublicRoadmapFeature {
  id: number;
  linear_id: string;
  milestone_id: number | null;
  title: string;
  description?: string | null;
  status: PublicFeatureStatus;
  demo_url?: string | null;
  labels: string[];
  linear_url?: string | null;
  sort_order: number;
}

export interface PublicRoadmapMilestone {
  id: number;
  linear_id: string;
  title: string;
  description?: string | null;
  status: PublicMilestoneStatus;
  start_date?: string | null;
  end_date?: string | null;
  sort_order: number;
  features: PublicRoadmapFeature[];
}

export interface PublicRoadmapDataResponse {
  milestones: PublicRoadmapMilestone[];
  upcoming_features: PublicRoadmapFeature[];
}

export interface PublicPlanningItem {
  id: number;
  title: string;
  description?: string | null;
  vote_count: number;
  status: PlanningItemStatus;
  created_at: string;
}

export interface PublicPlanningItemListResponse {
  items: PublicPlanningItem[];
  total: number;
}

export interface PlanningItemCreateRequest {
  title: string;
  description?: string | null;
  submitter_email?: string | null;
}

export interface PlanningItemVoteResponse {
  item_id: number;
  vote_count: number;
  already_voted: boolean;
}

export function getPublicRoadmapMockData(locale: Locale): PublicRoadmapDataResponse {
  if (locale === 'zh') {
    return {
      milestones: [
        {
          id: 1,
          linear_id: 'cycle-foundation',
          title: 'v1.0 基础能力',
          description: '用多 Agent 工作流打通路线图生成的核心链路。',
          status: 'completed',
          start_date: '2025-01-10T00:00:00',
          end_date: '2025-02-05T00:00:00',
          sort_order: 0,
          features: [
            {
              id: 101,
              linear_id: 'issue-roadmap-generation',
              milestone_id: 1,
              title: 'AI 路线图生成',
              description: '根据一个学习目标自动生成 Stage-Module-Concept 结构，并串联验证与审核环节。',
              status: 'released',
              demo_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
              labels: ['langgraph', 'multi-agent'],
              linear_url: 'https://linear.app',
              sort_order: 0,
            },
            {
              id: 102,
              linear_id: 'issue-learning-stages',
              milestone_id: 1,
              title: '沉浸式学习阶段页',
              description: '提供分阶段学习视图、概念进度和更轻量的结构化导航体验。',
              status: 'released',
              demo_url: 'https://www.bilibili.com/video/BV1GJ411x7h7',
              labels: ['next.js', 'motion'],
              linear_url: 'https://linear.app',
              sort_order: 1,
            },
            {
              id: 103,
              linear_id: 'issue-celery-pipeline',
              milestone_id: 1,
              title: 'Celery 异步任务链路',
              description: '把重型生成任务放进 Worker，前端可持续接收实时进度而不阻塞主流程。',
              status: 'released',
              demo_url: null,
              labels: ['celery', 'redis'],
              linear_url: 'https://linear.app',
              sort_order: 2,
            },
          ],
        },
        {
          id: 2,
          linear_id: 'cycle-mentor',
          title: 'v2.0 AI Mentor',
          description: '围绕上下文感知、长期记忆和模型路由，构建更懂用户的学习助手。',
          status: 'active',
          start_date: '2025-03-01T00:00:00',
          end_date: '2025-04-10T00:00:00',
          sort_order: 1,
          features: [
            {
              id: 201,
              linear_id: 'issue-mentor-chat',
              milestone_id: 2,
              title: 'Mentor 对话界面',
              description: '支持流式回复、Markdown 渲染、多线程会话，并理解当前学习上下文。',
              status: 'released',
              demo_url: 'https://www.youtube.com/watch?v=ScMzIvxBSi4',
              labels: ['assistant-ui', 'streaming'],
              linear_url: 'https://linear.app',
              sort_order: 0,
            },
            {
              id: 202,
              linear_id: 'issue-memory',
              milestone_id: 2,
              title: '长期记忆能力',
              description: '记住你之前的问题、薄弱点与进度，让学习建议更持续、更个性化。',
              status: 'in_progress',
              demo_url: null,
              labels: ['mem0', 'pgvector'],
              linear_url: 'https://linear.app',
              sort_order: 1,
            },
            {
              id: 203,
              linear_id: 'issue-model-registry',
              milestone_id: 2,
              title: '模型注册表与 Thinking Mode',
              description: '支持后台配置模型能力，并在复杂问题下自动切换更适合的推理路线。',
              status: 'in_progress',
              demo_url: null,
              labels: ['admin', 'llm-routing'],
              linear_url: 'https://linear.app',
              sort_order: 2,
            },
          ],
        },
        {
          id: 3,
          linear_id: 'cycle-community',
          title: 'v3.0 社区协作',
          description: '围绕公开分享、协同学习与路线图发现，打开更强的社区场景。',
          status: 'upcoming',
          start_date: '2025-05-01T00:00:00',
          end_date: '2025-06-15T00:00:00',
          sort_order: 2,
          features: [
            {
              id: 301,
              linear_id: 'issue-gallery',
              milestone_id: 3,
              title: '公开路线图广场',
              description: '浏览社区路线图、复制到自己的空间，并比较不同学习路径的设计方式。',
              status: 'planned',
              demo_url: null,
              labels: ['discovery'],
              linear_url: 'https://linear.app',
              sort_order: 0,
            },
            {
              id: 302,
              linear_id: 'issue-study-group',
              milestone_id: 3,
              title: '学习小组房间',
              description: '让同一路线图的学习者可以实时共享进度、卡点和学习笔记。',
              status: 'planned',
              demo_url: null,
              labels: ['real-time', 'websocket'],
              linear_url: 'https://linear.app',
              sort_order: 1,
            },
          ],
        },
      ],
      upcoming_features: [
        {
          id: 401,
          linear_id: 'issue-mentor-agent-refactor',
          milestone_id: null,
          title: '重构 Mentor Agent 核心消息结构',
          description: '统一 MentorAgent 在前后端之间流转的消息结构，降低后续迭代时的复杂度。',
          status: 'in_progress',
          demo_url: null,
          labels: ['mentor'],
          linear_url: 'https://linear.app',
          sort_order: 0,
        },
        {
          id: 402,
          linear_id: 'issue-linear-feedback',
          milestone_id: null,
          title: '推进用户反馈接入 Linear',
          description: '打通用户反馈提交流程，分类与写入 Linear 的闭环，让反馈可以直接进入产品迭代。',
          status: 'in_progress',
          demo_url: null,
          labels: ['linear'],
          linear_url: 'https://linear.app',
          sort_order: 1,
        },
        {
          id: 403,
          linear_id: 'issue-mobile-app',
          milestone_id: null,
          title: '移动端应用（iOS / Android）',
          description: '支持离线内容、学习提醒和更轻量的随手复习体验。',
          status: 'planned',
          demo_url: null,
          labels: ['mobile'],
          linear_url: 'https://linear.app',
          sort_order: 2,
        },
        {
          id: 404,
          linear_id: 'issue-certificate',
          milestone_id: null,
          title: '结业证书生成',
          description: '生成可分享、可验证的学习完成证书，并附带路线图元数据。',
          status: 'planned',
          demo_url: null,
          labels: ['credential'],
          linear_url: 'https://linear.app',
          sort_order: 3,
        },
      ],
    };
  }

  return {
    milestones: [
      {
        id: 1,
        linear_id: 'cycle-foundation',
        title: 'v1.0 Foundation',
        description: 'Core roadmap generation pipeline powered by multi-agent AI.',
        status: 'completed',
        start_date: '2025-01-10T00:00:00',
        end_date: '2025-02-05T00:00:00',
        sort_order: 0,
        features: [
          {
            id: 101,
            linear_id: 'issue-roadmap-generation',
            milestone_id: 1,
            title: 'AI Roadmap Generation',
            description:
              'Generate a full Stage-Module-Concept roadmap from a single learning goal with validation and review stages.',
            status: 'released',
            demo_url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
            labels: ['langgraph', 'multi-agent'],
            linear_url: 'https://linear.app',
            sort_order: 0,
          },
          {
            id: 102,
            linear_id: 'issue-learning-stages',
            milestone_id: 1,
            title: 'Interactive Learning Stages',
            description:
              'An immersive stage view with concept progress, structured navigation, and lightweight stage summaries.',
            status: 'released',
            demo_url: 'https://www.bilibili.com/video/BV1GJ411x7h7',
            labels: ['next.js', 'motion'],
            linear_url: 'https://linear.app',
            sort_order: 1,
          },
          {
            id: 103,
            linear_id: 'issue-celery-pipeline',
            milestone_id: 1,
            title: 'Celery Async Pipeline',
            description:
              'Offload heavy generation tasks into workers so the product can stream progress without blocking the UI.',
            status: 'released',
            demo_url: null,
            labels: ['celery', 'redis'],
            linear_url: 'https://linear.app',
            sort_order: 2,
          },
        ],
      },
      {
        id: 2,
        linear_id: 'cycle-mentor',
        title: 'v2.0 AI Mentor',
        description: 'Context-aware tutoring with persistent memory and configurable model routing.',
        status: 'active',
        start_date: '2025-03-01T00:00:00',
        end_date: '2025-04-10T00:00:00',
        sort_order: 1,
        features: [
          {
            id: 201,
            linear_id: 'issue-mentor-chat',
            milestone_id: 2,
            title: 'Mentor Chat Interface',
            description:
              'Streaming mentor conversations with markdown rendering, multi-thread sessions, and context from the current roadmap.',
            status: 'released',
            demo_url: 'https://www.youtube.com/watch?v=ScMzIvxBSi4',
            labels: ['assistant-ui', 'streaming'],
            linear_url: 'https://linear.app',
            sort_order: 0,
          },
          {
            id: 202,
            linear_id: 'issue-memory',
            milestone_id: 2,
            title: 'Long-term Memory',
            description:
              'The mentor remembers your prior questions, weak spots, and progress across sessions for more personalized guidance.',
            status: 'in_progress',
            demo_url: null,
            labels: ['mem0', 'pgvector'],
            linear_url: 'https://linear.app',
            sort_order: 1,
          },
          {
            id: 203,
            linear_id: 'issue-model-registry',
            milestone_id: 2,
            title: 'Model Registry & Thinking Mode',
            description:
              'Admin-configurable model registry with support flags and optional thinking-mode routing for harder prompts.',
            status: 'in_progress',
            demo_url: null,
            labels: ['admin', 'llm-routing'],
            linear_url: 'https://linear.app',
            sort_order: 2,
          },
        ],
      },
      {
        id: 3,
        linear_id: 'cycle-community',
        title: 'v3.0 Community',
        description: 'Public sharing, collaboration, and roadmap discovery across learners.',
        status: 'upcoming',
        start_date: '2025-05-01T00:00:00',
        end_date: '2025-06-15T00:00:00',
        sort_order: 2,
        features: [
          {
            id: 301,
            linear_id: 'issue-gallery',
            milestone_id: 3,
            title: 'Public Roadmap Gallery',
            description:
              'Explore public roadmaps, fork them into your account, and compare different learning strategies.',
            status: 'planned',
            demo_url: null,
            labels: ['discovery'],
            linear_url: 'https://linear.app',
            sort_order: 0,
          },
          {
            id: 302,
            linear_id: 'issue-study-group',
            milestone_id: 3,
            title: 'Study Group Rooms',
            description:
              'Real-time study rooms so learners on the same roadmap can share progress, blockers, and useful notes.',
            status: 'planned',
            demo_url: null,
            labels: ['real-time', 'websocket'],
            linear_url: 'https://linear.app',
            sort_order: 1,
          },
        ],
      },
    ],
    upcoming_features: [
      {
        id: 401,
        linear_id: 'issue-mentor-agent-refactor',
        milestone_id: null,
        title: 'Refine MentorAgent core messages',
        description: 'Unify the message structure shared across frontend and backend so future mentor iterations stay simpler.',
        status: 'in_progress',
        demo_url: null,
        labels: ['mentor'],
        linear_url: 'https://linear.app',
        sort_order: 0,
      },
      {
        id: 402,
        linear_id: 'issue-linear-feedback',
        milestone_id: null,
        title: 'Ship user feedback into Linear',
        description: 'Pipe user feedback into Linear with cleaner categorization so product iteration can happen faster.',
        status: 'in_progress',
        demo_url: null,
        labels: ['linear'],
        linear_url: 'https://linear.app',
        sort_order: 1,
      },
      {
        id: 403,
        linear_id: 'issue-mobile-app',
        milestone_id: null,
        title: 'Mobile App (iOS / Android)',
        description: 'Offline content, streak reminders, and quick concept review on the go.',
        status: 'planned',
        demo_url: null,
        labels: ['mobile'],
        linear_url: 'https://linear.app',
        sort_order: 2,
      },
      {
        id: 404,
        linear_id: 'issue-certificate',
        milestone_id: null,
        title: 'Certificate Generation',
        description: 'Generate shareable completion certificates with verified roadmap metadata.',
        status: 'planned',
        demo_url: null,
        labels: ['credential'],
        linear_url: 'https://linear.app',
        sort_order: 3,
      },
    ],
  };
}

export function getPublicPlanningItemsMockData(locale: Locale): PublicPlanningItemListResponse {
  if (locale === 'zh') {
    return {
      items: [
        {
          id: 1,
          title: '一键导出为 PDF / Notion 文档',
          description: '支持将路线图一键导出为 PDF，或直接推送进 Notion 工作区。',
          vote_count: 128,
          status: 'open',
          created_at: '2026-03-20T10:00:00',
        },
        {
          id: 2,
          title: '教程内加入 Copilot 风格代码提示',
          description: '在教程代码块中直接提供上下文感知的提示与补全。',
          vote_count: 89,
          status: 'open',
          created_at: '2026-03-19T10:00:00',
        },
        {
          id: 3,
          title: '每日学习摘要邮件',
          description: '结合当前路线图进度，自动生成当天最适合推进的学习建议。',
          vote_count: 67,
          status: 'open',
          created_at: '2026-03-18T10:00:00',
        },
        {
          id: 4,
          title: '间隔复习系统',
          description: '根据概念难度与记忆衰减，自动安排更科学的复习节奏。',
          vote_count: 52,
          status: 'open',
          created_at: '2026-03-17T10:00:00',
        },
        {
          id: 5,
          title: 'VSCode 内嵌学习扩展',
          description: '把路线图任务和概念提示直接带进你的编码工作流。',
          vote_count: 44,
          status: 'open',
          created_at: '2026-03-16T10:00:00',
        },
        {
          id: 6,
          title: '团队 / 企业学习计划',
          description: '支持团队共享学习路径、进度追踪和内部赋能场景。',
          vote_count: 35,
          status: 'open',
          created_at: '2026-03-15T10:00:00',
        },
      ],
      total: 6,
    };
  }

  return {
    items: [
      {
        id: 1,
        title: 'Export roadmap as PDF / Notion doc',
        description: 'One-click export to PDF or direct push into a Notion workspace.',
        vote_count: 128,
        status: 'open',
        created_at: '2026-03-20T10:00:00',
      },
      {
        id: 2,
        title: 'Copilot-style code hints in tutorials',
        description: 'Inline hints and completions embedded into tutorial code examples.',
        vote_count: 89,
        status: 'open',
        created_at: '2026-03-19T10:00:00',
      },
      {
        id: 3,
        title: 'Daily learning digest email',
        description: 'A short daily study plan personalized to your current roadmap progress.',
        vote_count: 67,
        status: 'open',
        created_at: '2026-03-18T10:00:00',
      },
      {
        id: 4,
        title: 'Spaced repetition review system',
        description: 'Automatic review queue based on concept difficulty and memory decay.',
        vote_count: 52,
        status: 'open',
        created_at: '2026-03-17T10:00:00',
      },
      {
        id: 5,
        title: 'VSCode extension for in-editor learning',
        description: 'Bring roadmap tasks and concept hints directly into your coding workflow.',
        vote_count: 44,
        status: 'open',
        created_at: '2026-03-16T10:00:00',
      },
      {
        id: 6,
        title: 'Team / company learning plans',
        description: 'Shared learning tracks and reporting for internal enablement programs.',
        vote_count: 35,
        status: 'open',
        created_at: '2026-03-15T10:00:00',
      },
    ],
    total: 6,
  };
}

export const PUBLIC_ROADMAP_MOCK_DATA: PublicRoadmapDataResponse = getPublicRoadmapMockData('en');

export const PUBLIC_PLANNING_ITEMS_MOCK_DATA: PublicPlanningItemListResponse =
  getPublicPlanningItemsMockData('en');

export async function getPublicRoadmapData(): Promise<PublicRoadmapDataResponse> {
  const response = await apiClient.get<PublicRoadmapDataResponse>('/roadmap/milestones');
  return response.data;
}

export async function getPlanningItems(): Promise<PublicPlanningItemListResponse> {
  const response = await apiClient.get<PublicPlanningItemListResponse>('/roadmap/planning-items');
  return response.data;
}

export async function createPlanningItem(
  payload: PlanningItemCreateRequest
): Promise<PublicPlanningItem> {
  const response = await apiClient.post<PublicPlanningItem>('/roadmap/planning-items', payload);
  return response.data;
}

export async function votePlanningItem(itemId: number): Promise<PlanningItemVoteResponse> {
  const response = await apiClient.post<PlanningItemVoteResponse>(`/roadmap/planning-items/${itemId}/vote`);
  return response.data;
}
