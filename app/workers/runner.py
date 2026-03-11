from __future__ import annotations

from app.workers.queue import get_queue, get_redis_connection


def main() -> None:
    from rq import Connection, Worker

    connection = get_redis_connection()
    queue = get_queue()
    with Connection(connection):
        worker = Worker([queue.name], connection=connection)
        worker.work()


if __name__ == "__main__":
    main()
