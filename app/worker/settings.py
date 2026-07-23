from typing import ClassVar

from arq.connections import RedisSettings

from app.core.config import settings
from app.worker.tasks import import_catalog_profile


def _redis_settings() -> RedisSettings:
    redis_settings = settings.redis_settings
    return RedisSettings(
        host=redis_settings.host, port=redis_settings.port, database=redis_settings.db
    )


class WorkerSettings:
    functions: ClassVar = [import_catalog_profile]
    redis_settings = _redis_settings()
    max_jobs = 2
    job_timeout = 3600
