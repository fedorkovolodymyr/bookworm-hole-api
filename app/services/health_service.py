from loguru import logger
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.health_schemas import (
    HealthCheckResponse,
    HealthCheckStatus,
    ServiceHealth,
)


class HealthService:
    async def check_api(self) -> ServiceHealth:
        logger.debug("Performing API health check")
        return ServiceHealth(status=HealthCheckStatus.HEALTHY, message="API is running")

    async def check_database(self, session: AsyncSession) -> ServiceHealth:
        """Перевіряє підключення до бази даних."""
        try:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar()

            if value == 1:
                return ServiceHealth(
                    status=HealthCheckStatus.HEALTHY,
                    message="Database connection is healthy",
                )
            else:
                return ServiceHealth(
                    status=HealthCheckStatus.UNHEALTHY,
                    message="Database returned unexpected result",
                )

        except SQLAlchemyError as e:
            logger.error(f"Database health check failed: {e}")
            return ServiceHealth(
                status=HealthCheckStatus.UNHEALTHY,
                message=f"Database connection failed: {str(e)}",
            )

    async def check_overall(self, session: AsyncSession) -> HealthCheckResponse:
        api_health = await self.check_api()
        db_health = await self.check_database(session)

        overall_status = self._get_overall_status(api_health, db_health)

        return HealthCheckResponse(
            status=overall_status,
            checks={
                "api": api_health,
                "database": db_health,
            },
        )

    def _get_overall_status(self, *service_healths: ServiceHealth) -> HealthCheckStatus:
        all_healthy = all(
            [
                service_health.status == HealthCheckStatus.HEALTHY
                for service_health in service_healths
            ]
        )

        return HealthCheckStatus.HEALTHY if all_healthy else HealthCheckStatus.UNHEALTHY
