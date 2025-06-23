import os
import signal
import sys
from rq import Worker, Queue
from redis import Redis

# Set environment variable to prevent macOS fork issues
os.environ['OBJC_DISABLE_INITIALIZE_FORK_SAFETY'] = 'YES'

# Additional macOS-specific environment variables
os.environ['PYTHONUNBUFFERED'] = '1'

redis_conn = Redis.from_url("redis://localhost:6380/0")
queue = Queue("experiments", connection=redis_conn)

def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"[Worker] Received signal {signum}, shutting down gracefully...")
    sys.exit(0)

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    print("[Worker] Starting RQ worker...")
    print(f"[Worker] Connecting to Redis at {redis_conn.connection_pool.connection_kwargs}")
    
    # Configure worker to handle macOS fork issues better
    worker = Worker(["experiments"], connection=redis_conn)
    
    try:
        worker.work(with_scheduler=True)
    except Exception as e:
        print(f"[Worker] Error: {e}")
        sys.exit(1)
