# app/worker.py
from rq import Worker, Queue
from redis import Redis
from jobs import run_experiment

redis_conn = Redis.from_url("redis://localhost:6379/0")
queue = Queue("experiments", connection=redis_conn)

if __name__ == "__main__":
    Worker(["experiments"], connection=redis_conn).work()
