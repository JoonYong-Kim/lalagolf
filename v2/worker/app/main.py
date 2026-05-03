import os
import signal
import time
import logging

from redis import Redis
from rq import Worker

logger = logging.getLogger("lalagolf.worker")


def get_redis_connection() -> Redis:
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    return Redis.from_url(redis_url)


def create_worker(queues: list[str] | None = None) -> Worker:
    queue_names = queues or os.getenv("RQ_QUEUES", "default").split(",")
    normalized_queues = [queue.strip() for queue in queue_names if queue.strip()]
    return Worker(normalized_queues, connection=get_redis_connection())


def sample_noop_job() -> str:
    logger.info("sample job completed", extra={"job_id": "sample_noop_job"})
    return "ok"


def run() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO").upper())
    poll_interval = int(os.getenv("WORKER_POLL_INTERVAL_SECONDS", "5"))
    run_once = os.getenv("WORKER_RUN_ONCE", "").lower() in {"1", "true", "yes"}
    use_rq = os.getenv("WORKER_USE_RQ", "").lower() in {"1", "true", "yes"}
    running = True

    def stop(_signum: int, _frame: object) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    logger.info("worker started", extra={"job_id": None})
    if run_once:
        logger.info("worker run-once check complete", extra={"job_id": "run_once"})
        return

    if use_rq:
        create_worker().work()
        return

    while running:
        time.sleep(poll_interval)
    logger.info("worker stopped", extra={"job_id": None})


if __name__ == "__main__":
    run()
