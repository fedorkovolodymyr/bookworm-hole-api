from arq.connections import ArqRedis
from arq.jobs import Job, JobStatus
from fastapi import APIRouter, Depends

from app.core.deps import require_admin
from app.core.errors import AppError, NotFoundError
from app.core.redis import get_redis_pool
from app.routers.responses import ADMIN_RESPONSES, NOT_FOUND_RESPONSE
from app.schemas.catalog_import_schemas import (
    CatalogImportJobStatusResponse,
    CatalogImportRequest,
)
from app.worker.tasks import import_catalog_profile

admin_catalog_imports_router = APIRouter(
    prefix="/admin/catalog-imports",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
    responses=ADMIN_RESPONSES,
)


@admin_catalog_imports_router.post(
    "",
    response_model=CatalogImportJobStatusResponse,
    summary="Manually trigger a catalog import profile (books, comics, or manga)",
)
async def trigger_catalog_import(
    body: CatalogImportRequest,
    redis: ArqRedis = Depends(get_redis_pool),
) -> CatalogImportJobStatusResponse:
    job = await redis.enqueue_job(import_catalog_profile.__name__, body.profile)
    if job is None:
        raise AppError("Failed to enqueue catalog import job")
    return CatalogImportJobStatusResponse(
        job_id=job.job_id, status=JobStatus.queued.value
    )


@admin_catalog_imports_router.get(
    "/{job_id}",
    response_model=CatalogImportJobStatusResponse,
    responses=NOT_FOUND_RESPONSE,
    summary="Check the status/result of a triggered catalog import job",
)
async def get_catalog_import_status(
    job_id: str,
    redis: ArqRedis = Depends(get_redis_pool),
) -> CatalogImportJobStatusResponse:
    job = Job(job_id, redis)
    status = await job.status()
    if status == JobStatus.not_found:
        raise NotFoundError("Catalog import job not found")

    result_info = await job.result_info()
    result = result_info.result if result_info and result_info.success else None
    return CatalogImportJobStatusResponse(
        job_id=job_id, status=status.value, result=result
    )
