"""Tests for the background task executor."""

import time

from src.workers.executor import TaskExecutor, TaskResult, TaskStatus


class _EchoTask:
    @property
    def name(self) -> str:
        return "echo"

    def run(self) -> TaskResult:
        return TaskResult(status=TaskStatus.COMPLETED, data={"echo": "done"})


class _SlowTask:
    @property
    def name(self) -> str:
        return "slow"

    def run(self) -> TaskResult:
        time.sleep(0.1)
        return TaskResult(status=TaskStatus.COMPLETED, data={"slow": True})


class _FailingTask:
    @property
    def name(self) -> str:
        return "failing"

    def run(self) -> TaskResult:
        raise RuntimeError("intentional failure")


def test_submit_and_complete():
    executor = TaskExecutor(max_workers=1)
    try:
        task_id = executor.submit(_EchoTask())
        time.sleep(0.2)
        record = executor.get_status(task_id)
        assert record is not None
        assert record.status == TaskStatus.COMPLETED
        assert record.result.data["echo"] == "done"
    finally:
        executor.shutdown()


def test_failing_task_records_error():
    executor = TaskExecutor(max_workers=1)
    try:
        task_id = executor.submit(_FailingTask())
        time.sleep(0.2)
        record = executor.get_status(task_id)
        assert record is not None
        assert record.status == TaskStatus.FAILED
        assert "intentional failure" in record.result.error
    finally:
        executor.shutdown()


def test_list_tasks():
    executor = TaskExecutor(max_workers=2)
    try:
        executor.submit(_EchoTask())
        executor.submit(_EchoTask())
        time.sleep(0.3)
        tasks = executor.list_tasks()
        assert len(tasks) == 2
        assert all(t["status"] == "completed" for t in tasks)
    finally:
        executor.shutdown()


def test_missing_task_returns_none():
    executor = TaskExecutor(max_workers=1)
    try:
        assert executor.get_status("nonexistent") is None
    finally:
        executor.shutdown()
