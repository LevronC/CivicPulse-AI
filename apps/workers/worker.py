"""
Simple queue-style worker loop with retry + DLQ simulation.
"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any

import requests

API = "http://localhost:8000"
API_KEY = "dev-api-key"


@dataclass
class Job:
    endpoint: str
    payload: dict[str, Any] = field(default_factory=dict)
    retries: int = 0


def run() -> None:
    queue = deque([Job("/ingest"), Job("/enrich"), Job("/events/rebuild")])
    dlq: list[Job] = []
    while True:
        if not queue:
            queue.extend([Job("/ingest"), Job("/enrich"), Job("/events/rebuild")])
            time.sleep(5)
            continue
        job = queue.popleft()
        try:
            resp = requests.post(f"{API}{job.endpoint}", headers={"x-api-key": API_KEY}, timeout=10)
            resp.raise_for_status()
            print(f"ok {job.endpoint}: {resp.json()}")
        except Exception as exc:  # noqa: BLE001
            job.retries += 1
            if job.retries <= 3:
                queue.append(job)
                print(f"retry {job.endpoint} ({job.retries}): {exc}")
            else:
                dlq.append(job)
                print(f"dlq {job.endpoint}: {exc}")
        time.sleep(1)


if __name__ == "__main__":
    run()
