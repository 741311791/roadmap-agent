"""
API 端点模块

重构后按7大业务领域组织（2026-01-14）：

1. auth/ - 认证授权
   - 登出、登出所有设备、Token黑名单

2. users/ - 用户画像管理
   - 用户画像获取/保存

3. roadmaps/ - 路线图资源管理
   - list.py: 用户路线图列表、回收站、精选路线图
   - crud.py: 获取、删除、恢复、永久删除、状态检查
   - metadata.py: 需求分析、编辑记录、验证记录
   - streaming.py: 流式生成
   - cover_image.py: 封面图管理

4. tasks/ - 任务执行与追踪
   - generation.py: 任务生成、取消
   - query.py: 任务状态、用户任务列表、活跃任务
   - retry.py: 任务重试
   - approval.py: 人工审核
   - trace.py: 执行日志追踪（带权限验证）

5. content/ - 内容管理
   - query.py: 教程/资源/测验查询
   - regenerate.py: 内容重新生成
   - modification.py: 内容修改
   - concept_status.py: Concept状态
   - subgraph.py: 单Concept内容生成

6. learning/ - 学习体验
   - progress.py: 学习进度
   - assessment.py: 技术栈能力测试
   - mentor.py: 伴学Mentor

7. admin/ - 平台管理
   - users.py: 用户邀请、超级管理员
   - waitlist.py: Waitlist管理（公开+管理）
   - tavily.py: Tavily Key管理
   - monitoring.py: Celery监控
"""
