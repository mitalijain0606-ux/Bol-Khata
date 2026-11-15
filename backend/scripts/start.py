"""Production entry point (Docker / Render).

    python -m scripts.start

- SEED_ON_START=1 (default in the container) reloads the fake demo data on every
  start, so the public demo account always looks clean. Hosts like Render's free
  tier wipe the disk on restart anyway; accounts people register are temporary.
- Listens on $PORT and trusts the host's proxy headers (real client IP for rate
  limits, https scheme).
"""
import os

import uvicorn

from app.db import DB_PATH


def main():
    if os.getenv("SEED_ON_START", "1") == "1" or not DB_PATH.exists():
        from scripts.seed_fake_data import seed
        seed()
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.getenv("PORT", "8000")),
                proxy_headers=True, forwarded_allow_ips="*", log_level="info")


if __name__ == "__main__":
    main()
