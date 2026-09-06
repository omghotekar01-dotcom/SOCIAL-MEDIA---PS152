from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SEED_URL = "http://127.0.0.1:8000/api/demo/seed"


def main() -> int:
    payload = json.dumps({"reset": True}).encode("utf-8")
    request = Request(
        SEED_URL,
        data=payload,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            body = response.read().decode("utf-8", errors="replace")
            if not 200 <= response.status < 300:
                print(f"[ERROR] Demo seed returned HTTP {response.status}: {body}", file=sys.stderr)
                return 1
            data = json.loads(body) if body else {}
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        print(f"[ERROR] Demo seed returned HTTP {exc.code}: {detail}", file=sys.stderr)
        return 1
    except URLError as exc:
        print(f"[ERROR] Could not reach NEXUS FastAPI at {SEED_URL}: {exc}", file=sys.stderr)
        return 1
    except (TimeoutError, json.JSONDecodeError) as exc:
        print(f"[ERROR] Demo seed failed: {exc}", file=sys.stderr)
        return 1

    inserted = data.get("inserted", "?")
    total = data.get("total_events", "?")
    print(f"[PASS] Demo dataset seeded: inserted={inserted}, total_events={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
