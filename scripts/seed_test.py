import asyncio
import os

os.environ.setdefault("POSTGRES_DB", "bookwormhole_test")

from scripts.seed import main  # noqa: E402

if __name__ == "__main__":
    asyncio.run(main())
