from __future__ import annotations

from redis import Redis

from app.config import get_settings


def get_redis_connection() -> Redis:
    settings = get_settings()
    return Redis.from_url(settings.redis_url)

def get_queue():
    from rq import Queue

    settings = get_settings()
    return Queue(settings.rq_queue_name, connection=get_redis_connection())
