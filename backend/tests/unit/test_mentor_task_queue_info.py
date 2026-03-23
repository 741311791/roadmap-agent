from app.core.celery_app import celery_app
from app.core.celery_worker_heartbeat import infer_worker_queues


def test_mentor_task_routes_registered() -> None:
    """AI 伴学助手任务应路由到独立队列。"""
    task_routes = celery_app.conf.task_routes

    assert task_routes["mentor.persist_and_extract_memory"]["queue"] == "mentor_persist"
    assert task_routes["mentor.extract_long_term_memory"]["queue"] == "mentor_memory"
    assert task_routes["mentor.run_reflection"]["queue"] == "mentor_memory"


def test_mentor_queues_registered() -> None:
    """Celery 队列配置应包含 AI 伴学助手专用队列。"""
    task_queues = celery_app.conf.task_queues

    assert "mentor_persist" in task_queues
    assert "mentor_memory" in task_queues


def test_mentor_reflection_registered_in_existing_beat_schedule() -> None:
    """mentor_reflection 应合并进现有 Beat 调度表。"""
    beat_schedule = celery_app.conf.beat_schedule

    assert "mentor-reflection" in beat_schedule
    assert beat_schedule["mentor-reflection"]["task"] == "mentor.run_reflection"


def test_mentor_worker_heartbeat_queue_mapping() -> None:
    """Worker 心跳映射应能识别新的 AI 伴学助手队列。"""
    assert infer_worker_queues("mentor-persist@test-host") == ["mentor_persist"]
    assert infer_worker_queues("mentor-memory@test-host") == ["mentor_memory"]
