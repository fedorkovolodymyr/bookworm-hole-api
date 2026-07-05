from enum import Enum

from pydantic import BaseModel


class HealthCheckStatus(str, Enum):
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"


class ServiceHealth(BaseModel):
    status: HealthCheckStatus
    message: str | None = None


class HealthCheckResponse(BaseModel):
    status: HealthCheckStatus
    checks: dict[str, ServiceHealth]
    version: str


class StatusResponse(BaseModel):
    status: str


class VersionResponse(BaseModel):
    version: str
