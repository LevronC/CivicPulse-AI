from __future__ import annotations

"""
Background task execution boundary.

Provides a queue-friendly execution model that separates task
submission from task execution. In local development, tasks run
in a thread pool. In production, the same Task interface can be
backed by Celery, RQ, or a custom worker process.

Design constraints:
  - Tasks implement a simple run() -> TaskResult interface
  - The executor owns concurrency, not the caller
  - Task status is trackable (pending, running, completed, failed)
  - Executor can be swapped without changing route handlers
"""

import threading
import time
import uuid
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Protocol

from src.logging import get_logger

logger = get_logger("workers.executor")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class TaskResult:
    """Outcome of a background task execution."""

    status: TaskStatus
    data: dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    duration_ms: float = 0.0
    completed_at: Optional[datetime] = None


class Task(Protocol):
    """
    Protocol for executable background tasks.

    Implementations encapsulate all dependencies needed for execution
    so the executor doesn't need to know about databases, models, or
    other infrastructure.
    """

    @property
    def name(self) -> str:
        ...

    def run(self) -> TaskResult:
        ...


@dataclass
class TaskRecord:
    """Internal tracking record for submitted tasks."""

    task_id: str
    task_name: str
    status: TaskStatus
    submitted_at: datetime
    result: Optional[TaskResult] = None
    future: Optional[Future] = field(default=None, repr=False)


class TaskExecutor:
    """
    Thread-pool backed task executor.

    Wraps concurrent.futures.ThreadPoolExecutor with task tracking,
    status queries, and structured logging. In production, replace
    the thread pool with a Celery/RQ submit while keeping the
    same submit/status interface.
    """

    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="task")
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = threading.Lock()

    def submit(self, task: Task) -> str:
        """Submit a task for background execution. Returns a task ID."""
        task_id = f"task-{uuid.uuid4().hex[:12]}"
        record = TaskRecord(
            task_id=task_id,
            task_name=task.name,
            status=TaskStatus.PENDING,
            submitted_at=datetime.now(timezone.utc),
        )

        with self._lock:
            self._tasks[task_id] = record

        future = self._pool.submit(self._execute, task_id, task)
        record.future = future

        logger.info("Task submitted", extra={"task_id": task_id, "task_name": task.name})
        return task_id

    def get_status(self, task_id: str) -> Optional[TaskRecord]:
        return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> list[dict[str, Any]]:
        records = sorted(
            self._tasks.values(),
            key=lambda r: r.submitted_at,
            reverse=True,
        )[:limit]
        return [
            {
                "task_id": r.task_id,
                "task_name": r.task_name,
                "status": r.status.value,
                "submitted_at": r.submitted_at.isoformat(),
                "result": r.result.data if r.result else None,
                "error": r.result.error if r.result else None,
                "duration_ms": r.result.duration_ms if r.result else None,
            }
            for r in records
        ]

    def _execute(self, task_id: str, task: Task) -> None:
        record = self._tasks[task_id]
        record.status = TaskStatus.RUNNING
        start = time.monotonic()

        try:
            result = task.run()
            result.duration_ms = (time.monotonic() - start) * 1000
            result.completed_at = datetime.now(timezone.utc)
            record.result = result
            record.status = result.status
            logger.info(
                "Task completed",
                extra={
                    "task_id": task_id,
                    "status": result.status.value,
                    "duration_ms": round(result.duration_ms, 1),
                },
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            record.status = TaskStatus.FAILED
            record.result = TaskResult(
                status=TaskStatus.FAILED,
                error=str(exc),
                duration_ms=elapsed,
                completed_at=datetime.now(timezone.utc),
            )
            logger.exception("Task failed", extra={"task_id": task_id})

    def shutdown(self, wait: bool = True) -> None:
        self._pool.shutdown(wait=wait)


_executor: TaskExecutor | None = None


def get_executor() -> TaskExecutor:
    global _executor
    if _executor is None:
        _executor = TaskExecutor()
    return _executor
