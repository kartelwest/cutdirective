import os
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

API_URL = os.getenv("API_URL", "http://api:8000")
HEARTBEAT_INTERVAL = int(os.getenv("WORKER_HEARTBEAT_INTERVAL_SECONDS", "10"))
WORKER_ID = os.getenv("WORKER_ID", "worker-001")


def log(msg: str) -> None:
    print(f"{datetime.now(timezone.utc).isoformat()} {WORKER_ID}: {msg}", flush=True)


def main() -> None:
    log("worker started")
    while True:
        try:
            req = urllib.request.Request(f"{API_URL}/health")
            with urllib.request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode()
            log(f"health ok: {body[:120]}")
        except urllib.error.URLError as exc:
            log(f"api unreachable: {exc}")
        except Exception as exc:
            log(f"error: {exc}")
        time.sleep(HEARTBEAT_INTERVAL)


if __name__ == "__main__":
    main()
